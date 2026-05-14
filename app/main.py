from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import roteador_api
from app.core.config import obter_configuracoes
from app.core.excecoes import registrar_tratadores_excecao
from app.core.logging import MiddlewareIdentificadorRequisicao, configurar_logging
from app.infra.banco import inicializar_banco

PASTA_WEB = Path(__file__).parent / "web"


def criar_aplicacao() -> FastAPI:
    configuracoes = obter_configuracoes()
    configurar_logging(configuracoes)
    inicializar_banco()

    app = FastAPI(
        title=configuracoes.nome_app,
        version=configuracoes.versao_app,
        description="API para projeto RAG de documentação técnica.",
    )

    app.add_middleware(MiddlewareIdentificadorRequisicao)
    registrar_tratadores_excecao(app)
    app.include_router(roteador_api, prefix=configuracoes.prefixo_api)

    @app.get("/interface", include_in_schema=False)
    def exibir_interface() -> FileResponse:
        return FileResponse(PASTA_WEB / "index.html")

    app.mount(
        "/interface",
        StaticFiles(directory=PASTA_WEB, html=True),
        name="interface_web",
    )

    return app


app = criar_aplicacao()
