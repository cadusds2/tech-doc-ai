from app.domain.documento import DocumentoIngerido, StatusProcessamentoDocumento
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.chunking import ServicoChunkingDocumentos
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.parser_documentos import ErroLeituraDocumento, ServicoParserDocumentos
from app.services.processamento_documentos import ProcessadorDocumentos, extrair_extensao_arquivo


class ServicoIngestaoDocumentos:
    def __init__(
        self,
        repositorio: RepositorioDocumentos,
        parser: ServicoParserDocumentos,
        servico_chunking: ServicoChunkingDocumentos,
        servico_indexacao: ServicoIndexacaoVetorial | None = None,
    ):
        self._repositorio = repositorio
        self._parser = parser
        self._servico_chunking = servico_chunking
        self._servico_indexacao = servico_indexacao

    def registrar_documento_recebido(self, nome_arquivo: str, conteudo_bytes: bytes) -> DocumentoIngerido:
        documento = self._repositorio.registrar_documento_recebido(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=extrair_extensao_arquivo(nome_arquivo),
            tamanho_bytes=len(conteudo_bytes),
        )
        return _criar_documento_ingerido(documento)

    def ingerir_arquivo(self, nome_arquivo: str, conteudo_bytes: bytes) -> DocumentoIngerido:
        documento_recebido = self._repositorio.registrar_documento_recebido(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=extrair_extensao_arquivo(nome_arquivo),
            tamanho_bytes=len(conteudo_bytes),
        )
        ProcessadorDocumentos(
            repositorio=self._repositorio,
            parser=self._parser,
            servico_chunking=self._servico_chunking,
            servico_indexacao=self._servico_indexacao,
        ).processar_documento(
            documento_id=documento_recebido.id,
            nome_arquivo=nome_arquivo,
            conteudo_bytes=conteudo_bytes,
        )
        documento_processado = self._repositorio.buscar_documento_por_id(documento_recebido.id)
        if documento_processado is None:
            raise ErroLeituraDocumento("Documento não encontrado após processamento.")
        return _criar_documento_ingerido(documento_processado)

    def buscar_documento(self, documento_id: int) -> DocumentoIngerido | None:
        documento = self._repositorio.buscar_documento_por_id(documento_id)
        if documento is None:
            return None
        return _criar_documento_ingerido(documento)


def _criar_documento_ingerido(documento) -> DocumentoIngerido:
    return DocumentoIngerido(
        id=documento.id,
        nome_arquivo=documento.nome_arquivo,
        tipo_arquivo=documento.tipo_arquivo,
        tamanho_bytes=documento.tamanho_bytes,
        quantidade_caracteres=documento.quantidade_caracteres,
        status_processamento=StatusProcessamentoDocumento(documento.status_processamento),
        mensagem_erro_processamento=documento.mensagem_erro_processamento,
        criado_em=documento.criado_em,
        atualizado_em=documento.atualizado_em,
    )
