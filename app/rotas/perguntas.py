from fastapi import APIRouter, Depends

from app.dependencias import obter_servico_rag
from app.dominio.modelos import RequisicaoPergunta, RespostaPergunta
from app.servicos.rag import ServicoRAG

roteador_perguntas = APIRouter(prefix="/perguntas", tags=["perguntas"])


@roteador_perguntas.post("", response_model=RespostaPergunta)
def responder_pergunta(
    requisicao: RequisicaoPergunta,
    servico_rag: ServicoRAG = Depends(obter_servico_rag),
) -> RespostaPergunta:
    return servico_rag.responder_pergunta(requisicao.pergunta, requisicao.limite)
