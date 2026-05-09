from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dependencias import obter_agendador_processamento_documentos, obter_servico_ingestao_documentos
from app.domain.documento import StatusProcessamentoDocumento
from app.infra.modelos_orm import Base
from app.main import app
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.chunking import TrechoGerado
from app.services.ingestao_documentos import ServicoIngestaoDocumentos
from app.services.processamento_documentos import ProcessadorDocumentos


class AgendadorFalso:
    def __init__(self):
        self.chamadas = []

    def agendar_processamento(self, documento_id: int, nome_arquivo: str, conteudo_bytes: bytes) -> None:
        self.chamadas.append((documento_id, nome_arquivo, conteudo_bytes))


class ParserFalso:
    def __init__(self, texto: str | None = "Texto técnico extraído."):
        self.texto = texto

    def extrair_texto(self, _nome_arquivo: str, _conteudo_bytes: bytes) -> str:
        if self.texto is None:
            raise ValueError("Falha simulada no parser.")
        return self.texto


class ChunkingFalso:
    def chunkar_texto(self, texto: str) -> list[TrechoGerado]:
        return [
            TrechoGerado(
                indice_trecho=0,
                conteudo=texto,
                indice_inicio=0,
                indice_fim=len(texto),
                tamanho_caracteres=len(texto),
            )
        ]


def _criar_fabrica_sessao_sqlite():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_post_ingestao_deve_criar_documento_recebido_e_agendar_processamento():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    agendador = AgendadorFalso()

    def sobrescrever_servico_ingestao():
        sessao = fabrica_sessao()
        return ServicoIngestaoDocumentos(
            repositorio=RepositorioDocumentos(sessao),
            parser=ParserFalso(),
            servico_chunking=ChunkingFalso(),
        )

    app.dependency_overrides[obter_servico_ingestao_documentos] = sobrescrever_servico_ingestao
    app.dependency_overrides[obter_agendador_processamento_documentos] = lambda: agendador
    try:
        cliente = TestClient(app)
        resposta = cliente.post(
            "/documentos/ingestao",
            files={"arquivo": ("manual.txt", b"conteudo tecnico", "text/plain")},
        )
        resposta_consulta = cliente.get("/documentos/1")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["documento_id"] == 1
    assert corpo["nome_arquivo"] == "manual.txt"
    assert corpo["tipo_arquivo"] == "txt"
    assert corpo["status_processamento"] == StatusProcessamentoDocumento.RECEBIDO.value
    assert corpo["mensagem_erro_processamento"] is None
    assert agendador.chamadas == [(1, "manual.txt", b"conteudo tecnico")]
    assert resposta_consulta.status_code == 200
    assert resposta_consulta.json()["status_processamento"] == StatusProcessamentoDocumento.RECEBIDO.value


def test_processador_deve_atualizar_status_ate_indexado_sem_indexacao_vetorial():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    repositorio = RepositorioDocumentos(sessao)
    documento = repositorio.registrar_documento_recebido("manual.txt", "txt", tamanho_bytes=8)

    ProcessadorDocumentos(
        repositorio=repositorio,
        parser=ParserFalso("Conteúdo final extraído."),
        servico_chunking=ChunkingFalso(),
    ).processar_documento(documento.id, "manual.txt", b"conteudo")

    documento_atualizado = repositorio.buscar_documento_por_id(documento.id)
    assert documento_atualizado is not None
    assert documento_atualizado.quantidade_caracteres == len("Conteúdo final extraído.")
    assert documento_atualizado.status_processamento == StatusProcessamentoDocumento.INDEXADO.value
    assert documento_atualizado.mensagem_erro_processamento is None
    assert len(documento_atualizado.trechos) == 1


def test_processador_deve_persistir_erro_resumido_quando_parser_falhar():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    repositorio = RepositorioDocumentos(sessao)
    documento = repositorio.registrar_documento_recebido("manual.txt", "txt", tamanho_bytes=8)

    ProcessadorDocumentos(
        repositorio=repositorio,
        parser=ParserFalso(texto=None),
        servico_chunking=ChunkingFalso(),
    ).processar_documento(documento.id, "manual.txt", b"conteudo")

    documento_atualizado = repositorio.buscar_documento_por_id(documento.id)
    assert documento_atualizado is not None
    assert documento_atualizado.status_processamento == StatusProcessamentoDocumento.ERRO.value
    assert documento_atualizado.mensagem_erro_processamento == "Falha simulada no parser."
    assert documento_atualizado.quantidade_caracteres == 0
