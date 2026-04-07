from datetime import datetime

from pydantic import BaseModel


class DocumentoIngerido(BaseModel):
    id: int
    nome_arquivo: str
    tipo_arquivo: str
    tamanho_bytes: int
    quantidade_caracteres: int
    criado_em: datetime
