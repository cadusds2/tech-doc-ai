from app.services.provedor_modelo_linguagem import (
    ConfiguracaoProvedorModeloLinguagem,
    ProvedorModeloLinguagemOpenAICompativel,
    criar_provedor_modelo_linguagem,
)


def test_provedor_openai_compativel_deve_usar_url_base_configurada():
    provedor = ProvedorModeloLinguagemOpenAICompativel(
        modelo="modelo-teste",
        chave_api="chave-teste",
        url_base="http://localhost:11434/v1/",
    )

    assert provedor._url_api == "http://localhost:11434/v1/chat/completions"


def test_fabrica_deve_repassar_url_base_configurada_para_provedor_externo():
    provedor = criar_provedor_modelo_linguagem(
        ConfiguracaoProvedorModeloLinguagem(
            provedor="openai_compativel",
            modelo="modelo-teste",
            chave_api="chave-teste",
            temperatura=0.1,
            tempo_limite=10.0,
            url_base="https://gateway.exemplo.com/api/v1",
        )
    )

    assert isinstance(provedor, ProvedorModeloLinguagemOpenAICompativel)
    assert provedor._url_api == "https://gateway.exemplo.com/api/v1/chat/completions"
