from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.config import obter_configuracoes
from app.domain.documento import StatusProcessamentoDocumento

config = obter_configuracoes()


class Base(DeclarativeBase):
    pass


class ProjetoORM(Base):
    __tablename__ = "projetos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    documentos: Mapped[list["DocumentoORM"]] = relationship(back_populates="projeto")


class DocumentoORM(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    projeto_id: Mapped[int | None] = mapped_column(
        ForeignKey("projetos.id"),
        nullable=True,
        index=True,
    )
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    hash_conteudo: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    tipo_arquivo: Mapped[str] = mapped_column(String(20), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantidade_caracteres: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conteudo_extraido: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status_processamento: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=StatusProcessamentoDocumento.RECEBIDO.value,
        index=True,
    )
    mensagem_erro_processamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    projeto: Mapped[ProjetoORM | None] = relationship(back_populates="documentos")
    trechos: Mapped[list["TrechoORM"]] = relationship(
        back_populates="documento",
        cascade="all, delete-orphan",
    )


class TrechoORM(Base):
    __tablename__ = "trechos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("documentos.id", ondelete="CASCADE"),
        index=True,
    )
    indice_trecho: Mapped[int] = mapped_column(Integer, nullable=False)
    indice_inicio: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indice_fim: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tamanho_caracteres: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_trechos_documento: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    pagina: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    titulo_contexto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caminho_hierarquico: Mapped[str | None] = mapped_column(Text, nullable=True)
    pontuacao_similaridade: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(config.dimensao_embeddings),
        nullable=True,
    )

    documento: Mapped[DocumentoORM] = relationship(back_populates="trechos")
