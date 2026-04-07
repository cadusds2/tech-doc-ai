import pytest

from app.services.parser_documentos import ErroTipoArquivoInvalido, ServicoParserDocumentos


class _PaginaFalsa:
    def __init__(self, texto: str):
        self._texto = texto

    def extract_text(self) -> str:
        return self._texto


class _LeitorPdfFalso:
    def __init__(self, _conteudo):
        self.pages = [_PaginaFalsa("Primeira página"), _PaginaFalsa("Segunda página")]


def test_parser_deve_extrair_texto_de_arquivo_txt():
    parser = ServicoParserDocumentos()

    texto = parser.extrair_texto("manual.txt", b"conteudo tecnico")

    assert texto == "conteudo tecnico"


def test_parser_deve_extrair_texto_de_arquivo_md():
    parser = ServicoParserDocumentos()

    texto = parser.extrair_texto("guia.md", b"# Titulo\n\nDescricao")

    assert "Titulo" in texto


def test_parser_deve_extrair_texto_de_pdf(monkeypatch):
    parser = ServicoParserDocumentos()
    monkeypatch.setattr("app.services.parser_documentos.PdfReader", _LeitorPdfFalso)

    texto = parser.extrair_texto("manual.pdf", b"%PDF-simulado")

    assert texto == "Primeira página\nSegunda página"


def test_parser_deve_rejeitar_tipo_invalido():
    parser = ServicoParserDocumentos()

    with pytest.raises(ErroTipoArquivoInvalido):
        parser.extrair_texto("planilha.csv", b"a,b,c")
