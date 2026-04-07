from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.configuracao import obter_configuracao
from app.infra.banco import obter_sessao
from app.repositorios.repositorio_documentos import RepositorioDocumentos
from app.servicos.embeddings import ServicoEmbeddings
from app.servicos.parser_documentos import ParserDocumentos
from app.servicos.rag import ServicoRAG


@lru_cache
def obter_servico_embeddings() -> ServicoEmbeddings:
    config = obter_configuracao()
    return ServicoEmbeddings(config.modelo_embeddings, config.dimensao_embeddings)


def obter_servico_rag(sessao: Session = Depends(obter_sessao)) -> ServicoRAG:
    config = obter_configuracao()
    return ServicoRAG(
        config=config,
        repositorio=RepositorioDocumentos(sessao),
        parser=ParserDocumentos(),
        servico_embeddings=obter_servico_embeddings(),
    )
