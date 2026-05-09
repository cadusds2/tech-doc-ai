from datetime import datetime

from pydantic import BaseModel

from app.domain.documento import StatusProcessamentoDocumento


class RespostaDocumentoIngerido(BaseModel):
    documento_id: int
    nome_arquivo: str
    tipo_arquivo: str
    tamanho_bytes: int
    quantidade_caracteres: int
    status_processamento: StatusProcessamentoDocumento
    mensagem_erro_processamento: str | None = None
    criado_em: datetime
    atualizado_em: datetime | None = None
