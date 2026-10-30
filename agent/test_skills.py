from skills import charger_skill, lire_ressource_skill


def test_path_traversal_refuse():
    reponse = lire_ressource_skill(nom="postmortem", chemin="../../../../.sentinelle.env")
    assert "interdite" in reponse


def test_skill_hors_du_dossier_refusee():
    assert "inconnue" in charger_skill(nom="../outils_locaux")


def test_ressource_legitime_lue():
    reponse = lire_ressource_skill(nom="triage-incident", chemin="references/matrice-severite.md")
    assert "SEV1" in reponse
