from datetime import datetime

from pydantic import BaseModel


class RespostaDocumentoIngerido(BaseModel):
    documento_id: int
    nome_arquivo: str
    tipo_arquivo: str
    tamanho_bytes: int
    quantidade_caracteres: int
    status_processamento: str
    criado_em: datetime
