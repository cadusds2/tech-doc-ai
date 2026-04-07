from collections.abc import Generator
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.configuracao import obter_configuracao
from app.infra.modelos_orm import Base

config = obter_configuracao()
engine = create_engine(config.url_banco, future=True)
FabricaSessao = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
logger = logging.getLogger(__name__)


def obter_sessao() -> Generator[Session, None, None]:
    sessao = FabricaSessao()
    try:
        yield sessao
    finally:
        sessao.close()


def garantir_extensao_pgvector() -> None:
    with engine.begin() as conexao:
        conexao.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def inicializar_banco() -> None:
    try:
        if config.habilitar_pgvector:
            garantir_extensao_pgvector()
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as erro:
        logger.warning("Inicialização do banco indisponível no momento. A aplicação seguirá ativa. detalhe=%s", erro)
