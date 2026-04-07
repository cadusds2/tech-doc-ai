import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.banco import engine, garantir_extensao_pgvector
from app.infra.modelos_orm import Base
from app.rotas.documentos import roteador_documentos
from app.rotas.healthcheck import roteador_saude
from app.rotas.perguntas import roteador_perguntas

logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_vida(_app: FastAPI):
    try:
        garantir_extensao_pgvector()
        Base.metadata.create_all(bind=engine)
    except Exception as erro:  # pragma: no cover
        logger.warning("Não foi possível inicializar o banco no startup: %s", erro)
    yield


app = FastAPI(title="Tech Doc AI", version="0.1.0", lifespan=ciclo_vida)

app.include_router(roteador_saude)
app.include_router(roteador_documentos)
app.include_router(roteador_perguntas)
