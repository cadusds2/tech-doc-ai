from pydantic import BaseModel


class RespostaSaude(BaseModel):
    status: str = "ok"
