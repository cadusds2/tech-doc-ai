from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    nome_app: str = "Tech Doc AI"
    versao_app: str = "0.1.0"
    ambiente: str = "desenvolvimento"

    prefixo_api: str = ""

    nivel_log: str = "INFO"
    formato_log: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    url_banco: str = "postgresql+psycopg://postgres:postgres@localhost:5432/techdocai"
    habilitar_pgvector: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
