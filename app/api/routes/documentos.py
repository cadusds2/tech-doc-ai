from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.schemas.documentos import RespostaDocumentoIngerido
from app.dependencias import obter_agendador_processamento_documentos, obter_servico_ingestao_documentos
from app.services.ingestao_documentos import ServicoIngestaoDocumentos
from app.services.processamento_documentos import AgendadorProcessamentoDocumentos

roteador_documentos = APIRouter(prefix="/documentos", tags=["documentos"])


@roteador_documentos.post(
    "/ingestao",
    response_model=RespostaDocumentoIngerido,
    status_code=status.HTTP_201_CREATED,
)
async def ingerir_documento(
    arquivo: UploadFile = File(...),
    servico_ingestao: ServicoIngestaoDocumentos = Depends(obter_servico_ingestao_documentos),
    agendador_processamento: AgendadorProcessamentoDocumentos = Depends(obter_agendador_processamento_documentos),
) -> RespostaDocumentoIngerido:
    conteudo = await arquivo.read()
    nome_arquivo = arquivo.filename or "arquivo_sem_nome.txt"
    documento = servico_ingestao.registrar_documento_recebido(nome_arquivo, conteudo)
    agendador_processamento.agendar_processamento(documento.id, nome_arquivo, conteudo)
    return _criar_resposta_documento(documento)


@roteador_documentos.get(
    "/{documento_id}",
    response_model=RespostaDocumentoIngerido,
)
def consultar_documento(
    documento_id: int,
    servico_ingestao: ServicoIngestaoDocumentos = Depends(obter_servico_ingestao_documentos),
) -> RespostaDocumentoIngerido:
    documento = servico_ingestao.buscar_documento(documento_id)
    if documento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    return _criar_resposta_documento(documento)


def _criar_resposta_documento(documento) -> RespostaDocumentoIngerido:
    return RespostaDocumentoIngerido(
        documento_id=documento.id,
        nome_arquivo=documento.nome_arquivo,
        tipo_arquivo=documento.tipo_arquivo,
        tamanho_bytes=documento.tamanho_bytes,
        quantidade_caracteres=documento.quantidade_caracteres,
        status_processamento=documento.status_processamento,
        mensagem_erro_processamento=documento.mensagem_erro_processamento,
        criado_em=documento.criado_em,
        atualizado_em=documento.atualizado_em,
    )
