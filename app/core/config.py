from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    nome_app: str = "Tech Doc AI"
    versao_app: str = "0.1.0"
    ambiente: str = "desenvolvimento"

    host_api: str = "0.0.0.0"
    porta_api: int = 8000
    prefixo_api: str = ""

    nivel_log: str = "INFO"
    formato_log: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    url_banco: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai"
    habilitar_pgvector: bool = True

    modelo_embeddings: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimensao_embeddings: int = 384
    tamanho_lote_indexacao: int = 100
    tamanho_trecho: int = 800
    sobreposicao_trecho: int = 120
    limite_busca_padrao: int = 4

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
