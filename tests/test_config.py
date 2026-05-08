from app.core.config import Configuracoes


def test_configuracao_padrao_deve_usar_banco_do_docker_compose(monkeypatch):
    monkeypatch.delenv("URL_BANCO", raising=False)

    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.url_banco == "postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai"


def test_configuracao_padrao_deve_manter_chunking_por_caracteres():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.usar_chunking_por_tokens is False
    assert configuracoes.tamanho_maximo_tokens_trecho == 256
    assert configuracoes.sobreposicao_tokens_trecho == 40
