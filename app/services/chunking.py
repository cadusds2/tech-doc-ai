from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TrechoGerado:
    indice_trecho: int
    conteudo: str
    indice_inicio: int
    indice_fim: int
    tamanho_caracteres: int


class EstrategiaChunking(Protocol):
    def gerar_trechos(self, texto: str) -> list[TrechoGerado]:
        ...


class EstrategiaChunkingTamanhoComSobreposicao:
    def __init__(self, tamanho_trecho: int, sobreposicao: int):
        if tamanho_trecho <= 0:
            raise ValueError("tamanho_trecho deve ser maior que zero")
        if sobreposicao < 0:
            raise ValueError("sobreposicao deve ser maior ou igual a zero")
        if sobreposicao >= tamanho_trecho:
            raise ValueError("sobreposicao deve ser menor que tamanho_trecho")

        self._tamanho_trecho = tamanho_trecho
        self._sobreposicao = sobreposicao

    def gerar_trechos(self, texto: str) -> list[TrechoGerado]:
        texto_limpo = " ".join(texto.split())
        if not texto_limpo:
            return []

        passo = self._tamanho_trecho - self._sobreposicao
        trechos: list[TrechoGerado] = []

        for indice_trecho, inicio in enumerate(range(0, len(texto_limpo), passo)):
            fim = min(inicio + self._tamanho_trecho, len(texto_limpo))
            conteudo_trecho = texto_limpo[inicio:fim].strip()
            if not conteudo_trecho:
                continue

            trechos.append(
                TrechoGerado(
                    indice_trecho=indice_trecho,
                    conteudo=conteudo_trecho,
                    indice_inicio=inicio,
                    indice_fim=fim,
                    tamanho_caracteres=len(conteudo_trecho),
                )
            )

            if fim >= len(texto_limpo):
                break

        return trechos


class ServicoChunkingDocumentos:
    def __init__(self, estrategia: EstrategiaChunking):
        self._estrategia = estrategia

    def chunkar_texto(self, texto: str) -> list[TrechoGerado]:
        return self._estrategia.gerar_trechos(texto)
