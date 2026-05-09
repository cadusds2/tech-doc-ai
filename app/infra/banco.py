from collections.abc import Generator
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_configuracoes
from app.infra.modelos_orm import Base

config = obter_configuracoes()
engine = create_engine(config.url_banco, future=True)
FabricaSessao = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
logger = logging.getLogger(__name__)


_COLUNAS_ORIGEM_TRECHOS = {
    "pagina": "INTEGER",
    "secao": "VARCHAR(255)",
    "titulo_contexto": "VARCHAR(255)",
    "caminho_hierarquico": "TEXT",
}

_COLUNAS_PROCESSAMENTO_DOCUMENTOS = {
    "status_processamento": "VARCHAR(30) NOT NULL DEFAULT 'recebido'",
    "mensagem_erro_processamento": "TEXT",
    "atualizado_em": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}


def obter_sessao() -> Generator[Session, None, None]:
    sessao = FabricaSessao()
    try:
        yield sessao
    finally:
        sessao.close()


def garantir_extensao_pgvector() -> None:
    with engine.begin() as conexao:
        conexao.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def _garantir_colunas_origem_trechos() -> None:
    _garantir_colunas("trechos", _COLUNAS_ORIGEM_TRECHOS)


def _garantir_colunas_processamento_documentos() -> None:
    _garantir_colunas("documentos", _COLUNAS_PROCESSAMENTO_DOCUMENTOS)


def _garantir_colunas(nome_tabela: str, colunas_necessarias: dict[str, str]) -> None:
    with engine.begin() as conexao:
        inspetor = inspect(conexao)
        if not inspetor.has_table(nome_tabela):
            return

        colunas_existentes = {coluna["name"] for coluna in inspetor.get_columns(nome_tabela)}
        for nome_coluna, tipo_coluna in colunas_necessarias.items():
            if nome_coluna in colunas_existentes:
                continue
            conexao.execute(text(f"ALTER TABLE {nome_tabela} ADD COLUMN {nome_coluna} {tipo_coluna}"))


def inicializar_banco() -> None:
    try:
        if config.habilitar_pgvector:
            garantir_extensao_pgvector()
        Base.metadata.create_all(bind=engine)
        _garantir_colunas_origem_trechos()
        _garantir_colunas_processamento_documentos()
    except SQLAlchemyError as erro:
        logger.warning("Inicialização do banco indisponível no momento. A aplicação seguirá ativa. detalhe=%s", erro)
