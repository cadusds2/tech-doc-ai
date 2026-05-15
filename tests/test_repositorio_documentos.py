from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.documento import StatusProcessamentoDocumento
from app.infra.modelos_orm import Base, DocumentoORM, ProjetoORM, TrechoORM
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.consulta_rag import ServicoRecuperacaoHibrida


class _ServicoEmbeddingsFalso:
    def gerar_embeddings(self, textos):
        return [[0.1, 0.2, 0.3] for _ in textos]


class _RepositorioDocumentosSemBuscaVetorial(RepositorioDocumentos):
    def buscar_trechos_similares(self, embedding_pergunta, limite, projeto_id):
        return []


class _ConsultaFalsa:
    def __init__(self):
        self.filtros = []

    def join(self, *args, **kwargs):
        return self

    def filter(self, *criterios):
        self.filtros.extend(criterios)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _SessaoFalsa:
    def __init__(self):
        self.consulta = _ConsultaFalsa()

    def query(self, *args, **kwargs):
        return self.consulta


def _criar_sessao_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _criar_projeto(sessao, nome: str = "Projeto Teste") -> ProjetoORM:
    projeto = ProjetoORM(nome=nome, slug=nome.lower().replace(" ", "-"))
    sessao.add(projeto)
    sessao.flush()
    return projeto


def _adicionar_documento(
    sessao,
    projeto_id: int,
    nome_arquivo: str,
    status: StatusProcessamentoDocumento,
) -> DocumentoORM:
    documento = DocumentoORM(
        projeto_id=projeto_id,
        nome_arquivo=nome_arquivo,
        tipo_arquivo="md",
        conteudo_extraido="",
        tamanho_bytes=0,
        quantidade_caracteres=0,
        status_processamento=status.value,
    )
    sessao.add(documento)
    sessao.flush()
    return documento


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
    projeto = _criar_projeto(sessao)
    documento = _adicionar_documento(
        sessao, projeto.id, "manual.md", StatusProcessamentoDocumento.INDEXADO
    )

    for indice in range(4):
        _adicionar_trecho(
            sessao, documento.id, indice, f"Trecho comum com alfa apenas {indice}."
        )
    _adicionar_trecho(
        sessao,
        documento.id,
        4,
        "Trecho decisivo com alfa beta gamma em sequencia exata.",
    )
    sessao.commit()

    resultado = RepositorioDocumentos(sessao).buscar_trechos_por_texto(
        "alfa beta gamma", limite=1, projeto_id=projeto.id
    )

    assert len(resultado) == 1
    assert (
        resultado[0].conteudo
        == "Trecho decisivo com alfa beta gamma em sequencia exata."
    )
    assert resultado[0].pontuacao_similaridade == 1.0


def test_repositorio_deve_salvar_e_retornar_metadados_de_trechos_lexicais():
    from app.services.chunking import TrechoGerado

    sessao = _criar_sessao_sqlite()
    projeto = _criar_projeto(sessao)
    documento = _adicionar_documento(
        sessao, projeto.id, "manual.md", StatusProcessamentoDocumento.TEXTO_EXTRAIDO
    )
    sessao.commit()

    repositorio = RepositorioDocumentos(sessao)
    repositorio.salvar_trechos_documento(
        documento_id=documento.id,
        trechos=[
            TrechoGerado(
                indice_trecho=0,
                conteudo="Instalacao usa o pacote principal.",
                indice_inicio=0,
                indice_fim=34,
                tamanho_caracteres=34,
                pagina=3,
                secao="Instalacao",
                titulo_contexto="Instalacao",
                caminho_hierarquico="Guia > Instalacao",
            )
        ],
    )
    repositorio.atualizar_status_documento(
        documento.id, StatusProcessamentoDocumento.INDEXADO
    )

    resultado = repositorio.buscar_trechos_por_texto(
        "pacote principal", limite=1, projeto_id=projeto.id
    )

    assert len(resultado) == 1
    assert resultado[0].pagina == 3
    assert resultado[0].secao == "Instalacao"
    assert resultado[0].titulo_contexto == "Instalacao"
    assert resultado[0].caminho_hierarquico == "Guia > Instalacao"


def test_repositorio_deve_manter_metadados_opcionais_ausentes():
    sessao = _criar_sessao_sqlite()
    projeto = _criar_projeto(sessao)
    documento = _adicionar_documento(
        sessao, projeto.id, "notas.txt", StatusProcessamentoDocumento.INDEXADO
    )
    _adicionar_trecho(sessao, documento.id, 0, "Trecho simples sem metadados extras.")
    sessao.commit()

    resultado = RepositorioDocumentos(sessao).buscar_trechos_por_texto(
        "simples", limite=1, projeto_id=projeto.id
    )

    assert resultado[0].pagina is None
    assert resultado[0].secao is None
    assert resultado[0].titulo_contexto is None
    assert resultado[0].caminho_hierarquico is None


