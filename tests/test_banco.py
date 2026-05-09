from sqlalchemy import create_engine, inspect, text

from app.infra import banco


def test_inicializacao_deve_adicionar_colunas_de_origem_em_trechos_existente(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "CREATE TABLE trechos ("
                "id INTEGER PRIMARY KEY, "
                "documento_id INTEGER, "
                "indice_trecho INTEGER NOT NULL, "
                "conteudo TEXT NOT NULL"
                ")"
            )
        )

    monkeypatch.setattr(banco, "engine", engine)

    banco._garantir_colunas_origem_trechos()
    banco._garantir_colunas_origem_trechos()

    colunas = {coluna["name"] for coluna in inspect(engine).get_columns("trechos")}
    assert {"pagina", "secao", "titulo_contexto", "caminho_hierarquico"}.issubset(colunas)


def test_inicializacao_deve_adicionar_colunas_de_processamento_em_documentos_existente(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "CREATE TABLE documentos ("
                "id INTEGER PRIMARY KEY, "
                "nome_arquivo VARCHAR(255) NOT NULL, "
                "tipo_arquivo VARCHAR(20) NOT NULL, "
                "tamanho_bytes INTEGER NOT NULL, "
                "quantidade_caracteres INTEGER NOT NULL, "
                "conteudo_extraido TEXT NOT NULL"
                ")"
            )
        )

    monkeypatch.setattr(banco, "engine", engine)

    banco._garantir_colunas_processamento_documentos()
    banco._garantir_colunas_processamento_documentos()

    colunas = {coluna["name"] for coluna in inspect(engine).get_columns("documentos")}
    assert {"status_processamento", "mensagem_erro_processamento", "atualizado_em"}.issubset(colunas)


def test_inicializacao_deve_retropreencher_status_processamento_de_documentos_legados(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "CREATE TABLE documentos ("
                "id INTEGER PRIMARY KEY, "
                "nome_arquivo VARCHAR(255) NOT NULL, "
                "tipo_arquivo VARCHAR(20) NOT NULL, "
                "tamanho_bytes INTEGER NOT NULL, "
                "quantidade_caracteres INTEGER NOT NULL, "
                "conteudo_extraido TEXT NOT NULL"
                ")"
            )
        )
        conexao.execute(
            text(
                "CREATE TABLE trechos ("
                "id INTEGER PRIMARY KEY, "
                "documento_id INTEGER, "
                "indice_trecho INTEGER NOT NULL, "
                "conteudo TEXT NOT NULL, "
                "embedding TEXT"
                ")"
            )
        )
        conexao.execute(
            text(
                "INSERT INTO documentos "
                "(id, nome_arquivo, tipo_arquivo, tamanho_bytes, quantidade_caracteres, conteudo_extraido) "
                "VALUES "
                "(1, 'recebido.pdf', 'pdf', 10, 0, ''), "
                "(2, 'texto.pdf', 'pdf', 10, 5, 'texto'), "
                "(3, 'trechos.pdf', 'pdf', 10, 5, 'texto'), "
                "(4, 'indexado.pdf', 'pdf', 10, 5, 'texto'), "
                "(5, 'parcial.pdf', 'pdf', 10, 5, 'texto')"
            )
        )
        conexao.execute(
            text(
                "INSERT INTO trechos (id, documento_id, indice_trecho, conteudo, embedding) "
                "VALUES "
                "(10, 3, 0, 'A', NULL), "
                "(11, 4, 0, 'B', '[0.1]'), "
                "(12, 5, 0, 'C', '[0.2]'), "
                "(13, 5, 1, 'D', NULL)"
            )
        )

    monkeypatch.setattr(banco, "engine", engine)

    banco._garantir_colunas_processamento_documentos()
    banco._garantir_colunas_processamento_documentos()

    with engine.connect() as conexao:
        status_por_id = dict(
            conexao.execute(text("SELECT id, status_processamento FROM documentos ORDER BY id")).all()
        )

    assert status_por_id == {
        1: "recebido",
        2: "texto_extraido",
        3: "trechos_gerados",
        4: "indexado",
        5: "trechos_gerados",
    }
