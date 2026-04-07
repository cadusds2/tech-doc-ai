from dataclasses import dataclass

from app.services.indexacao_vetorial import ServicoIndexacaoVetorial


@dataclass
class _TrechoFalso:
    id: int
    conteudo: str


class _RepositorioFalso:
    def __init__(self, trechos):
        self._trechos = trechos
        self.embeddings_atualizados = {}
        self.documento_limpo = None

    def listar_trechos_sem_embedding(self, limite: int, documento_id: int | None = None):
        return self._trechos[:limite]

    def atualizar_embeddings_trechos(self, embeddings_por_trecho_id):
        self.embeddings_atualizados = embeddings_por_trecho_id

    def limpar_embeddings_documento(self, documento_id: int):
        self.documento_limpo = documento_id
        return 3


class _ServicoEmbeddingsFalso:
    def gerar_embeddings(self, textos):
        return [[float(indice)] * 3 for indice, _ in enumerate(textos, start=1)]


def test_indexacao_vetorial_deve_indexar_trechos_pendentes():
    repositorio = _RepositorioFalso([_TrechoFalso(id=10, conteudo="A"), _TrechoFalso(id=11, conteudo="B")])
    servico = ServicoIndexacaoVetorial(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
        tamanho_lote_padrao=10,
    )

    total = servico.indexar_trechos_pendentes()

    assert total == 2
    assert repositorio.embeddings_atualizados[10] == [1.0, 1.0, 1.0]
    assert repositorio.embeddings_atualizados[11] == [2.0, 2.0, 2.0]


def test_indexacao_vetorial_deve_preparar_reindexacao():
    repositorio = _RepositorioFalso([])
    servico = ServicoIndexacaoVetorial(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
    )

    total = servico.preparar_reindexacao_documento(documento_id=42)

    assert total == 3
    assert repositorio.documento_limpo == 42
