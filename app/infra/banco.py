from collections.abc import Generator
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_configuracoes
from app.infra.modelos_orm import Base

config = obter_configuracoes()
engine = create_engine(config.url_banco, future=True)
FabricaSessao = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
logger = logging.getLogger(__name__)


_COLUNAS_ORIGEM_TRECHOS = {
    "pagina": "INTEGER",
    "secao": "VARCHAR(255)",
    "titulo_contexto": "VARCHAR(255)",
    "caminho_hierarquico": "TEXT",
}

_COLUNAS_PROCESSAMENTO_DOCUMENTOS = {
    "hash_conteudo": "VARCHAR(64)",
    "status_processamento": "VARCHAR(30) NOT NULL DEFAULT 'recebido'",
    "mensagem_erro_processamento": "TEXT",
    "atualizado_em": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}


def obter_sessao() -> Generator[Session, None, None]:
    sessao = FabricaSessao()
    try:
        yield sessao
    finally:
        sessao.close()


def garantir_extensao_pgvector() -> None:
    with engine.begin() as conexao:
        conexao.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def _garantir_colunas_origem_trechos() -> None:
    _garantir_colunas("trechos", _COLUNAS_ORIGEM_TRECHOS)


def _garantir_colunas_processamento_documentos() -> None:
    _garantir_colunas("documentos", _COLUNAS_PROCESSAMENTO_DOCUMENTOS)
    _retropreencher_status_processamento_documentos()


def _retropreencher_status_processamento_documentos() -> None:
    with engine.begin() as conexao:
        inspetor = inspect(conexao)
        if not inspetor.has_table("documentos"):
            return

        colunas_documentos = {coluna["name"] for coluna in inspetor.get_columns("documentos")}
        if "status_processamento" not in colunas_documentos:
            return

        _executar_atualizacao_status_documentos(
            conexao,
            """
            UPDATE documentos
            SET atualizado_em = CURRENT_TIMESTAMP
            WHERE atualizado_em IS NULL
            """,
        )

        tem_tabela_trechos = inspetor.has_table("trechos")
        colunas_trechos = (
            {coluna["name"] for coluna in inspetor.get_columns("trechos")} if tem_tabela_trechos else set()
        )
        tem_embedding_trechos = "embedding" in colunas_trechos

        _executar_atualizacao_status_documentos(
            conexao,
            """
            UPDATE documentos
            SET status_processamento = 'texto_extraido',
                atualizado_em = CURRENT_TIMESTAMP
            WHERE status_processamento = 'recebido'
              AND length(trim(coalesce(conteudo_extraido, ''))) > 0
            """,
        )

        if not tem_tabela_trechos:
            return

        _executar_atualizacao_status_documentos(
            conexao,
            """
            UPDATE documentos
            SET status_processamento = 'trechos_gerados',
                atualizado_em = CURRENT_TIMESTAMP
            WHERE status_processamento IN ('recebido', 'texto_extraido')
              AND EXISTS (
                  SELECT 1
                  FROM trechos
                  WHERE trechos.documento_id = documentos.id
              )
            """,
        )

        if not tem_embedding_trechos:
            return

        _executar_atualizacao_status_documentos(
            conexao,
            """
            UPDATE documentos
            SET status_processamento = 'indexado',
                atualizado_em = CURRENT_TIMESTAMP
            WHERE status_processamento IN ('recebido', 'texto_extraido', 'trechos_gerados')
              AND EXISTS (
                  SELECT 1
                  FROM trechos
                  WHERE trechos.documento_id = documentos.id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM trechos
                  WHERE trechos.documento_id = documentos.id
                    AND trechos.embedding IS NULL
              )
            """,
        )


def _executar_atualizacao_status_documentos(conexao, sql: str) -> None:
    conexao.execute(text(sql))


def _garantir_colunas(nome_tabela: str, colunas_necessarias: dict[str, str]) -> None:
    with engine.begin() as conexao:
        inspetor = inspect(conexao)
        if not inspetor.has_table(nome_tabela):
            return

        colunas_existentes = {coluna["name"] for coluna in inspetor.get_columns(nome_tabela)}
        for nome_coluna, tipo_coluna in colunas_necessarias.items():
            if nome_coluna in colunas_existentes:
                continue
            tipo_coluna_compativel = _ajustar_tipo_coluna_para_dialeto(
                conexao.engine.dialect.name, tipo_coluna
            )
            conexao.execute(
                text(f"ALTER TABLE {nome_tabela} ADD COLUMN {nome_coluna} {tipo_coluna_compativel}")
            )


def _ajustar_tipo_coluna_para_dialeto(nome_dialeto: str, tipo_coluna: str) -> str:
    if nome_dialeto != "sqlite":
        return tipo_coluna
    return tipo_coluna.replace(" DEFAULT CURRENT_TIMESTAMP", "")


def inicializar_banco() -> None:
    try:
        if config.habilitar_pgvector:
            garantir_extensao_pgvector()
        Base.metadata.create_all(bind=engine)
        _garantir_colunas_origem_trechos()
        _garantir_colunas_processamento_documentos()
    except SQLAlchemyError as erro:
        logger.warning("Inicialização do banco indisponível no momento. A aplicação seguirá ativa. detalhe=%s", erro)
