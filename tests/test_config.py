from pathlib import Path

from app.core.config import Configuracoes


def test_configuracao_padrao_deve_definir_metadados_da_api():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.nome_app == "Tech Doc AI"
    assert configuracoes.versao_app == "0.1.0"
    assert configuracoes.ambiente == "desenvolvimento"
    assert configuracoes.host_api == "0.0.0.0"
    assert configuracoes.porta_api == 8000
    assert configuracoes.prefixo_api == ""


def test_configuracao_padrao_deve_definir_logging():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.nivel_log == "INFO"
    assert "%(identificador_requisicao)s" in configuracoes.formato_log


def test_configuracao_padrao_deve_usar_banco_do_docker_compose(monkeypatch):
    monkeypatch.delenv("URL_BANCO", raising=False)

    configuracoes = Configuracoes(_env_file=None)

    assert (
        configuracoes.url_banco
        == "postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai"
    )
    assert configuracoes.habilitar_pgvector is True


def test_configuracao_padrao_deve_definir_embeddings_e_indexacao():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.modelo_embeddings == "sentence-transformers/all-MiniLM-L6-v2"
    assert configuracoes.dimensao_embeddings == 384
    assert configuracoes.tamanho_lote_indexacao == 100


def test_configuracao_padrao_deve_manter_chunking_por_caracteres():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.usar_chunking_por_tokens is False
    assert configuracoes.tamanho_trecho == 800
    assert configuracoes.sobreposicao_trecho == 120
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

    assert configuracoes.limite_busca_padrao == 4
    assert configuracoes.peso_busca_vetorial == 0.7
    assert configuracoes.peso_busca_lexical == 0.3


def test_configuracao_padrao_deve_habilitar_reranqueamento():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.habilitar_reranqueamento is True


def test_configuracao_padrao_deve_definir_limite_upload():
    configuracoes = Configuracoes(_env_file=None)

    assert configuracoes.tamanho_maximo_upload_bytes == 10 * 1024 * 1024


def test_configuracao_legada_deve_reexportar_configuracao_oficial():
    from app.configuracao import Configuracoes as ConfiguracoesLegadas
    from app.configuracao import obter_configuracoes as obter_configuracoes_legadas
    from app.core.config import obter_configuracoes

    assert ConfiguracoesLegadas is Configuracoes
    assert obter_configuracoes_legadas is obter_configuracoes


def test_readme_deve_documentar_variaveis_reais_da_configuracao():
    conteudo_readme = Path("README.md").read_text()

    variaveis_configuradas = {
        nome_campo.upper() for nome_campo in Configuracoes.model_fields
    }

    for nome_variavel in sorted(variaveis_configuradas):
        assert f"`{nome_variavel}`" in conteudo_readme
