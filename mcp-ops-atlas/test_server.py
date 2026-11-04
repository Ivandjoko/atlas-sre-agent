from server import resumer_evenements


def test_taux_et_causes():
    evts = [
        {"message": "requête traitée", "path": "/virements", "status": 201},
        {"message": "requête traitée", "path": "/virements", "status": 500},
        {"message": "échec du virement", "error_code": "CORE_BANKING_TIMEOUT"},
        {"message": "requête traitée", "path": "/health", "status": 200},  # sonde ignorée
    ]
    r = resumer_evenements(evts, 15)
    assert r["requetes_clients"] == 2
    assert r["requetes_en_echec"] == 1
    assert r["taux_echec_pct"] == 50.0
    assert r["causes_par_code"] == {"CORE_BANKING_TIMEOUT": 1}
