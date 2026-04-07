from pydantic import BaseModel, Field


class RespostaSaude(BaseModel):
    status: str = "ok"


class RespostaIngestao(BaseModel):
    documento_id: int
    nome_arquivo: str
    quantidade_trechos: int


class RequisicaoPergunta(BaseModel):
    pergunta: str = Field(min_length=3)
    limite: int = Field(default=4, ge=1, le=20)


class FonteResposta(BaseModel):
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao: float


class RespostaPergunta(BaseModel):
    pergunta: str
    resposta: str
    fontes: list[FonteResposta]
