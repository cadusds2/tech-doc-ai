import logging
from contextvars import ContextVar
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Configuracoes

logger = logging.getLogger(__name__)

CABECALHO_IDENTIFICADOR_REQUISICAO = "X-Request-ID"
IDENTIFICADOR_REQUISICAO_PADRAO = "sem-requisicao"
_identificador_requisicao: ContextVar[str] = ContextVar(
    "identificador_requisicao",
    default=IDENTIFICADOR_REQUISICAO_PADRAO,
)


class FiltroIdentificadorRequisicao(logging.Filter):
    def filter(self, registro: logging.LogRecord) -> bool:
        registro.identificador_requisicao = obter_identificador_requisicao()
        return True


class MiddlewareIdentificadorRequisicao:
    def __init__(self, app: ASGIApp):
        self._app = app

    async def __call__(self, escopo: Scope, receber: Receive, enviar: Send) -> None:
        if escopo["type"] != "http":
            await self._app(escopo, receber, enviar)
            return

        identificador = _normalizar_identificador_requisicao(
            _obter_cabecalho(escopo, CABECALHO_IDENTIFICADOR_REQUISICAO)
        )
        marcador = definir_identificador_requisicao(identificador)

        async def enviar_com_identificador(mensagem):
            if mensagem["type"] == "http.response.start":
                cabecalhos = list(mensagem.get("headers", []))
                cabecalhos.append(
                    (
                        CABECALHO_IDENTIFICADOR_REQUISICAO.lower().encode("latin-1"),
                        identificador.encode("latin-1"),
                    )
                )
                mensagem["headers"] = cabecalhos
            await enviar(mensagem)

        logger.info(
            "Início da requisição HTTP.",
            extra={"metodo_http": escopo.get("method"), "caminho": escopo.get("path")},
        )
        try:
            await self._app(escopo, receber, enviar_com_identificador)
        finally:
            logger.info(
                "Fim da requisição HTTP.",
                extra={
                    "metodo_http": escopo.get("method"),
                    "caminho": escopo.get("path"),
                },
            )
            redefinir_identificador_requisicao(marcador)


def configurar_logging(configuracoes: Configuracoes) -> None:
    _configurar_fabrica_registros_log()
    logging.basicConfig(
        level=getattr(logging, configuracoes.nivel_log.upper(), logging.INFO),
        format=configuracoes.formato_log,
    )
    filtro = FiltroIdentificadorRequisicao()
    logging.getLogger().addFilter(filtro)
    for manipulador in logging.getLogger().handlers:
        manipulador.addFilter(filtro)


def obter_identificador_requisicao() -> str:
    return _identificador_requisicao.get()


def definir_identificador_requisicao(identificador: str | None = None):
    return _identificador_requisicao.set(
        _normalizar_identificador_requisicao(identificador)
    )


def redefinir_identificador_requisicao(marcador) -> None:
    _identificador_requisicao.reset(marcador)


def _normalizar_identificador_requisicao(identificador: str | None) -> str:
    identificador_limpo = (identificador or "").strip()
    if identificador_limpo:
        return identificador_limpo[:128]
    return uuid4().hex


def _obter_cabecalho(escopo: Scope, nome_cabecalho: str) -> str | None:
    nome_normalizado = nome_cabecalho.lower().encode("latin-1")
    for nome, valor in escopo.get("headers", []):
        if nome.lower() == nome_normalizado:
            return valor.decode("latin-1")
    return None


def _configurar_fabrica_registros_log() -> None:
    fabrica_atual = logging.getLogRecordFactory()
    if getattr(fabrica_atual, "_inclui_identificador_requisicao", False):
        return

    def criar_registro(*args, **kwargs):
        registro = fabrica_atual(*args, **kwargs)
        registro.identificador_requisicao = obter_identificador_requisicao()
        return registro

    criar_registro._inclui_identificador_requisicao = True
    logging.setLogRecordFactory(criar_registro)
