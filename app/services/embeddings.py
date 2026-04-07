import hashlib
import importlib
import importlib.util
import math
from typing import Protocol


class ProvedorEmbeddings(Protocol):
    def gerar_embeddings(self, textos: list[str]) -> list[list[float]]:
        ...


class ProvedorEmbeddingsDeterministico:
    def __init__(self, dimensao: int):
        if dimensao <= 0:
            raise ValueError("dimensao deve ser maior que zero")
        self._dimensao = dimensao

    def gerar_embeddings(self, textos: list[str]) -> list[list[float]]:
        return [self._gerar_embedding_unico(texto) for texto in textos]

    def _gerar_embedding_unico(self, texto: str) -> list[float]:
        digest = hashlib.sha256(texto.encode("utf-8")).digest()
        valores_normalizados: list[float] = []

        while len(valores_normalizados) < self._dimensao:
            for byte in digest:
                valor = (byte / 255.0) * 2 - 1
                valores_normalizados.append(valor)
                if len(valores_normalizados) >= self._dimensao:
                    break

        norma = math.sqrt(sum(valor * valor for valor in valores_normalizados))
        if norma == 0:
            return valores_normalizados

        return [valor / norma for valor in valores_normalizados]


class ServicoEmbeddings:
    def __init__(self, provedor: ProvedorEmbeddings):
        self._provedor = provedor

    def gerar_embeddings(self, textos: list[str]) -> list[list[float]]:
        textos_validos = [texto.strip() for texto in textos if texto and texto.strip()]
        if not textos_validos:
            return []
        return self._provedor.gerar_embeddings(textos_validos)


def criar_provedor_embeddings(nome_modelo: str, dimensao: int) -> ProvedorEmbeddings:
    if importlib.util.find_spec("sentence_transformers") is None:
        return ProvedorEmbeddingsDeterministico(dimensao=dimensao)

    modulo = importlib.import_module("sentence_transformers")
    classe_modelo = getattr(modulo, "SentenceTransformer")
    modelo = classe_modelo(nome_modelo)

    class _ProvedorSentenceTransformers:
        def gerar_embeddings(self, textos: list[str]) -> list[list[float]]:
            vetores = modelo.encode(textos, normalize_embeddings=True)
            return [vetor.tolist() for vetor in vetores]

    return _ProvedorSentenceTransformers()
