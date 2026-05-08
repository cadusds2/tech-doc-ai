import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TrechoGerado:
    indice_trecho: int
    conteudo: str
    indice_inicio: int
    indice_fim: int
    tamanho_caracteres: int


@dataclass(frozen=True)
class _UnidadeTexto:
    indice_inicio: int
    indice_fim: int


class EstrategiaChunking(Protocol):
    def gerar_trechos(self, texto: str) -> list[TrechoGerado]:
        ...


def _validar_parametros_chunking(
    tamanho_trecho: int,
    sobreposicao_trecho: int,
    nome_sobreposicao: str = "sobreposicao_trecho",
) -> None:
    if tamanho_trecho <= 0:
        raise ValueError("tamanho_trecho deve ser maior que zero")
    if sobreposicao_trecho < 0:
        raise ValueError(f"{nome_sobreposicao} deve ser maior ou igual a zero")
    if sobreposicao_trecho >= tamanho_trecho:
        raise ValueError(f"{nome_sobreposicao} deve ser menor que tamanho_trecho")


class EstrategiaChunkingTamanhoComSobreposicao:
    def __init__(self, tamanho_trecho: int, sobreposicao: int):
        _validar_parametros_chunking(
            tamanho_trecho=tamanho_trecho,
            sobreposicao_trecho=sobreposicao,
            nome_sobreposicao="sobreposicao",
        )

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


