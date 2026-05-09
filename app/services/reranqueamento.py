from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.services.consulta_rag import TrechoRecuperado


class ReranqueadorTrechos(Protocol):
    """Interface para reordenar trechos antes da montagem do contexto RAG."""

    def reranquear(
        self, pergunta: str, trechos: list[TrechoRecuperado]
    ) -> list[TrechoRecuperado]:
        """Retorna os trechos em ordem de utilidade estimada para a pergunta."""
        ...


class ReranqueadorHeuristicoTrechos:
    """Reranqueador simples preparado para futura troca por implementação baseada em modelo."""

    def __init__(
        self,
        peso_termos_pergunta: float = 0.45,
        peso_tamanho_util: float = 0.25,
        peso_pontuacao_original: float = 0.30,
    ):
        self._peso_termos_pergunta = peso_termos_pergunta
        self._peso_tamanho_util = peso_tamanho_util
        self._peso_pontuacao_original = peso_pontuacao_original

    def reranquear(
        self, pergunta: str, trechos: list[TrechoRecuperado]
    ) -> list[TrechoRecuperado]:
        if not trechos:
            return []

        termos_pergunta = self._extrair_termos(pergunta)
        return sorted(
            trechos,
            key=lambda trecho: self._calcular_pontuacao_reranqueamento(
                pergunta_normalizada=self._normalizar_texto(pergunta),
                termos_pergunta=termos_pergunta,
                trecho=trecho,
            ),
            reverse=True,
        )

    def _calcular_pontuacao_reranqueamento(
        self,
        pergunta_normalizada: str,
        termos_pergunta: set[str],
        trecho: TrechoRecuperado,
    ) -> float:
        texto_trecho_normalizado = self._normalizar_texto(trecho.conteudo)
        pontuacao_termos = self._pontuar_presenca_termos(
            termos_pergunta=termos_pergunta,
            texto_trecho_normalizado=texto_trecho_normalizado,
            pergunta_normalizada=pergunta_normalizada,
        )
        pontuacao_tamanho = self._pontuar_tamanho_util(trecho.conteudo)
        pontuacao_original = self._normalizar_pontuacao_original(
            trecho.pontuacao_similaridade
        )

        return (
            self._peso_termos_pergunta * pontuacao_termos
            + self._peso_tamanho_util * pontuacao_tamanho
            + self._peso_pontuacao_original * pontuacao_original
        )

    @classmethod
    def _extrair_termos(cls, texto: str) -> set[str]:
        return {termo for termo in cls._extrair_tokens(texto) if len(termo) >= 3}

    @classmethod
    def _extrair_tokens(cls, texto: str) -> set[str]:
        texto_normalizado = cls._normalizar_texto(texto)
        return set(re.findall(r"\w+", texto_normalizado))

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        texto_sem_acentos = unicodedata.normalize("NFKD", texto)
        texto_sem_acentos = "".join(
            caractere
            for caractere in texto_sem_acentos
            if not unicodedata.combining(caractere)
        )
        return texto_sem_acentos.lower()

    @staticmethod
    def _pontuar_presenca_termos(
        termos_pergunta: set[str],
        texto_trecho_normalizado: str,
        pergunta_normalizada: str,
    ) -> float:
        if not termos_pergunta:
            return 0.0

        termos_trecho = ReranqueadorHeuristicoTrechos._extrair_tokens(
            texto_trecho_normalizado
        )
        termos_encontrados = termos_pergunta & termos_trecho
        pontuacao = len(termos_encontrados) / len(termos_pergunta)
        if (
            pergunta_normalizada.strip()
            and pergunta_normalizada.strip() in texto_trecho_normalizado
        ):
            pontuacao = min(1.0, pontuacao + 0.15)
        return pontuacao

    @staticmethod
    def _pontuar_tamanho_util(conteudo: str) -> float:
        tamanho = len(conteudo.strip())
        if tamanho <= 0:
            return 0.0
        if tamanho < 120:
            return tamanho / 120
        if tamanho <= 1200:
            return 1.0
        return max(0.35, 1.0 - ((tamanho - 1200) / 2400))

    @staticmethod
    def _normalizar_pontuacao_original(pontuacao: float) -> float:
        return min(1.0, max(0.0, pontuacao))
