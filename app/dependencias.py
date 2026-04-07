from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.configuracao import obter_configuracao
from app.infra.banco import obter_sessao
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.chunking import EstrategiaChunkingTamanhoComSobreposicao, ServicoChunkingDocumentos
from app.services.embeddings import ServicoEmbeddings, criar_provedor_embeddings
from app.services.ingestao_documentos import ServicoIngestaoDocumentos
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.parser_documentos import ServicoParserDocumentos


@lru_cache
def obter_servico_parser_documentos() -> ServicoParserDocumentos:
    return ServicoParserDocumentos()


@lru_cache
def obter_servico_chunking_documentos() -> ServicoChunkingDocumentos:
    configuracao = obter_configuracao()
    estrategia = EstrategiaChunkingTamanhoComSobreposicao(
        tamanho_trecho=configuracao.tamanho_trecho,
        sobreposicao=configuracao.sobreposicao_trecho,
    )
    return ServicoChunkingDocumentos(estrategia=estrategia)


@lru_cache
def obter_servico_embeddings() -> ServicoEmbeddings:
    configuracao = obter_configuracao()
    provedor = criar_provedor_embeddings(
        nome_modelo=configuracao.modelo_embeddings,
        dimensao=configuracao.dimensao_embeddings,
    )
    return ServicoEmbeddings(provedor=provedor)


def obter_servico_indexacao_vetorial(sessao: Session = Depends(obter_sessao)) -> ServicoIndexacaoVetorial:
    configuracao = obter_configuracao()
    return ServicoIndexacaoVetorial(
        repositorio=RepositorioDocumentos(sessao),
        servico_embeddings=obter_servico_embeddings(),
        tamanho_lote_padrao=configuracao.tamanho_lote_indexacao,
    )


def obter_servico_ingestao_documentos(sessao: Session = Depends(obter_sessao)) -> ServicoIngestaoDocumentos:
    configuracao = obter_configuracao()
    servico_indexacao: ServicoIndexacaoVetorial | None = None
    if configuracao.habilitar_pgvector:
        servico_indexacao = ServicoIndexacaoVetorial(
            repositorio=RepositorioDocumentos(sessao),
            servico_embeddings=obter_servico_embeddings(),
            tamanho_lote_padrao=configuracao.tamanho_lote_indexacao,
        )
    return ServicoIngestaoDocumentos(
        repositorio=RepositorioDocumentos(sessao),
        parser=obter_servico_parser_documentos(),
        servico_chunking=obter_servico_chunking_documentos(),
        servico_indexacao=servico_indexacao,
    )
