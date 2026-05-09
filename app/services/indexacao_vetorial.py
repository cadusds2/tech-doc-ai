import logging

from app.domain.documento import StatusProcessamentoDocumento
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.embeddings import ServicoEmbeddings

logger = logging.getLogger(__name__)


class ServicoIndexacaoVetorial:
    def __init__(
        self,
        repositorio: RepositorioDocumentos,
        servico_embeddings: ServicoEmbeddings,
        tamanho_lote_padrao: int = 100,
    ):
        self._repositorio = repositorio
        self._servico_embeddings = servico_embeddings
        self._tamanho_lote_padrao = tamanho_lote_padrao

    def indexar_trechos_pendentes(
        self, limite: int | None = None, documento_id: int | None = None
    ) -> int:
        limite_consulta = limite or self._tamanho_lote_padrao
        total_indexado = 0

        while True:
            trechos_pendentes = self._repositorio.listar_trechos_sem_embedding(
                limite=limite_consulta,
                documento_id=documento_id,
            )
            if not trechos_pendentes:
                if documento_id is not None:
                    self._repositorio.atualizar_status_documento(
                        documento_id=documento_id,
                        status_processamento=StatusProcessamentoDocumento.INDEXADO,
                    )
                return total_indexado

            textos = [trecho.conteudo for trecho in trechos_pendentes]
            embeddings = self._servico_embeddings.gerar_embeddings(textos)
            mapeamento_embeddings = {
                trecho.id: embeddings[indice]
                for indice, trecho in enumerate(trechos_pendentes)
            }

            self._repositorio.atualizar_embeddings_trechos(mapeamento_embeddings)
            total_indexado += len(trechos_pendentes)
            logger.info(
                "Embeddings indexados para trechos.",
                extra={
                    "documento_id": documento_id,
                    "quantidade_embeddings_indexados": len(trechos_pendentes),
                    "total_embeddings_indexados": total_indexado,
                },
            )

            if documento_id is None:
                return total_indexado

    def preparar_reindexacao_documento(self, documento_id: int) -> int:
        return self._repositorio.limpar_embeddings_documento(documento_id=documento_id)
