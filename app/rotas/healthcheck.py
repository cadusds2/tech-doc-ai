from fastapi import APIRouter

from app.dominio.modelos import RespostaSaude

roteador_saude = APIRouter(prefix="/healthcheck", tags=["saúde"])


@roteador_saude.get("", response_model=RespostaSaude)
def healthcheck() -> RespostaSaude:
    return RespostaSaude()
