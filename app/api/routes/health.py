from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.schemas.health import RespostaSaude
from app.core.config import obter_configuracoes

roteador_saude = APIRouter(prefix="/health", tags=["saúde"])


@roteador_saude.get("", response_model=RespostaSaude)
def obter_saude() -> RespostaSaude:
    configuracoes = obter_configuracoes()

    return RespostaSaude(
        status="ok",
        aplicacao=configuracoes.nome_app,
        versao=configuracoes.versao_app,
        ambiente=configuracoes.ambiente,
        horario_utc=datetime.now(timezone.utc),
    )
