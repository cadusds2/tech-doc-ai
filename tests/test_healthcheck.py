from fastapi.testclient import TestClient

from app.main import app



def test_health_deve_retornar_ok():
    cliente = TestClient(app)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
