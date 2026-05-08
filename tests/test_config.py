from app.core.config import Configuracoes


def test_configuracao_padrao_deve_usar_banco_do_docker_compose(monkeypatch):
    monkeypatch.delenv("URL_BANCO", raising=False)

    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.url_banco == "postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai"
