from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import dependencias
from app.dependencias import (
    obter_agendador_processamento_documentos,
    obter_servico_ingestao_documentos,
    obter_servico_projetos,
)
from app.domain.documento import StatusProcessamentoDocumento
from app.infra.modelos_orm import Base, ProjetoORM
from app.main import app
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.repositories.repositorio_projetos import RepositorioProjetos
from app.services import processamento_documentos
from app.services.chunking import TrechoGerado
from app.services.ingestao_documentos import ErroDocumentoDuplicado, ServicoIngestaoDocumentos
from app.services.processamento_documentos import (
    AgendadorBackgroundTasksFastAPI,
    ProcessadorDocumentos,
    executar_processamento_documento_em_nova_sessao,
)
from app.services.projetos import ServicoProjetos


class AgendadorFalso:
    def __init__(self):
        self.chamadas = []

    def agendar_processamento(
        self, documento_id: int, nome_arquivo: str, conteudo_bytes: bytes
    ) -> None:
        self.chamadas.append((documento_id, nome_arquivo, conteudo_bytes))


class TarefasBackgroundFalsas:
    def __init__(self):
        self.chamadas = []

    def add_task(self, funcao, *args):
        self.chamadas.append((funcao, args))


class ParserFalso:
    def __init__(self, texto: str | None = "Texto tecnico extraido."):
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


def _criar_projeto(sessao, nome: str = "Projeto Teste") -> ProjetoORM:
    projeto = ProjetoORM(nome=nome, slug=nome.lower().replace(" ", "-"))
    sessao.add(projeto)
    sessao.commit()
    sessao.refresh(projeto)
    return projeto


