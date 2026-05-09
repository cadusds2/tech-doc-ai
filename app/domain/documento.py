from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class StatusProcessamentoDocumento(StrEnum):
    RECEBIDO = "recebido"
    TEXTO_EXTRAIDO = "texto_extraido"
    TRECHOS_GERADOS = "trechos_gerados"
    INDEXADO = "indexado"
    ERRO = "erro"


class DocumentoIngerido(BaseModel):
    id: int
    nome_arquivo: str
    tipo_arquivo: str
    tamanho_bytes: int
    quantidade_caracteres: int
    status_processamento: StatusProcessamentoDocumento
    mensagem_erro_processamento: str | None = None
    criado_em: datetime
    atualizado_em: datetime | None = None
