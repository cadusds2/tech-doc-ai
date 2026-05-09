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


def test_repositorio_deve_salvar_e_retornar_metadados_de_trechos_lexicais():
    from app.services.chunking import TrechoGerado

    sessao = _criar_sessao_sqlite()
    documento = DocumentoORM(
        nome_arquivo="manual.md",
        tipo_arquivo="md",
        conteudo_extraido="",
        tamanho_bytes=0,
        quantidade_caracteres=0,
    )
    sessao.add(documento)
    sessao.commit()

    repositorio = RepositorioDocumentos(sessao)
    repositorio.salvar_trechos_documento(
        documento_id=documento.id,
        trechos=[
            TrechoGerado(
                indice_trecho=0,
                conteudo="Instalação usa o pacote principal.",
                indice_inicio=0,
                indice_fim=34,
                tamanho_caracteres=34,
                pagina=3,
                secao="Instalação",
                titulo_contexto="Instalação",
                caminho_hierarquico="Guia > Instalação",
            )
        ],
    )

    resultado = repositorio.buscar_trechos_por_texto("pacote principal", limite=1)

    assert len(resultado) == 1
    assert resultado[0].pagina == 3
    assert resultado[0].secao == "Instalação"
    assert resultado[0].titulo_contexto == "Instalação"
    assert resultado[0].caminho_hierarquico == "Guia > Instalação"


def test_repositorio_deve_manter_metadados_opcionais_ausentes():
    sessao = _criar_sessao_sqlite()
    documento = DocumentoORM(
        nome_arquivo="notas.txt",
        tipo_arquivo="txt",
        conteudo_extraido="",
        tamanho_bytes=0,
        quantidade_caracteres=0,
    )
    sessao.add(documento)
    sessao.flush()
    _adicionar_trecho(sessao, documento.id, 0, "Trecho simples sem metadados extras.")
    sessao.commit()

    resultado = RepositorioDocumentos(sessao).buscar_trechos_por_texto("simples", limite=1)

    assert resultado[0].pagina is None
    assert resultado[0].secao is None
    assert resultado[0].titulo_contexto is None
    assert resultado[0].caminho_hierarquico is None
