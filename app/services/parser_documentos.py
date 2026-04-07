from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


class ErroTipoArquivoInvalido(ValueError):
    pass


class ErroLeituraDocumento(ValueError):
    pass


class ServicoParserDocumentos:
    tipos_suportados = {".txt", ".md", ".pdf"}

    def extrair_texto(self, nome_arquivo: str, conteudo_bytes: bytes) -> str:
        extensao = Path(nome_arquivo).suffix.lower()

        if extensao not in self.tipos_suportados:
            raise ErroTipoArquivoInvalido(
                f"Tipo de arquivo inválido: {extensao or 'sem_extensao'}. Use .md, .txt ou .pdf."
            )

        if extensao in {".txt", ".md"}:
            return conteudo_bytes.decode("utf-8", errors="ignore").strip()

        try:
            leitor = PdfReader(BytesIO(conteudo_bytes))
            texto_paginas = [pagina.extract_text() or "" for pagina in leitor.pages]
        except Exception as erro:  # noqa: BLE001
            raise ErroLeituraDocumento("Falha ao ler o arquivo PDF enviado.") from erro

        return "\n".join(texto_paginas).strip()
