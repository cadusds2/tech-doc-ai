import hashlib
from importlib import import_module

import numpy as np


class ServicoEmbeddings:
    def __init__(self, nome_modelo: str, dimensao: int):
        self._dimensao = dimensao
        self._modelo = None

        try:
            sentence_transformers = import_module("sentence_transformers")
            classe_modelo = getattr(sentence_transformers, "SentenceTransformer")
            self._modelo = classe_modelo(nome_modelo)
        except Exception:
            self._modelo = None

    def gerar(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []

        if self._modelo is not None:
            vetores = self._modelo.encode(textos, normalize_embeddings=True)
            return [vetor.tolist() for vetor in vetores]

        return [self._embedding_deterministico(texto) for texto in textos]

    def _embedding_deterministico(self, texto: str) -> list[float]:
        digest = hashlib.sha256(texto.encode("utf-8")).digest()
        valores = np.frombuffer(digest * (self._dimensao // len(digest) + 1), dtype=np.uint8)[: self._dimensao]
        normalizado = (valores.astype(np.float32) / 255.0) * 2 - 1
        norma = np.linalg.norm(normalizado)
        if norma == 0:
            return normalizado.tolist()
        return (normalizado / norma).tolist()
