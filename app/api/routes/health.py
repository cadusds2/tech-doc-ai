from fastapi import APIRouter

from app.api.schemas.health import RespostaSaude

roteador_saude = APIRouter(prefix="/health", tags=["saúde"])


@roteador_saude.get("", response_model=RespostaSaude)
def obter_saude() -> RespostaSaude:
    return RespostaSaude()