def test_busca_lexical_deve_recuperar_apenas_documento_indexado():
    sessao = _criar_sessao_sqlite()
    projeto = _criar_projeto(sessao)
    documentos = [
        _adicionar_documento(
            sessao, projeto.id, "indexado.md", StatusProcessamentoDocumento.INDEXADO
        ),
        _adicionar_documento(
            sessao, projeto.id, "erro.md", StatusProcessamentoDocumento.ERRO
        ),
        _adicionar_documento(
            sessao, projeto.id, "recebido.md", StatusProcessamentoDocumento.RECEBIDO
        ),
        _adicionar_documento(
            sessao,
            projeto.id,
            "trechos.md",
            StatusProcessamentoDocumento.TRECHOS_GERADOS,
        ),
    ]
    for indice, documento in enumerate(documentos):
        _adicionar_trecho(
            sessao,
            documento.id,
            indice,
            f"Conteudo rastreavel para {documento.nome_arquivo}.",
        )
    sessao.commit()

    resultado = RepositorioDocumentos(sessao).buscar_trechos_por_texto(
        "rastreavel", limite=10, projeto_id=projeto.id
    )

    assert [trecho.nome_arquivo for trecho in resultado] == ["indexado.md"]


def test_busca_lexical_deve_filtrar_por_projeto():
    sessao = _criar_sessao_sqlite()
    projeto_a = _criar_projeto(sessao, "Projeto A")
    projeto_b = _criar_projeto(sessao, "Projeto B")
    documento_a = _adicionar_documento(
        sessao, projeto_a.id, "a.md", StatusProcessamentoDocumento.INDEXADO
    )
    documento_b = _adicionar_documento(
        sessao, projeto_b.id, "b.md", StatusProcessamentoDocumento.INDEXADO
    )
    _adicionar_trecho(sessao, documento_a.id, 0, "Termo compartilhado do projeto A.")
    _adicionar_trecho(sessao, documento_b.id, 0, "Termo compartilhado do projeto B.")
    sessao.commit()

    resultado = RepositorioDocumentos(sessao).buscar_trechos_por_texto(
        "compartilhado", limite=10, projeto_id=projeto_a.id
    )

    assert [trecho.nome_arquivo for trecho in resultado] == ["a.md"]


def test_busca_vetorial_deve_filtrar_apenas_documentos_indexados():
    sessao = _SessaoFalsa()

    RepositorioDocumentos(sessao).buscar_trechos_similares(
        [0.1, 0.2, 0.3], limite=5, projeto_id=9
    )

    assert any(
        getattr(criterio.left, "name", None) == "status_processamento"
        and criterio.right.value == StatusProcessamentoDocumento.INDEXADO.value
        for criterio in sessao.consulta.filtros
    )
    assert any(
        getattr(criterio.left, "name", None) == "projeto_id"
        and criterio.right.value == 9
        for criterio in sessao.consulta.filtros
    )


def test_recuperacao_hibrida_nao_deve_usar_fontes_de_documentos_nao_indexados():
    sessao = _criar_sessao_sqlite()
    projeto = _criar_projeto(sessao)
    documento_indexado = _adicionar_documento(
        sessao, projeto.id, "fonte-indexada.md", StatusProcessamentoDocumento.INDEXADO
    )
    documento_nao_indexado = _adicionar_documento(
        sessao,
        projeto.id,
        "fonte-nao-indexada.md",
        StatusProcessamentoDocumento.TRECHOS_GERADOS,
    )
    _adicionar_trecho(
        sessao,
        documento_indexado.id,
        0,
        "Recuperacao hibrida usa somente fonte liberada.",
    )
    _adicionar_trecho(
        sessao,
        documento_nao_indexado.id,
        1,
        "Recuperacao hibrida nao deve usar esta fonte.",
    )
    sessao.commit()

    servico = ServicoRecuperacaoHibrida(
        repositorio=_RepositorioDocumentosSemBuscaVetorial(sessao),
        servico_embeddings=_ServicoEmbeddingsFalso(),
    )

    resultado = servico.recuperar_trechos(
        projeto_id=projeto.id,
        pergunta="recuperacao hibrida fonte",
        limite_fontes=5,
    )

    assert [trecho.nome_arquivo for trecho in resultado] == ["fonte-indexada.md"]
