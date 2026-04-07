from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


class ParserDocumentos:
    tipos_suportados = {".txt", ".md", ".pdf"}

    def extrair_texto(self, nome_arquivo: str, conteudo_bytes: bytes) -> str:
        extensao = Path(nome_arquivo).suffix.lower()
        if extensao not in self.tipos_suportados:
            raise ValueError(f"Tipo de arquivo não suportado: {extensao}")

        if extensao in {".txt", ".md"}:
            return conteudo_bytes.decode("utf-8", errors="ignore")

        leitor = PdfReader(BytesIO(conteudo_bytes))
        texto_paginas = [pagina.extract_text() or "" for pagina in leitor.pages]
        return "\n".join(texto_paginas)
