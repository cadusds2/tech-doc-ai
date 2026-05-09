from dataclasses import dataclass

from app.domain.documento import StatusProcessamentoDocumento
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
        self.status_documento_atualizado = None
        self.chamadas_listagem = []

    def listar_trechos_sem_embedding(self, limite: int, documento_id: int | None = None):
        self.chamadas_listagem.append({"limite": limite, "documento_id": documento_id})
        return self._trechos[:limite]

    def atualizar_embeddings_trechos(self, embeddings_por_trecho_id):
        self.embeddings_atualizados.update(embeddings_por_trecho_id)
        ids_indexados = set(embeddings_por_trecho_id.keys())
        self._trechos = [trecho for trecho in self._trechos if trecho.id not in ids_indexados]

    def atualizar_status_documento(self, documento_id: int, status_processamento: StatusProcessamentoDocumento):
        self.status_documento_atualizado = {
            "documento_id": documento_id,
            "status_processamento": status_processamento,
        }

    def limpar_embeddings_documento(self, documento_id: int):
        self.documento_limpo = documento_id
        return 3


class _ServicoEmbeddingsFalso:
    def gerar_embeddings(self, textos):
        return [[float(indice)] * 3 for indice, _ in enumerate(textos, start=1)]


def test_indexacao_vetorial_deve_indexar_um_lote_de_trechos_pendentes_sem_documento_especifico():
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
    assert repositorio.status_documento_atualizado is None
    assert repositorio.chamadas_listagem == [{"limite": 10, "documento_id": None}]


def test_indexacao_vetorial_deve_processar_todos_lotes_antes_de_marcar_documento_indexado():
    repositorio = _RepositorioFalso(
        [
            _TrechoFalso(id=10, conteudo="A"),
            _TrechoFalso(id=11, conteudo="B"),
            _TrechoFalso(id=12, conteudo="C"),
        ]
    )
    servico = ServicoIndexacaoVetorial(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
        tamanho_lote_padrao=2,
    )

    total = servico.indexar_trechos_pendentes(documento_id=42)

    assert total == 3
    assert set(repositorio.embeddings_atualizados) == {10, 11, 12}
    assert repositorio.status_documento_atualizado == {
        "documento_id": 42,
        "status_processamento": StatusProcessamentoDocumento.INDEXADO,
    }
    assert repositorio.chamadas_listagem == [
        {"limite": 2, "documento_id": 42},
        {"limite": 2, "documento_id": 42},
        {"limite": 2, "documento_id": 42},
    ]


def test_indexacao_vetorial_deve_preparar_reindexacao():
    repositorio = _RepositorioFalso([])
    servico = ServicoIndexacaoVetorial(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
    )

    total = servico.preparar_reindexacao_documento(documento_id=42)

    assert total == 3
    assert repositorio.documento_limpo == 42
