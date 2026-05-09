from app.domain.documento import StatusProcessamentoDocumento
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.embeddings import ServicoEmbeddings


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

    def indexar_trechos_pendentes(self, limite: int | None = None, documento_id: int | None = None) -> int:
        limite_consulta = limite or self._tamanho_lote_padrao
        trechos_pendentes = self._repositorio.listar_trechos_sem_embedding(
            limite=limite_consulta,
            documento_id=documento_id,
        )
        if not trechos_pendentes:
            return 0

        textos = [trecho.conteudo for trecho in trechos_pendentes]
        embeddings = self._servico_embeddings.gerar_embeddings(textos)
        mapeamento_embeddings = {trecho.id: embeddings[indice] for indice, trecho in enumerate(trechos_pendentes)}

        self._repositorio.atualizar_embeddings_trechos(mapeamento_embeddings)
        if documento_id is not None:
            self._repositorio.atualizar_status_documento(
                documento_id=documento_id,
                status_processamento=StatusProcessamentoDocumento.INDEXADO,
            )
        return len(trechos_pendentes)

    def preparar_reindexacao_documento(self, documento_id: int) -> int:
        return self._repositorio.limpar_embeddings_documento(documento_id=documento_id)
