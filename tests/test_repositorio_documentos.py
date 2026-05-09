from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.modelos_orm import Base, DocumentoORM, TrechoORM
from app.repositories.repositorio_documentos import RepositorioDocumentos


def _criar_sessao_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _adicionar_trecho(sessao, documento_id: int, indice: int, conteudo: str) -> None:
    sessao.add(
        TrechoORM(
            documento_id=documento_id,
            indice_trecho=indice,
            indice_inicio=0,
            indice_fim=len(conteudo),
            tamanho_caracteres=len(conteudo),
            total_trechos_documento=5,
            conteudo=conteudo,
            embedding=None,
            pontuacao_similaridade=None,
        )
    )


def test_busca_lexical_deve_ordenar_candidatos_antes_de_limitar():
    sessao = _criar_sessao_sqlite()
    documento = DocumentoORM(
        nome_arquivo="manual.md",
        tipo_arquivo="md",
        conteudo_extraido="",
        tamanho_bytes=0,
        quantidade_caracteres=0,
    )
    sessao.add(documento)
    sessao.flush()

    for indice in range(4):
        _adicionar_trecho(sessao, documento.id, indice, f"Trecho comum com alfa apenas {indice}.")
    _adicionar_trecho(sessao, documento.id, 4, "Trecho decisivo com alfa beta gamma em sequência exata.")
    sessao.commit()

    resultado = RepositorioDocumentos(sessao).buscar_trechos_por_texto("alfa beta gamma", limite=1)

    assert len(resultado) == 1
    assert resultado[0].conteudo == "Trecho decisivo com alfa beta gamma em sequência exata."
    assert resultado[0].pontuacao_similaridade == 1.0
