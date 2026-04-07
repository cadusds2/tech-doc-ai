from pydantic import BaseModel, Field


class RequisicaoPergunta(BaseModel):
    pergunta: str = Field(min_length=3, description="Pergunta do usuário.")
    limite_fontes: int = Field(default=4, ge=1, le=10, description="Quantidade máxima de trechos recuperados.")


class FonteUtilizada(BaseModel):
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao_similaridade: float


class RespostaPergunta(BaseModel):
    resposta: str
    fontes: list[FonteUtilizada]
