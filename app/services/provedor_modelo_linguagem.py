import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from app.services.consulta_rag import MensagemModelo, ProvedorModeloLinguagem, ProvedorModeloLinguagemHeuristico

logger = logging.getLogger(__name__)


class ErroProvedorModeloLinguagem(RuntimeError):
    """Erro seguro para falhas de comunicação ou resposta do provedor externo."""


@dataclass(frozen=True)
class ConfiguracaoProvedorModeloLinguagem:
    provedor: str
    modelo: str
    chave_api: str | None
    temperatura: float
    tempo_limite: float
    url_base: str


class ProvedorModeloLinguagemOpenAICompativel:
    def __init__(
        self,
        modelo: str,
        chave_api: str,
        temperatura: float = 0.2,
        tempo_limite: float = 30.0,
        url_base: str = "https://api.openai.com/v1",
    ):
        if not chave_api or not chave_api.strip():
            raise ValueError("chave_api deve ser informada para o provedor externo de modelo de linguagem")
        if not modelo or not modelo.strip():
            raise ValueError("modelo deve ser informado para o provedor externo de modelo de linguagem")
        if tempo_limite <= 0:
            raise ValueError("tempo_limite deve ser maior que zero")
        if not url_base or not url_base.strip():
            raise ValueError("url_base deve ser informada para o provedor externo de modelo de linguagem")

        self._modelo = modelo
        self._chave_api = chave_api
        self._temperatura = temperatura
        self._tempo_limite = tempo_limite
        self._url_api = self._montar_url_chat_completions(url_base)

    def gerar_texto(self, mensagens: list[MensagemModelo]) -> str:
        corpo = {
            "model": self._modelo,
            "temperature": self._temperatura,
            "messages": [
                {"role": self._normalizar_papel(mensagem.papel), "content": mensagem.conteudo}
                for mensagem in mensagens
            ],
        }

        requisicao = urllib.request.Request(
            self._url_api,
            data=json.dumps(corpo).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._chave_api}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(requisicao, timeout=self._tempo_limite) as resposta_http:
                dados_resposta = json.loads(resposta_http.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            logger.exception(
                "falha_http_provedor_modelo_linguagem",
                extra={
                    "provedor_modelo_linguagem": "openai_compativel",
                    "modelo_linguagem": self._modelo,
                    "status_http": erro.code,
                },
            )
            raise ErroProvedorModeloLinguagem("Falha HTTP ao consultar provedor de modelo de linguagem.") from erro
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
            logger.exception(
                "falha_comunicacao_provedor_modelo_linguagem",
                extra={
                    "provedor_modelo_linguagem": "openai_compativel",
                    "modelo_linguagem": self._modelo,
                    "tipo_erro": type(erro).__name__,
                },
            )
            raise ErroProvedorModeloLinguagem("Falha ao consultar provedor de modelo de linguagem.") from erro

        return self._extrair_texto_resposta(dados_resposta)

    @staticmethod
    def _montar_url_chat_completions(url_base: str) -> str:
        return urljoin(f"{url_base.strip().rstrip('/')}/", "chat/completions")

    @staticmethod
    def _normalizar_papel(papel: str) -> str:
        mapa_papeis = {"sistema": "system", "usuario": "user", "assistente": "assistant"}
        return mapa_papeis.get(papel, papel)

    @staticmethod
    def _extrair_texto_resposta(dados_resposta: dict[str, Any]) -> str:
        try:
            conteudo = dados_resposta["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as erro:
            logger.exception("resposta_invalida_provedor_modelo_linguagem")
            raise ErroProvedorModeloLinguagem("Resposta inválida do provedor de modelo de linguagem.") from erro

        if not isinstance(conteudo, str):
            logger.error("conteudo_invalido_provedor_modelo_linguagem")
            raise ErroProvedorModeloLinguagem("Conteúdo inválido retornado pelo provedor de modelo de linguagem.")

        return conteudo


def criar_provedor_modelo_linguagem(
    configuracao: ConfiguracaoProvedorModeloLinguagem,
) -> ProvedorModeloLinguagem:
    provedor = configuracao.provedor.strip().lower()
    if provedor in {"heuristico", "local"}:
        return ProvedorModeloLinguagemHeuristico()
    if provedor in {"openai", "openai_compativel"}:
        return ProvedorModeloLinguagemOpenAICompativel(
            modelo=configuracao.modelo,
            chave_api=configuracao.chave_api or "",
            temperatura=configuracao.temperatura,
            tempo_limite=configuracao.tempo_limite,
            url_base=configuracao.url_base,
        )
    raise ValueError(f"provedor_modelo_linguagem não suportado: {configuracao.provedor}")
