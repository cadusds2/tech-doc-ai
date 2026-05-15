from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.routes import documentos
from app.dependencias import (
    obter_agendador_processamento_documentos,
    obter_servico_ingestao_documentos,
    obter_servico_projetos,
)
from app.main import app
from app.services.ingestao_documentos import ErroDocumentoDuplicado


class ServicoProjetosFalso:
    def resolver_projeto_upload(
        self,
        projeto_id: int | None = None,
        novo_projeto_nome: str | None = None,
    ):
        return SimpleNamespace(
            id=projeto_id or 1,
            nome=novo_projeto_nome or "Projeto Teste",
            slug="projeto-teste",
            descricao=None,
        )


class ServicoIngestaoNaoUtilizado:
    def registrar_documento_recebido(
        self,
        projeto_id: int,
        nome_arquivo: str,
        conteudo_bytes: bytes,
        hash_conteudo: str | None = None,
    ):
        raise AssertionError("Upload invalido nao deve registrar documento.")


class AgendadorNaoUtilizado:
    def agendar_processamento(
        self, _documento_id: int, _nome_arquivo: str, _conteudo: bytes
    ):
        raise AssertionError("Upload invalido nao deve agendar processamento.")


def _postar_arquivo(
    nome_arquivo: str, conteudo: bytes, monkeypatch, limite_bytes: int = 1024
):
    monkeypatch.setattr(
        documentos,
        "obter_configuracoes",
        lambda: SimpleNamespace(tamanho_maximo_upload_bytes=limite_bytes),
    )
    app.dependency_overrides[obter_servico_ingestao_documentos] = (
        ServicoIngestaoNaoUtilizado
    )
    app.dependency_overrides[obter_servico_projetos] = ServicoProjetosFalso
    app.dependency_overrides[obter_agendador_processamento_documentos] = (
        AgendadorNaoUtilizado
    )
    try:
        cliente = TestClient(app)
        return cliente.post(
            "/documentos/ingestao",
            data={"novo_projeto_nome": "Projeto Teste"},
            files={"arquivo": (nome_arquivo, conteudo, "application/octet-stream")},
        )
    finally:
        app.dependency_overrides.clear()


def test_upload_deve_rejeitar_arquivo_acima_do_limite(monkeypatch):
    resposta = _postar_arquivo(
        nome_arquivo="manual.txt",
        conteudo=b"12345",
        monkeypatch=monkeypatch,
        limite_bytes=4,
    )

    assert resposta.status_code == 413
    assert resposta.json() == {"detalhe": "Arquivo acima do limite permitido."}


def test_upload_deve_rejeitar_extensao_invalida(monkeypatch):
    resposta = _postar_arquivo(
        nome_arquivo="manual.exe",
        conteudo=b"conteudo",
        monkeypatch=monkeypatch,
    )

    assert resposta.status_code == 400
    assert resposta.json() == {"detalhe": "Arquivo enviado invalido."}


def test_upload_deve_rejeitar_nome_ausente(monkeypatch):
    resposta = _postar_arquivo(
        nome_arquivo=" ",
        conteudo=b"conteudo",
        monkeypatch=monkeypatch,
    )

    assert resposta.status_code == 400
    assert resposta.json() == {"detalhe": "Arquivo enviado invalido."}


def test_upload_deve_rejeitar_arquivo_vazio(monkeypatch):
    resposta = _postar_arquivo(
        nome_arquivo="manual.txt",
        conteudo=b"",
        monkeypatch=monkeypatch,
    )

    assert resposta.status_code == 400
    assert resposta.json() == {"detalhe": "Arquivo vazio nao e permitido."}


def test_upload_deve_rejeitar_arquivo_duplicado(monkeypatch):
    class ServicoIngestaoDuplicadoFalso:
        def registrar_documento_recebido(
            self,
            projeto_id: int,
            nome_arquivo: str,
            conteudo_bytes: bytes,
            hash_conteudo: str | None = None,
        ):
            raise ErroDocumentoDuplicado(documento_id_existente=7)

    monkeypatch.setattr(
        documentos,
        "obter_configuracoes",
        lambda: SimpleNamespace(tamanho_maximo_upload_bytes=1024),
    )
    app.dependency_overrides[obter_servico_ingestao_documentos] = (
        ServicoIngestaoDuplicadoFalso
    )
    app.dependency_overrides[obter_servico_projetos] = ServicoProjetosFalso
    app.dependency_overrides[obter_agendador_processamento_documentos] = (
        AgendadorNaoUtilizado
    )
    try:
        cliente = TestClient(app)
        resposta = cliente.post(
            "/documentos/ingestao",
            data={"novo_projeto_nome": "Projeto Teste"},
            files={"arquivo": ("manual.txt", b"conteudo tecnico", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detalhe": "Arquivo duplicado ja enviado anteriormente no documento 7."
    }
