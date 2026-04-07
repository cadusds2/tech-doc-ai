import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def registrar_tratadores_excecao(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def tratar_http_exception(_: Request, excecao: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=excecao.status_code, content={"detalhe": str(excecao.detail)})

    @app.exception_handler(RequestValidationError)
    async def tratar_erro_validacao(_: Request, excecao: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detalhe": "Dados de entrada inválidos."})

    @app.exception_handler(Exception)
    async def tratar_erro_inesperado(_: Request, excecao: Exception) -> JSONResponse:
        logger.exception("Erro inesperado na API", exc_info=excecao)
        return JSONResponse(status_code=500, content={"detalhe": "Erro interno do servidor."})
