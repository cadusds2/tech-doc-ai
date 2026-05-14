from fastapi.testclient import TestClient

from app.main import app


def test_interface_web_deve_retornar_ok():
    cliente = TestClient(app)

    resposta = cliente.get("/interface")

    assert resposta.status_code == 200
    assert "Interface web da API RAG" in resposta.text
