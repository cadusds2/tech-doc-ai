from fastapi import APIRouter, Depends

from app.api.schemas.chat import RequisicaoPergunta, RespostaPergunta
from app.dependencias import obter_servico_consulta_rag
from app.services.consulta_rag import ServicoConsultaRAG

roteador_chat = APIRouter(prefix="/chat", tags=["chat"])


@roteador_chat.post("/perguntar", response_model=RespostaPergunta)
def perguntar(
    requisicao: RequisicaoPergunta,
    servico_consulta: ServicoConsultaRAG = Depends(obter_servico_consulta_rag),
) -> RespostaPergunta:
    return servico_consulta.responder_pergunta(
        pergunta=requisicao.pergunta,
        limite_fontes=requisicao.limite_fontes,
        conversation_id=requisicao.conversation_id,
    )
