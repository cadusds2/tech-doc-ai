from collections.abc import Callable
import logging
from pathlib import Path
from typing import Protocol

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import obter_configuracoes
from app.core.logging import (
    definir_identificador_requisicao,
    obter_identificador_requisicao,
    redefinir_identificador_requisicao,
)
from app.domain.documento import StatusProcessamentoDocumento
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.chunking import ServicoChunkingDocumentos
from app.services.embeddings import ServicoEmbeddings
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.parser_documentos import ErroLeituraDocumento, ServicoParserDocumentos

logger = logging.getLogger(__name__)


class AgendadorProcessamentoDocumentos(Protocol):
    def agendar_processamento(
        self, documento_id: int, nome_arquivo: str, conteudo_bytes: bytes
    ) -> None:
        """Agenda o processamento para execução fora da requisição principal."""


class ProcessadorDocumentos:
    def __init__(
        self,
        repositorio: RepositorioDocumentos,
        parser: ServicoParserDocumentos,
        servico_chunking: ServicoChunkingDocumentos,
        servico_indexacao: ServicoIndexacaoVetorial | None = None,
    ):
        self._repositorio = repositorio
        self._parser = parser
        self._servico_chunking = servico_chunking
        self._servico_indexacao = servico_indexacao

    def processar_documento(
        self, documento_id: int, nome_arquivo: str, conteudo_bytes: bytes
    ) -> None:
        logger.info(
            "Início da ingestão do documento.",
            extra={
                "documento_id": documento_id,
                "nome_arquivo": nome_arquivo,
                "tamanho_bytes": len(conteudo_bytes),
            },
        )
        try:
            try:
                texto_extraido = self._parser.extrair_texto(
                    nome_arquivo, conteudo_bytes
                )
            except Exception as erro_parser:
                logger.error(
                    "Falha ao executar parser do documento.",
                    extra={
                        "documento_id": documento_id,
                        "nome_arquivo": nome_arquivo,
                        "tipo_erro": type(erro_parser).__name__,
                    },
                )
                raise

            if not texto_extraido:
                erro_parser = ErroLeituraDocumento(
                    "Documento sem conteúdo textual útil."
                )
                logger.warning(
                    "Falha ao executar parser do documento.",
                    extra={
                        "documento_id": documento_id,
                        "nome_arquivo": nome_arquivo,
                        "tipo_erro": type(erro_parser).__name__,
                    },
                )
                raise erro_parser

            self._repositorio.atualizar_texto_extraido_documento(
                documento_id=documento_id,
                conteudo_extraido=texto_extraido,
            )
            trechos = self._servico_chunking.chunkar_texto(texto_extraido)
            logger.info(
                "Trechos gerados para documento.",
                extra={
                    "documento_id": documento_id,
                    "quantidade_trechos": len(trechos),
                },
            )
            self._repositorio.salvar_trechos_documento(
                documento_id=documento_id, trechos=trechos
            )

            quantidade_embeddings_indexados = 0
            if self._servico_indexacao is not None:
                quantidade_embeddings_indexados = (
                    self._servico_indexacao.indexar_trechos_pendentes(
                        documento_id=documento_id
                    )
                )
            else:
                self._repositorio.atualizar_status_documento(
                    documento_id=documento_id,
                    status_processamento=StatusProcessamentoDocumento.INDEXADO,
                )
            logger.info(
                "Fim da ingestão do documento.",
                extra={
                    "documento_id": documento_id,
                    "quantidade_trechos": len(trechos),
                    "quantidade_embeddings_indexados": quantidade_embeddings_indexados,
                },
            )
        except Exception as erro:
            self._repositorio.registrar_erro_processamento(
                documento_id=documento_id,
                mensagem_erro=_resumir_erro_processamento(erro),
            )
            logger.info(
                "Fim da ingestão do documento com erro.",
                extra={"documento_id": documento_id, "tipo_erro": type(erro).__name__},
            )


class AgendadorBackgroundTasksFastAPI:
    def __init__(
        self,
        tarefas: BackgroundTasks,
        fabrica_sessao: Callable[[], Session],
        parser: ServicoParserDocumentos,
        servico_chunking: ServicoChunkingDocumentos,
        fabrica_servico_embeddings: Callable[[], ServicoEmbeddings] | None = None,
    ):
        self._tarefas = tarefas
        self._fabrica_sessao = fabrica_sessao
        self._parser = parser
        self._servico_chunking = servico_chunking
        self._fabrica_servico_embeddings = fabrica_servico_embeddings

    def agendar_processamento(
        self, documento_id: int, nome_arquivo: str, conteudo_bytes: bytes
    ) -> None:
        self._tarefas.add_task(
            executar_processamento_documento_em_nova_sessao,
            documento_id,
            nome_arquivo,
            conteudo_bytes,
            self._fabrica_sessao,
            self._parser,
            self._servico_chunking,
            self._fabrica_servico_embeddings,
            obter_identificador_requisicao(),
        )


def executar_processamento_documento_em_nova_sessao(
    documento_id: int,
    nome_arquivo: str,
    conteudo_bytes: bytes,
    fabrica_sessao: Callable[[], Session],
    parser: ServicoParserDocumentos,
    servico_chunking: ServicoChunkingDocumentos,
    fabrica_servico_embeddings: Callable[[], ServicoEmbeddings] | None = None,
    identificador_requisicao: str | None = None,
) -> None:
    marcador_identificador = definir_identificador_requisicao(identificador_requisicao)
    sessao = fabrica_sessao()
    try:
        repositorio = RepositorioDocumentos(sessao)
        configuracao = obter_configuracoes()
        servico_indexacao = None
        if configuracao.habilitar_pgvector and fabrica_servico_embeddings is not None:
            servico_indexacao = ServicoIndexacaoVetorial(
                repositorio=repositorio,
                servico_embeddings=fabrica_servico_embeddings(),
                tamanho_lote_padrao=configuracao.tamanho_lote_indexacao,
            )
        ProcessadorDocumentos(
            repositorio=repositorio,
            parser=parser,
            servico_chunking=servico_chunking,
            servico_indexacao=servico_indexacao,
        ).processar_documento(
            documento_id=documento_id,
            nome_arquivo=nome_arquivo,
            conteudo_bytes=conteudo_bytes,
        )
    finally:
        sessao.close()
        redefinir_identificador_requisicao(marcador_identificador)


def extrair_extensao_arquivo(nome_arquivo: str) -> str:
    return Path(nome_arquivo).suffix.lower().replace(".", "")


def _resumir_erro_processamento(erro: Exception) -> str:
    mensagem = str(erro).strip() or erro.__class__.__name__
    return mensagem[:500]
