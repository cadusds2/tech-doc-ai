from fastapi.testclient import TestClient

from app.main import app


def test_interface_web_deve_retornar_ok():
    cliente = TestClient(app)

    resposta = cliente.get("/interface")

    assert resposta.status_code == 200
    assert "Interface web da API RAG" in resposta.text


def test_interface_web_deve_exibir_exclusao_de_documentos():
    cliente = TestClient(app)

    resposta = cliente.get("/interface")

    assert resposta.status_code == 200
    assert "Remover documento" in resposta.text
    assert "formulario-exclusao-documento" in resposta.text
    assert "Excluir documento" in resposta.text
