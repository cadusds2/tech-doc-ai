from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ambiente: str = "desenvolvimento"
    host_api: str = "0.0.0.0"
    porta_api: int = 8000

    url_banco: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai"

    modelo_embeddings: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimensao_embeddings: int = 384
    tamanho_trecho: int = 800
    sobreposicao_trecho: int = 120
    limite_busca_padrao: int = 4


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
