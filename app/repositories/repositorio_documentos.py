from dataclasses import dataclass

from app.infra.modelos_orm import DocumentoORM, TrechoORM
from app.services.chunking import TrechoGerado


@dataclass(frozen=True)
class TrechoSimilarEncontrado:
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao_similaridade: float


class RepositorioDocumentos:
    def __init__(self, sessao):
        self.sessao = sessao

    def salvar_metadados_documento(
        self,
        nome_arquivo: str,
        tipo_arquivo: str,
        conteudo_extraido: str,
        tamanho_bytes: int,
        quantidade_caracteres: int,
    ) -> DocumentoORM:
        documento = DocumentoORM(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=tipo_arquivo,
            conteudo_extraido=conteudo_extraido,
            tamanho_bytes=tamanho_bytes,
            quantidade_caracteres=quantidade_caracteres,
        )
        self.sessao.add(documento)
        self.sessao.commit()
        self.sessao.refresh(documento)
        return documento

    def salvar_trechos_documento(self, documento_id: int, trechos: list[TrechoGerado]) -> list[TrechoORM]:
        total_trechos = len(trechos)
        trechos_orm = [
            TrechoORM(
                documento_id=documento_id,
                indice_trecho=trecho.indice_trecho,
                indice_inicio=trecho.indice_inicio,
                indice_fim=trecho.indice_fim,
                tamanho_caracteres=trecho.tamanho_caracteres,
                total_trechos_documento=total_trechos,
                conteudo=trecho.conteudo,
                embedding=None,
                pontuacao_similaridade=None,
            )
            for trecho in trechos
        ]

        if not trechos_orm:
            return []

        self.sessao.add_all(trechos_orm)
        self.sessao.commit()

        for trecho in trechos_orm:
            self.sessao.refresh(trecho)

        return trechos_orm

    def listar_trechos_sem_embedding(self, limite: int = 100, documento_id: int | None = None) -> list[TrechoORM]:
        consulta = self.sessao.query(TrechoORM).filter(TrechoORM.embedding.is_(None)).order_by(TrechoORM.id.asc())
        if documento_id is not None:
            consulta = consulta.filter(TrechoORM.documento_id == documento_id)
        return consulta.limit(limite).all()

    def atualizar_embeddings_trechos(self, embeddings_por_trecho_id: dict[int, list[float]]) -> None:
        if not embeddings_por_trecho_id:
            return

        ids_trechos = list(embeddings_por_trecho_id.keys())
        trechos = self.sessao.query(TrechoORM).filter(TrechoORM.id.in_(ids_trechos)).all()
        for trecho in trechos:
            trecho.embedding = embeddings_por_trecho_id[trecho.id]

        self.sessao.commit()

    def limpar_embeddings_documento(self, documento_id: int) -> int:
        total_atualizado = (
            self.sessao.query(TrechoORM)
            .filter(TrechoORM.documento_id == documento_id)
            .update({TrechoORM.embedding: None}, synchronize_session=False)
        )
        self.sessao.commit()
        return total_atualizado

    def buscar_trechos_similares(self, embedding_pergunta: list[float], limite: int) -> list[TrechoSimilarEncontrado]:
        distancia_cosseno = TrechoORM.embedding.cosine_distance(embedding_pergunta)
        consulta = (
            self.sessao.query(
                TrechoORM.id.label("trecho_id"),
                TrechoORM.documento_id.label("documento_id"),
                DocumentoORM.nome_arquivo.label("nome_arquivo"),
                TrechoORM.conteudo.label("conteudo"),
                (1 - distancia_cosseno).label("pontuacao_similaridade"),
            )
            .join(DocumentoORM, DocumentoORM.id == TrechoORM.documento_id)
            .filter(TrechoORM.embedding.is_not(None))
            .order_by(distancia_cosseno.asc())
            .limit(limite)
        )

        return [
            TrechoSimilarEncontrado(
                trecho_id=registro.trecho_id,
                documento_id=registro.documento_id,
                nome_arquivo=registro.nome_arquivo,
                conteudo=registro.conteudo,
                pontuacao_similaridade=float(registro.pontuacao_similaridade),
            )
            for registro in consulta.all()
        ]
