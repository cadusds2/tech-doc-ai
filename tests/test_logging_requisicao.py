import logging

from fastapi.testclient import TestClient

from app.core.logging import obter_identificador_requisicao
from app.main import app


def test_middleware_deve_devolver_identificador_requisicao_informado():
    cliente = TestClient(app)

    resposta = cliente.get("/health", headers={"X-Request-ID": "requisicao-teste-123"})

    assert resposta.status_code == 200
    assert resposta.headers["X-Request-ID"] == "requisicao-teste-123"


def test_middleware_deve_gerar_identificador_requisicao_quando_ausente():
    cliente = TestClient(app)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.headers["X-Request-ID"]
    assert len(resposta.headers["X-Request-ID"]) == 32


def test_filtro_de_logging_deve_incluir_identificador_do_contexto(caplog):
    cliente = TestClient(app)

    with caplog.at_level(logging.INFO):
        resposta = cliente.get("/health", headers={"X-Request-ID": "ctx-456"})
        logging.getLogger("tests.logging").info("Mensagem de teste em português.")

    assert resposta.headers["X-Request-ID"] == "ctx-456"
    assert obter_identificador_requisicao() == "sem-requisicao"
    assert any(
        getattr(registro, "identificador_requisicao", None) == "ctx-456"
        for registro in caplog.records
    )
