from fastapi import APIRouter

from app.api.routes.chat import roteador_chat
from app.api.routes.documentos import roteador_documentos
from app.api.routes.health import roteador_saude

roteador_api = APIRouter()
roteador_api.include_router(roteador_saude)
roteador_api.include_router(roteador_documentos)
roteador_api.include_router(roteador_chat)
