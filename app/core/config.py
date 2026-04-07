from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    nome_app: str = "Tech Doc AI"
    versao_app: str = "0.1.0"
    ambiente: str = "desenvolvimento"

    url_banco: str = "postgresql+psycopg://postgres:postgres@localhost:5432/techdocai"
    habilitar_pgvector: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


configuracoes = Configuracoes()
