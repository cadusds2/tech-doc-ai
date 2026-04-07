from pathlib import Path

from app.domain.documento import DocumentoIngerido
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.parser_documentos import ErroLeituraDocumento, ServicoParserDocumentos


class ServicoIngestaoDocumentos:
    def __init__(self, repositorio: RepositorioDocumentos, parser: ServicoParserDocumentos):
        self._repositorio = repositorio
        self._parser = parser

    def ingerir_arquivo(self, nome_arquivo: str, conteudo_bytes: bytes) -> DocumentoIngerido:
        texto_extraido = self._parser.extrair_texto(nome_arquivo, conteudo_bytes)
        if not texto_extraido:
            raise ErroLeituraDocumento("Documento sem conteúdo textual útil.")

        extensao = Path(nome_arquivo).suffix.lower().replace(".", "")
        documento = self._repositorio.salvar_metadados_documento(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=extensao,
            conteudo_extraido=texto_extraido,
            tamanho_bytes=len(conteudo_bytes),
            quantidade_caracteres=len(texto_extraido),
        )

        return DocumentoIngerido(
            id=documento.id,
            nome_arquivo=documento.nome_arquivo,
            tipo_arquivo=documento.tipo_arquivo,
            tamanho_bytes=documento.tamanho_bytes,
            quantidade_caracteres=documento.quantidade_caracteres,
            criado_em=documento.criado_em,
        )
