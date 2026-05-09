from app.core.config import Configuracoes


def test_configuracao_padrao_deve_usar_banco_do_docker_compose(monkeypatch):
    monkeypatch.delenv("URL_BANCO", raising=False)

    configuracoes = Configuracoes(_env_file=None)

    assert (
        configuracoes.url_banco
        == "postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai"
    )


def test_configuracao_padrao_deve_manter_chunking_por_caracteres():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.usar_chunking_por_tokens is False
    assert configuracoes.tamanho_maximo_tokens_trecho == 256
    assert configuracoes.sobreposicao_tokens_trecho == 40


def test_configuracao_padrao_deve_manter_provedor_modelo_linguagem_local():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.provedor_modelo_linguagem == "heuristico"
    assert configuracoes.modelo_linguagem == "gpt-4.1-mini"
    assert configuracoes.chave_api_modelo_linguagem is None
    assert configuracoes.temperatura_modelo_linguagem == 0.2
    assert configuracoes.tempo_limite_modelo_linguagem == 30.0
    assert configuracoes.url_api_modelo_linguagem is None


def test_configuracao_padrao_deve_definir_pesos_da_busca_hibrida():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.peso_busca_vetorial == 0.7
    assert configuracoes.peso_busca_lexical == 0.3


def test_configuracao_padrao_deve_habilitar_reranqueamento():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.habilitar_reranqueamento is True
