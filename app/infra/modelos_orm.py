from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.configuracao import obter_configuracao

config = obter_configuracao()


class Base(DeclarativeBase):
    pass


class DocumentoORM(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_arquivo: Mapped[str] = mapped_column(String(20), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantidade_caracteres: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conteudo_extraido: Mapped[str] = mapped_column(Text, nullable=False, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    trechos: Mapped[list["TrechoORM"]] = relationship(back_populates="documento", cascade="all, delete-orphan")


class TrechoORM(Base):
    __tablename__ = "trechos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    indice_trecho: Mapped[int] = mapped_column(Integer, nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    pontuacao_similaridade: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(config.dimensao_embeddings), nullable=False)

    documento: Mapped[DocumentoORM] = relationship(back_populates="trechos")
