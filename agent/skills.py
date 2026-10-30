"""Chargement des skills par divulgation progressive (catalogue, instructions, ressources)."""
from pathlib import Path

import yaml
from strands import tool

DOSSIER_SKILLS = (Path(__file__).parent / "skills").resolve()


def _lire_skill(dossier: Path) -> tuple[dict, str]:
    """Sépare le frontmatter YAML (entre les deux ---) du corps markdown."""
    texte = (dossier / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, corps = texte.split("---", 2)
    return yaml.safe_load(frontmatter), corps.strip()


def catalogue_skills() -> str:
    """Niveau 1 : une ligne par skill (nom + description), pour le system prompt."""
    lignes = []
    for dossier in sorted(DOSSIER_SKILLS.iterdir()):
        if (dossier / "SKILL.md").is_file():
            meta, _ = _lire_skill(dossier)
            lignes.append(f"- {meta['name']} : {meta['description']}")
    return "\n".join(lignes)


def _dossier_valide(nom: str) -> Path | None:
    """Refuse tout nom qui sortirait du dossier skills (ex. '../..')."""
    dossier = (DOSSIER_SKILLS / nom).resolve()
    if dossier.parent != DOSSIER_SKILLS or not (dossier / "SKILL.md").is_file():
        return None
    return dossier


@tool
def charger_skill(nom: str) -> str:
    """Charge les instructions complètes d'une skill du catalogue.
    À appeler avant toute tâche couverte par une skill, puis suivre ses instructions.

    Args:
        nom: nom exact de la skill, tel qu'affiché dans le catalogue.
    """
    dossier = _dossier_valide(nom)
    if dossier is None:
        return f"Skill inconnue : {nom}. Skills disponibles :\n{catalogue_skills()}"
    _, corps = _lire_skill(dossier)
    return corps


@tool
def lire_ressource_skill(nom: str, chemin: str) -> str:
    """Lit un fichier annexe d'une skill (référence, modèle), uniquement si ses instructions le demandent.

    Args:
        nom: nom de la skill.
        chemin: chemin relatif dans le dossier de la skill, par exemple "references/matrice-severite.md".
    """
    dossier = _dossier_valide(nom)
    if dossier is None:
        return f"Skill inconnue : {nom}."
    fichier = (dossier / chemin).resolve()
    if not fichier.is_relative_to(dossier) or not fichier.is_file():
        return f"Ressource introuvable ou interdite : {chemin}"
    return fichier.read_text(encoding="utf-8")[:20_000]
