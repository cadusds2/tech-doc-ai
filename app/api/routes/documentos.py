from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.schemas.documentos import RespostaDocumentoIngerido
from app.dependencias import obter_servico_ingestao_documentos
from app.services.ingestao_documentos import ServicoIngestaoDocumentos
from app.services.parser_documentos import ErroLeituraDocumento, ErroTipoArquivoInvalido

roteador_documentos = APIRouter(prefix="/documentos", tags=["documentos"])


@roteador_documentos.post(
    "/ingestao",
    response_model=RespostaDocumentoIngerido,
    status_code=status.HTTP_201_CREATED,
)
async def ingerir_documento(
    arquivo: UploadFile = File(...),
    servico_ingestao: ServicoIngestaoDocumentos = Depends(obter_servico_ingestao_documentos),
) -> RespostaDocumentoIngerido:
    try:
        conteudo = await arquivo.read()
        documento = servico_ingestao.ingerir_arquivo(arquivo.filename or "arquivo_sem_nome.txt", conteudo)
    except ErroTipoArquivoInvalido as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except ErroLeituraDocumento as erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro

    return RespostaDocumentoIngerido(
        documento_id=documento.id,
        nome_arquivo=documento.nome_arquivo,
        tipo_arquivo=documento.tipo_arquivo,
        tamanho_bytes=documento.tamanho_bytes,
        quantidade_caracteres=documento.quantidade_caracteres,
        status_processamento="texto_extraido",
        criado_em=documento.criado_em,
    )
