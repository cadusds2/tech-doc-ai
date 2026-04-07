import logging

from app.core.config import Configuracoes


def configurar_logging(configuracoes: Configuracoes) -> None:
    logging.basicConfig(
        level=getattr(logging, configuracoes.nivel_log.upper(), logging.INFO),
        format=configuracoes.formato_log,
    )
