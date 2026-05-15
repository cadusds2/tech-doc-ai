from fastapi.testclient import TestClient

from app.main import app


def test_interface_web_deve_retornar_ok():
    cliente = TestClient(app)

    resposta = cliente.get("/interface")

    assert resposta.status_code == 200
    assert "Interface web da API RAG" in resposta.text


def test_interface_web_deve_exibir_lista_de_documentos_e_conversa():
    cliente = TestClient(app)

    resposta = cliente.get("/interface")

    assert resposta.status_code == 200
    assert "Lista de documentos" in resposta.text
    assert "lista-documentos" in resposta.text
    assert "Conversa com os documentos" in resposta.text
    assert "timeline-chat" in resposta.text
    assert "Nova conversa" in resposta.text
