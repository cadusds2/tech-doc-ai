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
