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
    tamanho_maximo_tokens_trecho: int = 256
    sobreposicao_tokens_trecho: int = 40
    usar_chunking_por_tokens: bool = False
    limite_busca_padrao: int = 4
    peso_busca_vetorial: float = 0.7
    peso_busca_lexical: float = 0.3
    habilitar_reranqueamento: bool = True

    provedor_modelo_linguagem: str = "heuristico"
    modelo_linguagem: str = "gpt-4.1-mini"
    chave_api_modelo_linguagem: str | None = None
    temperatura_modelo_linguagem: float = 0.2
    tempo_limite_modelo_linguagem: float = 30.0
    url_api_modelo_linguagem: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
