import logging
import re
import unicodedata
from hashlib import sha256
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.schemas.documentos import (
    RespostaDocumentoExcluido,
    RespostaDocumentoIngerido,
)
from app.core.config import obter_configuracoes
from app.dependencias import (
    obter_agendador_processamento_documentos,
    obter_servico_ingestao_documentos,
)
from app.domain.documento import StatusProcessamentoDocumento
from app.services.ingestao_documentos import (
    ErroDocumentoDuplicado,
    ServicoIngestaoDocumentos,
)
from app.services.parser_documentos import ServicoParserDocumentos
from app.services.processamento_documentos import AgendadorProcessamentoDocumentos

roteador_documentos = APIRouter(prefix="/documentos", tags=["documentos"])
logger = logging.getLogger(__name__)

EXTENSOES_SUSPEITAS = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".jar",
    ".js",
    ".msi",
    ".php",
    ".ps1",
    ".scr",
    ".sh",
    ".vbs",
}
PADRAO_CARACTERES_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")
MENSAGEM_ARQUIVO_INVALIDO = "Arquivo enviado inválido."
MENSAGEM_ARQUIVO_GRANDE = "Arquivo acima do limite permitido."
MENSAGEM_ARQUIVO_VAZIO = "Arquivo vazio não é permitido."


@roteador_documentos.post(
    "/ingestao",
    response_model=RespostaDocumentoIngerido,
    status_code=status.HTTP_201_CREATED,
)
async def ingerir_documento(
    arquivo: UploadFile = File(...),
    servico_ingestao: ServicoIngestaoDocumentos = Depends(
        obter_servico_ingestao_documentos
    ),
    agendador_processamento: AgendadorProcessamentoDocumentos = Depends(
        obter_agendador_processamento_documentos
    ),
) -> RespostaDocumentoIngerido:
    configuracao = obter_configuracoes()
    nome_arquivo = _normalizar_nome_arquivo(arquivo.filename)
    _validar_nome_arquivo(nome_arquivo)
    conteudo = await _ler_conteudo_validando_tamanho(
        arquivo=arquivo,
        limite_bytes=configuracao.tamanho_maximo_upload_bytes,
        nome_arquivo=nome_arquivo,
    )
    logger.info(
        "Documento recebido para ingestão.",
        extra={"nome_arquivo": nome_arquivo, "tamanho_bytes": len(conteudo)},
    )
    hash_conteudo = sha256(conteudo).hexdigest()
    try:
        documento = servico_ingestao.registrar_documento_recebido(
            nome_arquivo=nome_arquivo,
            conteudo_bytes=conteudo,
            hash_conteudo=hash_conteudo,
        )
    except ErroDocumentoDuplicado as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        ) from erro
    agendador_processamento.agendar_processamento(documento.id, nome_arquivo, conteudo)
    logger.info(
        "Processamento de ingestão agendado.",
        extra={"documento_id": documento.id, "nome_arquivo": nome_arquivo},
    )
    return _criar_resposta_documento(documento)


STATUS_PROCESSAMENTO_COM_EXCLUSAO_BLOQUEADA = {
    StatusProcessamentoDocumento.RECEBIDO,
    StatusProcessamentoDocumento.TEXTO_EXTRAIDO,
    StatusProcessamentoDocumento.TRECHOS_GERADOS,
}


@roteador_documentos.delete(
    "/{documento_id}",
    response_model=RespostaDocumentoExcluido,
)
def excluir_documento(
    documento_id: int,
    servico_ingestao: ServicoIngestaoDocumentos = Depends(
        obter_servico_ingestao_documentos
    ),
) -> RespostaDocumentoExcluido:
    documento = servico_ingestao.buscar_documento(documento_id)
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado."
        )

    if documento.status_processamento in STATUS_PROCESSAMENTO_COM_EXCLUSAO_BLOQUEADA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Documento em processamento não pode ser excluído.",
        )

    excluido = servico_ingestao.excluir_documento(documento_id)
    if not excluido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado."
        )

    return RespostaDocumentoExcluido(
        documento_id=documento_id,
        excluido=True,
        mensagem="Documento excluído com sucesso.",
    )


@roteador_documentos.get(
    "/{documento_id}",
    response_model=RespostaDocumentoIngerido,
)
def consultar_documento(
    documento_id: int,
    servico_ingestao: ServicoIngestaoDocumentos = Depends(
        obter_servico_ingestao_documentos
    ),
) -> RespostaDocumentoIngerido:
    documento = servico_ingestao.buscar_documento(documento_id)
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado."
        )
    return _criar_resposta_documento(documento)


def _normalizar_nome_arquivo(nome_arquivo: str | None) -> str:
    if nome_arquivo is None:
        return ""
    nome_normalizado = unicodedata.normalize("NFKC", nome_arquivo)
    nome_normalizado = nome_normalizado.replace("\\", "/")
    return PurePosixPath(nome_normalizado).name.strip()


def _validar_nome_arquivo(nome_arquivo: str) -> None:
    if not nome_arquivo or nome_arquivo in {".", ".."}:
        _registrar_rejeicao_upload("nome_ausente")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAGEM_ARQUIVO_INVALIDO,
        )

    if PADRAO_CARACTERES_CONTROLE.search(nome_arquivo):
        _registrar_rejeicao_upload("nome_com_caractere_invalido")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAGEM_ARQUIVO_INVALIDO,
        )

    caminho = PurePosixPath(nome_arquivo)
    extensao = caminho.suffix.lower()
    extensoes = {sufixo.lower() for sufixo in caminho.suffixes}
    extensoes_aceitas = ServicoParserDocumentos.tipos_suportados
    if extensao not in extensoes_aceitas or extensoes & EXTENSOES_SUSPEITAS:
        _registrar_rejeicao_upload("extensao_invalida", nome_arquivo=nome_arquivo)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAGEM_ARQUIVO_INVALIDO,
        )


async def _ler_conteudo_validando_tamanho(
    arquivo: UploadFile,
    limite_bytes: int,
    nome_arquivo: str,
) -> bytes:
    conteudo = await arquivo.read(limite_bytes + 1)
    tamanho_bytes = len(conteudo)

    if tamanho_bytes > limite_bytes:
        _registrar_rejeicao_upload(
            "arquivo_acima_limite",
            nome_arquivo=nome_arquivo,
            tamanho_bytes=tamanho_bytes,
            limite_bytes=limite_bytes,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=MENSAGEM_ARQUIVO_GRANDE,
        )

    if tamanho_bytes == 0:
        _registrar_rejeicao_upload("arquivo_vazio", nome_arquivo=nome_arquivo)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAGEM_ARQUIVO_VAZIO,
        )

    return conteudo


def _registrar_rejeicao_upload(
    motivo: str,
    nome_arquivo: str | None = None,
    tamanho_bytes: int | None = None,
    limite_bytes: int | None = None,
) -> None:
    contexto = {"motivo": motivo}
    if nome_arquivo is not None:
        contexto["nome_arquivo"] = nome_arquivo
    if tamanho_bytes is not None:
        contexto["tamanho_bytes_lidos"] = tamanho_bytes
    if limite_bytes is not None:
        contexto["limite_bytes"] = limite_bytes
    logger.warning("Upload de documento rejeitado.", extra=contexto)


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
