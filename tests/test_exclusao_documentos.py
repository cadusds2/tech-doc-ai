from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dependencias import obter_servico_ingestao_documentos
from app.domain.documento import StatusProcessamentoDocumento
from app.infra.modelos_orm import Base, DocumentoORM, ProjetoORM, TrechoORM
from app.main import app
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.ingestao_documentos import ServicoIngestaoDocumentos


class ParserNaoUtilizado:
    pass


class ChunkingNaoUtilizado:
    pass


def _criar_fabrica_sessao_sqlite():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _criar_servico_ingestao(fabrica_sessao):
    sessao = fabrica_sessao()
    return ServicoIngestaoDocumentos(
        repositorio=RepositorioDocumentos(sessao),
        parser=ParserNaoUtilizado(),
        servico_chunking=ChunkingNaoUtilizado(),
    )


def _criar_projeto(sessao) -> ProjetoORM:
    projeto = ProjetoORM(nome="Projeto Teste", slug="projeto-teste")
    sessao.add(projeto)
    sessao.commit()
    sessao.refresh(projeto)
    return projeto


def _criar_documento(sessao, status_processamento: StatusProcessamentoDocumento):
    projeto = _criar_projeto(sessao)
    documento = DocumentoORM(
        projeto_id=projeto.id,
        nome_arquivo="manual.md",
        tipo_arquivo="md",
        conteudo_extraido="Conteudo processado.",
        tamanho_bytes=128,
        quantidade_caracteres=21,
        status_processamento=status_processamento.value,
    )
    sessao.add(documento)
    sessao.commit()
    sessao.refresh(documento)
    return documento


def _criar_trecho(sessao, documento_id: int):
    trecho = TrechoORM(
        documento_id=documento_id,
        indice_trecho=0,
        indice_inicio=0,
        indice_fim=18,
        tamanho_caracteres=18,
        total_trechos_documento=1,
        conteudo="Trecho vinculado.",
        embedding=None,
        pontuacao_similaridade=None,
    )
    sessao.add(trecho)
    sessao.commit()
    sessao.refresh(trecho)
    return trecho


def _cliente_com_banco(fabrica_sessao):
    app.dependency_overrides[obter_servico_ingestao_documentos] = (
        lambda: _criar_servico_ingestao(fabrica_sessao)
    )
    return TestClient(app)


def test_delete_deve_excluir_documento_existente_e_retornar_confirmacao():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    documento = _criar_documento(sessao, StatusProcessamentoDocumento.INDEXADO)

    try:
        cliente = _cliente_com_banco(fabrica_sessao)
        resposta = cliente.delete(f"/documentos/{documento.id}")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 200
    assert resposta.json() == {
        "documento_id": documento.id,
        "excluido": True,
        "mensagem": "Documento excluido com sucesso.",
    }
    sessao_verificacao = fabrica_sessao()
    assert sessao_verificacao.get(DocumentoORM, documento.id) is None


def test_delete_deve_retornar_404_para_documento_inexistente():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()

    try:
        cliente = _cliente_com_banco(fabrica_sessao)
        resposta = cliente.delete("/documentos/999")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 404
    assert resposta.json() == {"detalhe": "Documento nao encontrado."}


def test_delete_deve_remover_trechos_vinculados_ao_documento():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    documento = _criar_documento(sessao, StatusProcessamentoDocumento.INDEXADO)
    _criar_trecho(sessao, documento.id)

    try:
        cliente = _cliente_com_banco(fabrica_sessao)
        resposta = cliente.delete(f"/documentos/{documento.id}")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 200
    assert (
        sessao.query(TrechoORM).filter(TrechoORM.documento_id == documento.id).count()
        == 0
    )


def test_delete_deve_bloquear_documento_em_processamento():
    fabrica_sessao = _criar_fabrica_sessao_sqlite()
    sessao = fabrica_sessao()
    documento = _criar_documento(sessao, StatusProcessamentoDocumento.RECEBIDO)

    try:
        cliente = _cliente_com_banco(fabrica_sessao)
        resposta = cliente.delete(f"/documentos/{documento.id}")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detalhe": "Documento em processamento nao pode ser excluido."
    }
    sessao_verificacao = fabrica_sessao()
    assert sessao_verificacao.get(DocumentoORM, documento.id) is not None
