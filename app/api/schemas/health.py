from datetime import datetime

from pydantic import BaseModel


class RespostaSaude(BaseModel):
    status: str
    aplicacao: str
    versao: str
    ambiente: str
    horario_utc: datetime
