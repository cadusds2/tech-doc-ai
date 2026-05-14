import json

import pytest

from app.services.consulta_rag import MensagemModelo, ProvedorModeloLinguagemHeuristico
from app.services.provedor_modelo_linguagem import (
    URL_API_GROQ,
    URL_API_OPENAI,
    ConfiguracaoProvedorModeloLinguagem,
    ProvedorModeloLinguagemOpenAICompativel,
    USER_AGENT_HTTP_PADRAO,
    criar_provedor_modelo_linguagem,
)


class _RespostaHttpFalsa:
    def __enter__(self):
        return self

    def __exit__(self, tipo_erro, erro, rastreamento):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "Resposta do provedor."}}]}).encode("utf-8")


def test_fabrica_deve_criar_provedor_groq_com_endpoint_padrao():
    provedor = criar_provedor_modelo_linguagem(
        ConfiguracaoProvedorModeloLinguagem(
            provedor="groq",
            modelo="llama-3.3-70b-versatile",
            chave_api="chave-teste",
            temperatura=0.2,
            tempo_limite=30.0,
        )
    )

    assert isinstance(provedor, ProvedorModeloLinguagemOpenAICompativel)
    assert provedor.nome_provedor == "groq"
    assert provedor.url_api == URL_API_GROQ


def test_fabrica_deve_manter_openai_com_endpoint_padrao():
    provedor = criar_provedor_modelo_linguagem(
        ConfiguracaoProvedorModeloLinguagem(
            provedor="openai",
            modelo="gpt-4.1-mini",
            chave_api="chave-teste",
            temperatura=0.2,
            tempo_limite=30.0,
        )
    )

    assert isinstance(provedor, ProvedorModeloLinguagemOpenAICompativel)
    assert provedor.nome_provedor == "openai"
    assert provedor.url_api == URL_API_OPENAI


def test_fabrica_deve_respeitar_url_customizada_para_provedor_compativel():
    url_customizada = "https://provedor.exemplo/v1/chat/completions"

    provedor = criar_provedor_modelo_linguagem(
        ConfiguracaoProvedorModeloLinguagem(
            provedor="openai_compativel",
            modelo="modelo-compativel",
            chave_api="chave-teste",
            temperatura=0.2,
            tempo_limite=30.0,
            url_api=url_customizada,
        )
    )

    assert isinstance(provedor, ProvedorModeloLinguagemOpenAICompativel)
    assert provedor.url_api == url_customizada


def test_fabrica_deve_manter_provedor_heuristico_local():
    provedor = criar_provedor_modelo_linguagem(
        ConfiguracaoProvedorModeloLinguagem(
            provedor="local",
            modelo="qualquer",
            chave_api=None,
            temperatura=0.2,
            tempo_limite=30.0,
        )
    )

    assert isinstance(provedor, ProvedorModeloLinguagemHeuristico)


def test_provedor_groq_deve_enviar_requisicao_no_formato_compativel(monkeypatch):
    requisicoes = []

    def abrir_url_falsa(requisicao, timeout):
        requisicoes.append({"requisicao": requisicao, "tempo_limite": timeout})
        return _RespostaHttpFalsa()

    monkeypatch.setattr("urllib.request.urlopen", abrir_url_falsa)
    provedor = ProvedorModeloLinguagemOpenAICompativel(
        modelo="llama-3.3-70b-versatile",
        chave_api="chave-teste",
        temperatura=0.1,
        tempo_limite=12.0,
        url_api=URL_API_GROQ,
        nome_provedor="groq",
    )

    resposta = provedor.gerar_texto(
        [
            MensagemModelo(papel="sistema", conteudo="Responda em português brasileiro."),
            MensagemModelo(papel="usuario", conteudo="Explique RAG."),
        ]
    )

    corpo = json.loads(requisicoes[0]["requisicao"].data.decode("utf-8"))
    assert resposta == "Resposta do provedor."
    assert requisicoes[0]["requisicao"].full_url == URL_API_GROQ
    assert requisicoes[0]["tempo_limite"] == 12.0
    assert requisicoes[0]["requisicao"].headers["User-agent"] == USER_AGENT_HTTP_PADRAO
    assert corpo["model"] == "llama-3.3-70b-versatile"
    assert corpo["temperature"] == 0.1
    assert corpo["messages"] == [
        {"role": "system", "content": "Responda em português brasileiro."},
        {"role": "user", "content": "Explique RAG."},
    ]


def test_provedor_externo_deve_exigir_chave_api():
    with pytest.raises(ValueError, match="chave_api"):
        criar_provedor_modelo_linguagem(
            ConfiguracaoProvedorModeloLinguagem(
                provedor="groq",
                modelo="llama-3.3-70b-versatile",
                chave_api=None,
                temperatura=0.2,
                tempo_limite=30.0,
            )
        )
