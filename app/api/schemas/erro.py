from pydantic import BaseModel


class RespostaErro(BaseModel):
    detalhe: str
