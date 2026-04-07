from fastapi import FastAPI

from app.api.routes.health import roteador_saude
from app.core.config import configuracoes

app = FastAPI(
    title=configuracoes.nome_app,
    version=configuracoes.versao_app,
    description="API inicial para projeto RAG de documentação técnica.",
)

app.include_router(roteador_saude)
