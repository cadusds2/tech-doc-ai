from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.configuracao import obter_configuracao
from app.infra.banco import obter_sessao
from app.repositories.repositorio_documentos import RepositorioDocumentos
from app.services.ingestao_documentos import ServicoIngestaoDocumentos
from app.services.parser_documentos import ServicoParserDocumentos


@lru_cache
def obter_servico_parser_documentos() -> ServicoParserDocumentos:
    return ServicoParserDocumentos()


def obter_servico_ingestao_documentos(sessao: Session = Depends(obter_sessao)) -> ServicoIngestaoDocumentos:
    _ = obter_configuracao()
    return ServicoIngestaoDocumentos(
        repositorio=RepositorioDocumentos(sessao),
        parser=obter_servico_parser_documentos(),
    )
