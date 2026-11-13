"""Envoie les traces OpenTelemetry de Strands vers Langfuse."""
import base64
import os

from strands.telemetry import StrandsTelemetry


def activer_telemetrie() -> bool:
    """Configure l'export OTLP vers Langfuse. Sans clés, l'agent tourne quand même, sans traces."""
    cle_publique = os.getenv("LANGFUSE_PUBLIC_KEY")
    cle_secrete = os.getenv("LANGFUSE_SECRET_KEY")
    if not (cle_publique and cle_secrete):
        print("Télémétrie désactivée : clés Langfuse absentes.")
        return False
    hote = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    jeton = base64.b64encode(f"{cle_publique}:{cle_secrete}".encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{hote}/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {jeton}"
    StrandsTelemetry().setup_otlp_exporter()
    return True
