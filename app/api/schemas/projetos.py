from datetime import datetime

from pydantic import BaseModel, Field


class ProjetoResumo(BaseModel):
    id: int
    nome: str
    slug: str
    descricao: str | None = None


class ProjetoDetalhado(ProjetoResumo):
    criado_em: datetime
    atualizado_em: datetime | None = None


class RequisicaoCriacaoProjeto(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    descricao: str | None = Field(default=None, max_length=2000)


class RespostaSugestaoProjeto(BaseModel):
    projeto_existente: ProjetoResumo | None = None
    nome_sugerido: str | None = None
    slug_sugerido: str | None = None
    criterio: str