class EstrategiaChunkingEstrutural:
    _padrao_titulo_markdown = re.compile(r"^#{1,6}\s+\S")
    _padrao_lista_markdown = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|[-*+]\s+\[[ xX]\]\s+)")
    _padrao_cerca_codigo = re.compile(r"^\s*(```+|~~~+)")
    _padrao_frase = re.compile(r"[^.!?\s][^.!?]*(?:[.!?]+[\"')\]]*)?")

    def __init__(self, tamanho_trecho: int, sobreposicao_trecho: int):
        _validar_parametros_chunking(
            tamanho_trecho=tamanho_trecho,
            sobreposicao_trecho=sobreposicao_trecho,
        )
        self._tamanho_trecho = tamanho_trecho
        self._sobreposicao_trecho = sobreposicao_trecho

    def gerar_trechos(self, texto: str) -> list[TrechoGerado]:
        if not texto.strip():
            return []

        unidades = self._gerar_unidades(texto)
        if not unidades:
            return []

        trechos: list[TrechoGerado] = []
        inicio = unidades[0].indice_inicio
        fim_texto = unidades[-1].indice_fim

        while inicio < fim_texto:
            fim = self._calcular_fim_trecho(inicio=inicio, unidades=unidades)
            trecho = self._criar_trecho(
                texto=texto,
                indice_trecho=len(trechos),
                inicio=inicio,
                fim=fim,
            )
            if trecho is not None:
                trechos.append(trecho)

            if fim >= fim_texto:
                break

            proximo_inicio = max(inicio + 1, fim - self._sobreposicao_trecho)
            if self._calcular_fim_trecho(inicio=proximo_inicio, unidades=unidades) <= fim:
                proximo_inicio = fim
            inicio = self._avancar_espacos(texto=texto, inicio=proximo_inicio, fim=fim_texto)

        return trechos

    def _gerar_unidades(self, texto: str) -> list[_UnidadeTexto]:
        if self._parece_markdown(texto):
            return self._gerar_unidades_markdown(texto)
        return self._gerar_unidades_texto_simples(texto)

    def _parece_markdown(self, texto: str) -> bool:
        for linha in texto.splitlines():
            if (
                self._padrao_titulo_markdown.match(linha)
                or self._padrao_lista_markdown.match(linha)
                or self._padrao_cerca_codigo.match(linha)
            ):
                return True
        return False

    def _gerar_unidades_markdown(self, texto: str) -> list[_UnidadeTexto]:
        linhas = self._linhas_com_indices(texto)
        unidades: list[_UnidadeTexto] = []
        indice = 0

        while indice < len(linhas):
            inicio, fim, conteudo = linhas[indice]
            if not conteudo.strip():
                indice += 1
                continue

            if self._padrao_cerca_codigo.match(conteudo):
                indice, fim_bloco = self._coletar_bloco_codigo(linhas=linhas, indice_inicial=indice)
                unidades.append(_UnidadeTexto(indice_inicio=inicio, indice_fim=fim_bloco))
                continue

            if self._padrao_titulo_markdown.match(conteudo):
                unidades.append(_UnidadeTexto(indice_inicio=inicio, indice_fim=fim))
                indice += 1
                continue

            if self._padrao_lista_markdown.match(conteudo):
                indice, fim_lista = self._coletar_lista(linhas=linhas, indice_inicial=indice)
                unidades.append(_UnidadeTexto(indice_inicio=inicio, indice_fim=fim_lista))
                continue

            indice, fim_paragrafo = self._coletar_paragrafo_markdown(linhas=linhas, indice_inicial=indice)
            unidades.append(_UnidadeTexto(indice_inicio=inicio, indice_fim=fim_paragrafo))

        return unidades

    def _gerar_unidades_texto_simples(self, texto: str) -> list[_UnidadeTexto]:
        unidades: list[_UnidadeTexto] = []
        for paragrafo in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\s*$)", texto, flags=re.DOTALL):
            inicio_paragrafo, fim_paragrafo = paragrafo.span()
            conteudo_paragrafo = paragrafo.group()
            frases = list(self._padrao_frase.finditer(conteudo_paragrafo))
            frases_validas = [frase for frase in frases if frase.group().strip()]

            if len(frases_validas) <= 1:
                unidades.append(_UnidadeTexto(indice_inicio=inicio_paragrafo, indice_fim=fim_paragrafo))
                continue

            for frase in frases_validas:
                inicio = inicio_paragrafo + frase.start()
                fim = inicio_paragrafo + frase.end()
                inicio = self._avancar_espacos(texto=texto, inicio=inicio, fim=fim)
                fim = self._recuar_espacos(texto=texto, inicio=inicio, fim=fim)
                if inicio < fim:
                    unidades.append(_UnidadeTexto(indice_inicio=inicio, indice_fim=fim))

        return unidades

    def _calcular_fim_trecho(self, inicio: int, unidades: list[_UnidadeTexto]) -> int:
        limite = inicio + self._tamanho_trecho
        fim_escolhido: int | None = None

        for unidade in unidades:
            if unidade.indice_fim <= inicio:
                continue
            if unidade.indice_inicio >= limite:
                break
            if unidade.indice_fim <= limite:
                fim_escolhido = unidade.indice_fim
                continue
            break

        if fim_escolhido is not None and fim_escolhido > inicio:
            return fim_escolhido
        return min(limite, unidades[-1].indice_fim)

    def _criar_trecho(self, texto: str, indice_trecho: int, inicio: int, fim: int) -> TrechoGerado | None:
        inicio_ajustado = self._avancar_espacos(texto=texto, inicio=inicio, fim=fim)
        fim_ajustado = self._recuar_espacos(texto=texto, inicio=inicio_ajustado, fim=fim)
        if inicio_ajustado >= fim_ajustado:
            return None

        conteudo = texto[inicio_ajustado:fim_ajustado]
        return TrechoGerado(
            indice_trecho=indice_trecho,
            conteudo=conteudo,
            indice_inicio=inicio_ajustado,
            indice_fim=fim_ajustado,
            tamanho_caracteres=len(conteudo),
        )

    def _linhas_com_indices(self, texto: str) -> list[tuple[int, int, str]]:
        linhas: list[tuple[int, int, str]] = []
        inicio = 0
        for linha in texto.splitlines(keepends=True):
            fim = inicio + len(linha)
            linhas.append((inicio, fim, linha))
            inicio = fim
        return linhas

    def _coletar_bloco_codigo(self, linhas: list[tuple[int, int, str]], indice_inicial: int) -> tuple[int, int]:
        _, _, primeira_linha = linhas[indice_inicial]
        marcador = self._padrao_cerca_codigo.match(primeira_linha)
        cerca_abertura = marcador.group(1) if marcador else "```"
        caractere_cerca = cerca_abertura[0]
        tamanho_cerca = len(cerca_abertura)
        indice = indice_inicial + 1
        fim_bloco = linhas[indice_inicial][1]

        while indice < len(linhas):
            _, fim_linha, conteudo_linha = linhas[indice]
            fim_bloco = fim_linha
            indice += 1
            if self._linha_fecha_bloco_codigo(
                linha=conteudo_linha,
                caractere_cerca=caractere_cerca,
                tamanho_cerca=tamanho_cerca,
            ):
                break

        return indice, fim_bloco

    def _linha_fecha_bloco_codigo(self, linha: str, caractere_cerca: str, tamanho_cerca: int) -> bool:
        conteudo = linha.lstrip()
        tamanho_fechamento = len(conteudo) - len(conteudo.lstrip(caractere_cerca))
        return tamanho_fechamento >= tamanho_cerca

    def _coletar_lista(self, linhas: list[tuple[int, int, str]], indice_inicial: int) -> tuple[int, int]:
        indice = indice_inicial
        fim_lista = linhas[indice_inicial][1]

        while indice < len(linhas):
            _, fim_linha, conteudo_linha = linhas[indice]
            if not conteudo_linha.strip():
                break
            if indice != indice_inicial and (
                self._padrao_titulo_markdown.match(conteudo_linha)
                or self._padrao_cerca_codigo.match(conteudo_linha)
            ):
                break
            if self._padrao_lista_markdown.match(conteudo_linha) or conteudo_linha.startswith((" ", "\t")):
                fim_lista = fim_linha
                indice += 1
                continue
            break

        return indice, fim_lista

    def _coletar_paragrafo_markdown(self, linhas: list[tuple[int, int, str]], indice_inicial: int) -> tuple[int, int]:
        indice = indice_inicial
        fim_paragrafo = linhas[indice_inicial][1]

        while indice < len(linhas):
            _, fim_linha, conteudo_linha = linhas[indice]
            if not conteudo_linha.strip():
                break
            if indice != indice_inicial and (
                self._padrao_titulo_markdown.match(conteudo_linha)
                or self._padrao_lista_markdown.match(conteudo_linha)
                or self._padrao_cerca_codigo.match(conteudo_linha)
            ):
                break
            fim_paragrafo = fim_linha
            indice += 1

        return indice, fim_paragrafo

    def _avancar_espacos(self, texto: str, inicio: int, fim: int) -> int:
        while inicio < fim and texto[inicio].isspace():
            inicio += 1
        return inicio

    def _recuar_espacos(self, texto: str, inicio: int, fim: int) -> int:
        while fim > inicio and texto[fim - 1].isspace():
            fim -= 1
        return fim


class ServicoChunkingDocumentos:
    def __init__(self, estrategia: EstrategiaChunking):
        self._estrategia = estrategia

    def chunkar_texto(self, texto: str) -> list[TrechoGerado]:
        return self._estrategia.gerar_trechos(texto)
