from fastapi import APIRouter, Depends, Query, status

from app.api.schemas.projetos import (
    ProjetoDetalhado,
    ProjetoResumo,
    RequisicaoCriacaoProjeto,
    RespostaSugestaoProjeto,
)
from app.dependencias import obter_servico_projetos
from app.services.projetos import ServicoProjetos

roteador_projetos = APIRouter(prefix="/projetos", tags=["projetos"])


@roteador_projetos.get("", response_model=list[ProjetoDetalhado])
def listar_projetos(
    limite: int = Query(default=100, ge=1, le=200),
    servico_projetos: ServicoProjetos = Depends(obter_servico_projetos),
) -> list[ProjetoDetalhado]:
    return [
        ProjetoDetalhado(
            id=projeto.id,
            nome=projeto.nome,
            slug=projeto.slug,
            descricao=projeto.descricao,
            criado_em=projeto.criado_em,
            atualizado_em=projeto.atualizado_em,
        )
        for projeto in servico_projetos.listar_projetos(limite=limite)
    ]


@roteador_projetos.post("", response_model=ProjetoDetalhado, status_code=status.HTTP_201_CREATED)
def criar_projeto(
    requisicao: RequisicaoCriacaoProjeto,
    servico_projetos: ServicoProjetos = Depends(obter_servico_projetos),
) -> ProjetoDetalhado:
    projeto = servico_projetos.criar_projeto(
        nome=requisicao.nome,
        descricao=requisicao.descricao,
    )
    return ProjetoDetalhado(
        id=projeto.id,
        nome=projeto.nome,
        slug=projeto.slug,
        descricao=projeto.descricao,
        criado_em=projeto.criado_em,
        atualizado_em=projeto.atualizado_em,
    )


@roteador_projetos.get("/sugestao", response_model=RespostaSugestaoProjeto)
def sugerir_projeto(
    nome_arquivo: str = Query(min_length=1),
    servico_projetos: ServicoProjetos = Depends(obter_servico_projetos),
) -> RespostaSugestaoProjeto:
    sugestao = servico_projetos.sugerir_projeto(nome_arquivo=nome_arquivo)
    projeto_existente = None
    if sugestao.projeto_existente is not None:
        projeto_existente = ProjetoResumo(
            id=sugestao.projeto_existente.id,
            nome=sugestao.projeto_existente.nome,
            slug=sugestao.projeto_existente.slug,
            descricao=sugestao.projeto_existente.descricao,
        )
    return RespostaSugestaoProjeto(
        projeto_existente=projeto_existente,
        nome_sugerido=sugestao.nome_sugerido,
        slug_sugerido=sugestao.slug_sugerido,
        criterio=sugestao.criterio,
    )
