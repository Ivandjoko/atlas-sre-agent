"""API de virements factice de la Banque Atlas, avec injection de pannes."""
import asyncio
import json
import logging
import os
import random
import secrets
import sys
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

SERVICE = "api-virements"
VERSION = os.getenv("APP_VERSION", "1.0.0")


# --- Logs structurés : une ligne JSON par événement --------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": SERVICE,
            "version": VERSION,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        return json.dumps(entry, ensure_ascii=False)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger(SERVICE)
log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False


def log_event(message: str, level: int = logging.INFO, **fields) -> None:
    log.log(level, message, extra={"fields": fields})


# --- Vérification de configuration au démarrage -----------------------------
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    log_event("configuration invalide : variable DB_URL absente", logging.CRITICAL,
              error_code="CONFIG_MISSING", variable="DB_URL")
    sys.exit(1)  # code de sortie non nul : l'orchestrateur verra un échec

CHAOS_TOKEN = os.getenv("CHAOS_TOKEN")  # pas de jeton = injection de pannes désactivée
chaos = {"error_rate": 0.0, "latency_ms": 0, "ready": True}

app = FastAPI(title="API virements - Banque Atlas", version=VERSION)


# --- Middleware : un log d'accès par requête, avec identifiant de corrélation --
@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    try:
        response = await call_next(request)
    except Exception:
        log_event("exception non gérée", logging.ERROR, request_id=request_id)
        response = JSONResponse({"detail": "erreur interne"}, status_code=500)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    level = logging.ERROR if response.status_code >= 500 else logging.INFO
    log_event("requête traitée", level, method=request.method, path=request.url.path,
              status=response.status_code, duration_ms=duration_ms, request_id=request_id)
    response.headers["x-request-id"] = request_id
    return response


# --- Santé ------------------------------------------------------------------
@app.get("/health")
def health():
    """Liveness : le processus répond-il ? Ne teste aucune dépendance externe."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness : le service peut-il recevoir du trafic ?"""
    if not chaos["ready"]:
        raise HTTPException(status_code=503, detail="service non prêt")
    return {"status": "ready"}


# --- Métier -----------------------------------------------------------------
class Virement(BaseModel):
    compte_source: str = Field(min_length=5, max_length=34)
    compte_destination: str = Field(min_length=5, max_length=34)
    montant: float = Field(gt=0, le=100_000)


@app.post("/virements", status_code=201)
async def creer_virement(virement: Virement):
    if chaos["latency_ms"]:
        await asyncio.sleep(chaos["latency_ms"] / 1000)
    if random.random() < chaos["error_rate"]:
        log_event("échec du virement : délai dépassé vers le core banking", logging.ERROR,
                  error_code="CORE_BANKING_TIMEOUT", montant=virement.montant)
        raise HTTPException(status_code=500, detail="échec temporaire, réessayez")
    return {"id": f"VIR-{uuid.uuid4().hex[:10].upper()}", "statut": "accepté",
            "montant": virement.montant}


# --- Injection de pannes (protégée par jeton) -------------------------------
def verifier_chaos(x_chaos_token: str | None = Header(default=None)) -> None:
    if not CHAOS_TOKEN or not x_chaos_token or not secrets.compare_digest(x_chaos_token, CHAOS_TOKEN):
        raise HTTPException(status_code=403, detail="injection de pannes refusée")


@app.post("/chaos/errors", dependencies=[Depends(verifier_chaos)])
def chaos_errors(rate: float = 0.5):
    if not 0 <= rate <= 1:
        raise HTTPException(status_code=422, detail="rate doit être entre 0 et 1")
    chaos["error_rate"] = rate
    log_event("chaos : taux d'erreur modifié", logging.WARNING, error_rate=rate)
    return chaos


@app.post("/chaos/latency", dependencies=[Depends(verifier_chaos)])
def chaos_latency(ms: int = 2000):
    chaos["latency_ms"] = max(0, min(ms, 30_000))
    log_event("chaos : latence ajoutée", logging.WARNING, latency_ms=chaos["latency_ms"])
    return chaos


@app.post("/chaos/not-ready", dependencies=[Depends(verifier_chaos)])
def chaos_not_ready():
    chaos["ready"] = False
    log_event("chaos : service marqué non prêt", logging.WARNING)
    return chaos


@app.post("/chaos/crash", dependencies=[Depends(verifier_chaos)])
def chaos_crash():
    log_event("chaos : arrêt brutal du processus", logging.CRITICAL, error_code="CRASH_INJECTED")
    os._exit(1)


@app.post("/chaos/reset", dependencies=[Depends(verifier_chaos)])
def chaos_reset():
    chaos.update(error_rate=0.0, latency_ms=0, ready=True)
    log_event("chaos : retour à la normale", logging.WARNING)
    return chaos
