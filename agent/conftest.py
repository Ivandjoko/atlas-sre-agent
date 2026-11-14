"""Configuration commune de pytest : vider les traces avant la fin des tests."""
from opentelemetry import trace


def pytest_sessionfinish(session, exitstatus):
    """Les traces partent par lots en arrière-plan : on force l'envoi des derniers avant de quitter."""
    fournisseur = trace.get_tracer_provider()
    if hasattr(fournisseur, "force_flush"):
        fournisseur.force_flush()
