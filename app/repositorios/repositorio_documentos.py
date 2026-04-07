from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.infra.modelos_orm import DocumentoORM, TrechoORM


@dataclass
class ResultadoBuscaSemantica:
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao: float


class RepositorioDocumentos:
    def __init__(self, sessao: Session):
        self.sessao = sessao

    def salvar_documento_com_trechos(
        self,
        nome_arquivo: str,
        tipo_arquivo: str,
        trechos: list[str],
        embeddings: list[list[float]],
    ) -> DocumentoORM:
        documento = DocumentoORM(nome_arquivo=nome_arquivo, tipo_arquivo=tipo_arquivo)
        for indice, (trecho, embedding) in enumerate(zip(trechos, embeddings, strict=True)):
            documento.trechos.append(
                TrechoORM(
                    indice_trecho=indice,
                    conteudo=trecho,
                    embedding=embedding,
                )
            )

        self.sessao.add(documento)
        self.sessao.commit()
        self.sessao.refresh(documento)
        return documento

    def buscar_trechos_similares(self, embedding_pergunta: list[float], limite: int) -> list[ResultadoBuscaSemantica]:
        similaridade = TrechoORM.embedding.cosine_distance(embedding_pergunta)
        consulta: Select = (
            select(
                TrechoORM.id,
                TrechoORM.documento_id,
                DocumentoORM.nome_arquivo,
                TrechoORM.conteudo,
                similaridade.label("distancia"),
            )
            .join(DocumentoORM, DocumentoORM.id == TrechoORM.documento_id)
            .order_by(similaridade.asc())
            .limit(limite)
        )

        linhas = self.sessao.execute(consulta).all()
        return [
            ResultadoBuscaSemantica(
                trecho_id=linha.id,
                documento_id=linha.documento_id,
                nome_arquivo=linha.nome_arquivo,
                conteudo=linha.conteudo,
                pontuacao=float(1 - linha.distancia),
            )
            for linha in linhas
        ]
