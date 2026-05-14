from collections.abc import Callable

from app.domain.documento import DocumentoIngerido, StatusProcessamentoDocumento
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.chunking import ServicoChunkingDocumentos
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.parser_documentos import ErroLeituraDocumento, ServicoParserDocumentos
from app.services.processamento_documentos import (
    ProcessadorDocumentos,
    extrair_extensao_arquivo,
)


class ServicoIngestaoDocumentos:
    def __init__(
        self,
        repositorio: RepositorioDocumentos,
        parser: ServicoParserDocumentos,
        servico_chunking: ServicoChunkingDocumentos,
        servico_indexacao: ServicoIndexacaoVetorial | None = None,
        fabrica_servico_indexacao: (
            Callable[[], ServicoIndexacaoVetorial | None] | None
        ) = None,
    ):
        self._repositorio = repositorio
        self._parser = parser
        self._servico_chunking = servico_chunking
        self._servico_indexacao = servico_indexacao
        self._fabrica_servico_indexacao = fabrica_servico_indexacao

    def registrar_documento_recebido(
        self, nome_arquivo: str, conteudo_bytes: bytes, hash_conteudo: str | None = None
    ) -> DocumentoIngerido:
        documento_existente = self._buscar_documento_duplicado(hash_conteudo)
        if documento_existente is not None:
            raise ErroDocumentoDuplicado(documento_id_existente=documento_existente.id)
        documento = self._repositorio.registrar_documento_recebido(
            nome_arquivo=nome_arquivo,
            hash_conteudo=hash_conteudo,
            tipo_arquivo=extrair_extensao_arquivo(nome_arquivo),
            tamanho_bytes=len(conteudo_bytes),
        )
        return _criar_documento_ingerido(documento)

    def ingerir_arquivo(
        self, nome_arquivo: str, conteudo_bytes: bytes, hash_conteudo: str | None = None
    ) -> DocumentoIngerido:
        documento_existente = self._buscar_documento_duplicado(hash_conteudo)
        if documento_existente is not None:
            raise ErroDocumentoDuplicado(documento_id_existente=documento_existente.id)
        documento_recebido = self._repositorio.registrar_documento_recebido(
            nome_arquivo=nome_arquivo,
            hash_conteudo=hash_conteudo,
            tipo_arquivo=extrair_extensao_arquivo(nome_arquivo),
            tamanho_bytes=len(conteudo_bytes),
        )
        ProcessadorDocumentos(
            repositorio=self._repositorio,
            parser=self._parser,
            servico_chunking=self._servico_chunking,
            servico_indexacao=self._obter_servico_indexacao(),
        ).processar_documento(
            documento_id=documento_recebido.id,
            nome_arquivo=nome_arquivo,
            conteudo_bytes=conteudo_bytes,
        )
        documento_processado = self._repositorio.buscar_documento_por_id(
            documento_recebido.id
        )
        if documento_processado is None:
            raise ErroLeituraDocumento("Documento não encontrado após processamento.")
        return _criar_documento_ingerido(documento_processado)

    def _obter_servico_indexacao(self) -> ServicoIndexacaoVetorial | None:
        if self._servico_indexacao is not None:
            return self._servico_indexacao
        if self._fabrica_servico_indexacao is None:
            return None
        self._servico_indexacao = self._fabrica_servico_indexacao()
        return self._servico_indexacao

    def buscar_documento(self, documento_id: int) -> DocumentoIngerido | None:
        documento = self._repositorio.buscar_documento_por_id(documento_id)
        if documento is None:
            return None
        return _criar_documento_ingerido(documento)

    def excluir_documento(self, documento_id: int) -> bool:
        return self._repositorio.excluir_documento(documento_id)

    def _buscar_documento_duplicado(self, hash_conteudo: str | None):
        if not hash_conteudo:
            return None
        return self._repositorio.buscar_documento_por_hash_conteudo(hash_conteudo)


class ErroDocumentoDuplicado(RuntimeError):
    def __init__(self, documento_id_existente: int):
        self.documento_id_existente = documento_id_existente
        super().__init__(
            f"Arquivo duplicado já enviado anteriormente no documento {documento_id_existente}."
        )


def _criar_documento_ingerido(documento) -> DocumentoIngerido:
    return DocumentoIngerido(
        id=documento.id,
        nome_arquivo=documento.nome_arquivo,
        tipo_arquivo=documento.tipo_arquivo,
        tamanho_bytes=documento.tamanho_bytes,
        quantidade_caracteres=documento.quantidade_caracteres,
        status_processamento=StatusProcessamentoDocumento(
            documento.status_processamento
        ),
        mensagem_erro_processamento=documento.mensagem_erro_processamento,
        criado_em=documento.criado_em,
        atualizado_em=documento.atualizado_em,
    )
