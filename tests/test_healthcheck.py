from fastapi.testclient import TestClient

from app.main import app


def test_health_deve_retornar_ok():
    cliente = TestClient(app)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200

    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["aplicacao"] == "Tech Doc AI"
    assert corpo["versao"] == "0.1.0"
    assert corpo["ambiente"] == "desenvolvimento"
    assert "horario_utc" in corpo