def _criar_servico_projetos(fabrica_sessao):
    def _sobrescrever():
        return ServicoProjetos(RepositorioProjetos(fabrica_sessao()))

    return _sobrescrever


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
    app.dependency_overrides[obter_servico_projetos] = _criar_servico_projetos(
        fabrica_sessao
    )
    app.dependency_overrides[obter_agendador_processamento_documentos] = lambda: agendador
    try:
        cliente = TestClient(app)
        resposta = cliente.post(
            "/documentos/ingestao",
            data={"novo_projeto_nome": "Projeto Teste"},
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
    assert corpo["projeto"]["nome"] == "Projeto Teste"
    assert agendador.chamadas == [(1, "manual.txt", b"conteudo tecnico")]
    assert resposta_consulta.status_code == 200
    assert (
        resposta_consulta.json()["status_processamento"]
        == StatusProcessamentoDocumento.RECEBIDO.value
    )


def test_get_documentos_deve_listar_documentos_mais_recentes():
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
    app.dependency_overrides[obter_servico_projetos] = _criar_servico_projetos(
        fabrica_sessao
    )
    app.dependency_overrides[obter_agendador_processamento_documentos] = lambda: agendador
    try:
        cliente = TestClient(app)
        cliente.post(
            "/documentos/ingestao",
            data={"novo_projeto_nome": "Projeto Teste"},
            files={"arquivo": ("primeiro.txt", b"conteudo 1", "text/plain")},
        )
        cliente.post(
            "/documentos/ingestao",
            data={"projeto_id": "1"},
            files={"arquivo": ("segundo.txt", b"conteudo 2", "text/plain")},
        )
        resposta = cliente.get("/documentos")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [documento["nome_arquivo"] for documento in corpo] == [
        "segundo.txt",
        "primeiro.txt",
    ]
    assert all(documento["projeto"]["id"] == 1 for documento in corpo)


def test_processador_deve_atualizar_status_ate_indexado_sem_indexacao_vetorial():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    projeto = _criar_projeto(sessao)
    repositorio = RepositorioDocumentos(sessao)
    documento = repositorio.registrar_documento_recebido(
        projeto_id=projeto.id,
        nome_arquivo="manual.txt",
        hash_conteudo=None,
        tipo_arquivo="txt",
        tamanho_bytes=8,
    )

    ProcessadorDocumentos(
        repositorio=repositorio,
        parser=ParserFalso("Conteudo final extraido."),
        servico_chunking=ChunkingFalso(),
    ).processar_documento(documento.id, "manual.txt", b"conteudo")

    documento_atualizado = repositorio.buscar_documento_por_id(documento.id)
    assert documento_atualizado is not None
    assert documento_atualizado.quantidade_caracteres == len("Conteudo final extraido.")
    assert (
        documento_atualizado.status_processamento
        == StatusProcessamentoDocumento.INDEXADO.value
    )
    assert documento_atualizado.mensagem_erro_processamento is None
    assert len(documento_atualizado.trechos) == 1


def test_processador_deve_persistir_erro_resumido_quando_parser_falhar():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    projeto = _criar_projeto(sessao)
    repositorio = RepositorioDocumentos(sessao)
    documento = repositorio.registrar_documento_recebido(
        projeto_id=projeto.id,
        nome_arquivo="manual.txt",
        hash_conteudo=None,
        tipo_arquivo="txt",
        tamanho_bytes=8,
    )

    ProcessadorDocumentos(
        repositorio=repositorio,
        parser=ParserFalso(texto=None),
        servico_chunking=ChunkingFalso(),
    ).processar_documento(documento.id, "manual.txt", b"conteudo")

    documento_atualizado = repositorio.buscar_documento_por_id(documento.id)
    assert documento_atualizado is not None
    assert (
        documento_atualizado.status_processamento
        == StatusProcessamentoDocumento.ERRO.value
    )
    assert documento_atualizado.mensagem_erro_processamento == "Falha simulada no parser."
    assert documento_atualizado.quantidade_caracteres == 0


def test_dependencia_ingestao_nao_deve_inicializar_embeddings_ao_registrar_ou_buscar(
    monkeypatch,
):
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    projeto = _criar_projeto(sessao)

    def falhar_se_inicializar_embeddings():
        raise AssertionError(
            "Servico de embeddings nao deve ser inicializado na requisicao de ingestao."
        )

    monkeypatch.setattr(
        dependencias,
        "obter_servico_embeddings",
        falhar_se_inicializar_embeddings,
    )

    servico = dependencias.obter_servico_ingestao_documentos(sessao)
    documento = servico.registrar_documento_recebido(
        projeto_id=projeto.id,
        nome_arquivo="manual.txt",
        conteudo_bytes=b"conteudo tecnico",
    )
    documento_consultado = servico.buscar_documento(documento.id)

    assert documento.status_processamento == StatusProcessamentoDocumento.RECEBIDO
    assert documento_consultado is not None
    assert documento_consultado.status_processamento == StatusProcessamentoDocumento.RECEBIDO


def test_servico_ingestao_deve_rejeitar_duplicidade_por_hash():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    projeto = _criar_projeto(sessao)
    servico = ServicoIngestaoDocumentos(
        repositorio=RepositorioDocumentos(sessao),
        parser=ParserFalso(),
        servico_chunking=ChunkingFalso(),
    )

    servico.registrar_documento_recebido(
        projeto_id=projeto.id,
        nome_arquivo="manual.txt",
        conteudo_bytes=b"conteudo tecnico",
        hash_conteudo="abc123",
    )

    try:
        servico.registrar_documento_recebido(
            projeto_id=projeto.id,
            nome_arquivo="manual-copia.txt",
            conteudo_bytes=b"conteudo tecnico",
            hash_conteudo="abc123",
        )
        assert False, "Era esperado erro de documento duplicado."
    except ErroDocumentoDuplicado as erro:
        assert erro.documento_id_existente == 1


def test_agendador_deve_repassar_fabrica_de_embeddings_sem_inicializar_no_agendamento():
    tarefas = TarefasBackgroundFalsas()
    chamadas_fabrica = 0

    def criar_embeddings():
        nonlocal chamadas_fabrica
        chamadas_fabrica += 1
        raise AssertionError("Embeddings devem ser criados apenas na execucao do background task.")

    agendador = AgendadorBackgroundTasksFastAPI(
        tarefas=tarefas,
        fabrica_sessao=lambda: None,
        parser=ParserFalso(),
        servico_chunking=ChunkingFalso(),
        fabrica_servico_embeddings=criar_embeddings,
    )

    agendador.agendar_processamento(1, "manual.txt", b"conteudo")

    assert chamadas_fabrica == 0
    assert len(tarefas.chamadas) == 1
    _, argumentos = tarefas.chamadas[0]
    assert argumentos[-2] is criar_embeddings
    assert isinstance(argumentos[-1], str)


def test_processamento_background_nao_deve_inicializar_embeddings_com_pgvector_desabilitado(
    monkeypatch,
):
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    projeto = _criar_projeto(sessao)
    documento = RepositorioDocumentos(sessao).registrar_documento_recebido(
        projeto_id=projeto.id,
        nome_arquivo="manual.txt",
        hash_conteudo=None,
        tipo_arquivo="txt",
        tamanho_bytes=8,
    )
    documento_id = documento.id
    sessao.close()
    chamadas_fabrica = 0

    def criar_embeddings():
        nonlocal chamadas_fabrica
        chamadas_fabrica += 1
        raise AssertionError("Embeddings nao devem ser criados com pgvector desabilitado.")

    monkeypatch.setattr(
        processamento_documentos,
        "obter_configuracoes",
        lambda: SimpleNamespace(habilitar_pgvector=False, tamanho_lote_indexacao=1),
    )

    executar_processamento_documento_em_nova_sessao(
        documento_id=documento_id,
        nome_arquivo="manual.txt",
        conteudo_bytes=b"conteudo",
        fabrica_sessao=fabrica_sessao,
        parser=ParserFalso("Conteudo extraido."),
        servico_chunking=ChunkingFalso(),
        fabrica_servico_embeddings=criar_embeddings,
    )

    documento_atualizado = RepositorioDocumentos(fabrica_sessao()).buscar_documento_por_id(
        documento_id
    )
    assert chamadas_fabrica == 0
    assert documento_atualizado is not None
    assert (
        documento_atualizado.status_processamento
        == StatusProcessamentoDocumento.INDEXADO.value
    )
