from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class StatusProcessamentoDocumento(str, Enum):
    RECEBIDO = "recebido"
    TEXTO_EXTRAIDO = "texto_extraido"
    TRECHOS_GERADOS = "trechos_gerados"
    INDEXADO = "indexado"
    ERRO = "erro"


class ProjetoAssociado(BaseModel):
    id: int
    nome: str
    slug: str
    descricao: str | None = None


class DocumentoIngerido(BaseModel):
    id: int
    nome_arquivo: str
    tipo_arquivo: str
    tamanho_bytes: int
    quantidade_caracteres: int
    status_processamento: StatusProcessamentoDocumento
    mensagem_erro_processamento: str | None = None
    projeto: ProjetoAssociado
    criado_em: datetime
    atualizado_em: datetime | None = None
