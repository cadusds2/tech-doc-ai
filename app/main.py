from fastapi import FastAPI

from app.api.router import roteador_api
from app.core.config import obter_configuracoes
from app.core.excecoes import registrar_tratadores_excecao
from app.core.logging import configurar_logging


def criar_aplicacao() -> FastAPI:
    configuracoes = obter_configuracoes()
    configurar_logging(configuracoes)

    app = FastAPI(
        title=configuracoes.nome_app,
        version=configuracoes.versao_app,
        description="API para projeto RAG de documentação técnica.",
    )

    registrar_tratadores_excecao(app)
    app.include_router(roteador_api, prefix=configuracoes.prefixo_api)

    return app


app = criar_aplicacao()
