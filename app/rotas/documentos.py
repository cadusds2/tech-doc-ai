from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencias import obter_servico_rag
from app.dominio.modelos import RespostaIngestao
from app.servicos.rag import ServicoRAG

roteador_documentos = APIRouter(prefix="/documentos", tags=["documentos"])


@roteador_documentos.post("/ingestao", response_model=RespostaIngestao, status_code=status.HTTP_201_CREATED)
async def ingerir_documento(
    arquivo: UploadFile = File(...),
    servico_rag: ServicoRAG = Depends(obter_servico_rag),
) -> RespostaIngestao:
    try:
        conteudo = await arquivo.read()
        documento = servico_rag.ingerir_documento(arquivo.filename or "arquivo_sem_nome.txt", conteudo)
        return RespostaIngestao(
            documento_id=documento.id,
            nome_arquivo=documento.nome_arquivo,
            quantidade_trechos=len(documento.trechos),
        )
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
