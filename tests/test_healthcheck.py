from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck_deve_retornar_ok():
    cliente = TestClient(app)

    resposta = cliente.get("/healthcheck")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
