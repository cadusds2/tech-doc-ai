import re
from dataclasses import dataclass

from sqlalchemy import case, literal, or_

from app.domain.documento import StatusProcessamentoDocumento
from app.infra.modelos_orm import DocumentoORM, TrechoORM
from app.services.chunking import TrechoGerado


@dataclass(frozen=True)
class TrechoSimilarEncontrado:
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao_similaridade: float
    pagina: int | None = None
    secao: str | None = None
    titulo_contexto: str | None = None
    caminho_hierarquico: str | None = None


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
        status_processamento: StatusProcessamentoDocumento = StatusProcessamentoDocumento.TEXTO_EXTRAIDO,
    ) -> DocumentoORM:
        documento = DocumentoORM(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=tipo_arquivo,
            conteudo_extraido=conteudo_extraido,
            tamanho_bytes=tamanho_bytes,
            quantidade_caracteres=quantidade_caracteres,
            status_processamento=status_processamento.value,
            mensagem_erro_processamento=None,
        )
        self.sessao.add(documento)
        self.sessao.commit()
        self.sessao.refresh(documento)
        return documento

    def registrar_documento_recebido(
        self,
        nome_arquivo: str,
        tipo_arquivo: str,
        tamanho_bytes: int,
    ) -> DocumentoORM:
        documento = DocumentoORM(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=tipo_arquivo,
            conteudo_extraido="",
            tamanho_bytes=tamanho_bytes,
            quantidade_caracteres=0,
            status_processamento=StatusProcessamentoDocumento.RECEBIDO.value,
            mensagem_erro_processamento=None,
        )
        self.sessao.add(documento)
        self.sessao.commit()
        self.sessao.refresh(documento)
        return documento

    def buscar_documento_por_id(self, documento_id: int) -> DocumentoORM | None:
        return self.sessao.get(DocumentoORM, documento_id)

    def atualizar_status_documento(
        self,
        documento_id: int,
        status_processamento: StatusProcessamentoDocumento,
        mensagem_erro_processamento: str | None = None,
    ) -> DocumentoORM:
        documento = self._obter_documento_existente(documento_id)
        documento.status_processamento = status_processamento.value
        documento.mensagem_erro_processamento = mensagem_erro_processamento
        self.sessao.commit()
        self.sessao.refresh(documento)
        return documento

    def atualizar_texto_extraido_documento(
        self, documento_id: int, conteudo_extraido: str
    ) -> DocumentoORM:
        documento = self._obter_documento_existente(documento_id)
        documento.conteudo_extraido = conteudo_extraido
        documento.quantidade_caracteres = len(conteudo_extraido)
        documento.status_processamento = (
            StatusProcessamentoDocumento.TEXTO_EXTRAIDO.value
        )
        documento.mensagem_erro_processamento = None
        self.sessao.commit()
        self.sessao.refresh(documento)
        return documento

    def registrar_erro_processamento(
        self, documento_id: int, mensagem_erro: str
    ) -> DocumentoORM:
        return self.atualizar_status_documento(
            documento_id=documento_id,
            status_processamento=StatusProcessamentoDocumento.ERRO,
            mensagem_erro_processamento=mensagem_erro[:500],
        )

    def _obter_documento_existente(self, documento_id: int) -> DocumentoORM:
        documento = self.buscar_documento_por_id(documento_id)
        if documento is None:
            raise ValueError(f"Documento {documento_id} não encontrado.")
        return documento

    def salvar_trechos_documento(
        self, documento_id: int, trechos: list[TrechoGerado]
    ) -> list[TrechoORM]:
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
                pagina=trecho.pagina,
                secao=trecho.secao,
                titulo_contexto=trecho.titulo_contexto,
                caminho_hierarquico=trecho.caminho_hierarquico,
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

        self.atualizar_status_documento(
            documento_id=documento_id,
            status_processamento=StatusProcessamentoDocumento.TRECHOS_GERADOS,
        )

        return trechos_orm

    def listar_trechos_sem_embedding(
        self, limite: int = 100, documento_id: int | None = None
    ) -> list[TrechoORM]:
        consulta = (
            self.sessao.query(TrechoORM)
            .filter(TrechoORM.embedding.is_(None))
            .order_by(TrechoORM.id.asc())
        )
        if documento_id is not None:
            consulta = consulta.filter(TrechoORM.documento_id == documento_id)
        return consulta.limit(limite).all()

    def atualizar_embeddings_trechos(
        self, embeddings_por_trecho_id: dict[int, list[float]]
    ) -> None:
        if not embeddings_por_trecho_id:
            return

        ids_trechos = list(embeddings_por_trecho_id.keys())
        trechos = (
            self.sessao.query(TrechoORM).filter(TrechoORM.id.in_(ids_trechos)).all()
        )
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

    def buscar_trechos_por_texto(
        self, texto_busca: str, limite: int
    ) -> list[TrechoSimilarEncontrado]:
        termos_busca = self._extrair_termos_busca(texto_busca)
        if limite <= 0 or not termos_busca:
            return []

        filtros_termos = [
            TrechoORM.conteudo.ilike(f"%{termo}%") for termo in termos_busca
        ]
        criterios_ordenacao = self._criar_criterios_ordenacao_lexical(
            texto_busca=texto_busca,
            termos_busca=termos_busca,
        )
        consulta = (
            self.sessao.query(
                TrechoORM.id.label("trecho_id"),
                TrechoORM.documento_id.label("documento_id"),
                DocumentoORM.nome_arquivo.label("nome_arquivo"),
                TrechoORM.conteudo.label("conteudo"),
                TrechoORM.pagina.label("pagina"),
                TrechoORM.secao.label("secao"),
                TrechoORM.titulo_contexto.label("titulo_contexto"),
                TrechoORM.caminho_hierarquico.label("caminho_hierarquico"),
            )
            .join(DocumentoORM, DocumentoORM.id == TrechoORM.documento_id)
            .filter(
                DocumentoORM.status_processamento
                == StatusProcessamentoDocumento.INDEXADO.value,
                or_(*filtros_termos),
            )
            .order_by(*criterios_ordenacao)
            .limit(limite * 3)
        )

        resultados = [
            TrechoSimilarEncontrado(
                trecho_id=registro.trecho_id,
                documento_id=registro.documento_id,
                nome_arquivo=registro.nome_arquivo,
                conteudo=registro.conteudo,
                pontuacao_similaridade=self._calcular_pontuacao_lexical(
                    conteudo=registro.conteudo,
                    texto_busca=texto_busca,
                    termos_busca=termos_busca,
                ),
                pagina=registro.pagina,
                secao=registro.secao,
                titulo_contexto=registro.titulo_contexto,
                caminho_hierarquico=registro.caminho_hierarquico,
            )
            for registro in consulta.all()
        ]
        resultados.sort(key=lambda trecho: trecho.pontuacao_similaridade, reverse=True)
        return resultados[:limite]

    @staticmethod
    def _criar_criterios_ordenacao_lexical(texto_busca: str, termos_busca: list[str]):
        total_termos_encontrados = literal(0)
        for termo in termos_busca:
            total_termos_encontrados += case(
                (TrechoORM.conteudo.ilike(f"%{termo}%"), 1),
                else_=0,
            )

        texto_normalizado = texto_busca.strip()
        frase_exata_encontrada = (
            case(
                (TrechoORM.conteudo.ilike(f"%{texto_normalizado}%"), 1),
                else_=0,
            )
            if texto_normalizado
            else literal(0)
        )

        return (
            frase_exata_encontrada.desc(),
            total_termos_encontrados.desc(),
            TrechoORM.id.asc(),
        )

    @staticmethod
    def _extrair_termos_busca(texto_busca: str) -> list[str]:
        termos = re.findall(r"[\wÀ-ÿ]{3,}", texto_busca.lower())
        return list(dict.fromkeys(termos))

    @staticmethod
    def _calcular_pontuacao_lexical(
        conteudo: str, texto_busca: str, termos_busca: list[str]
    ) -> float:
        conteudo_normalizado = conteudo.lower()
        pergunta_normalizada = texto_busca.strip().lower()
        termos_encontrados = sum(
            1 for termo in termos_busca if termo in conteudo_normalizado
        )
        cobertura_termos = termos_encontrados / len(termos_busca)
        bonus_frase_exata = (
            0.25
            if pergunta_normalizada and pergunta_normalizada in conteudo_normalizado
            else 0.0
        )
        return min(1.0, cobertura_termos + bonus_frase_exata)

    def buscar_trechos_similares(
        self, embedding_pergunta: list[float], limite: int
    ) -> list[TrechoSimilarEncontrado]:
        distancia_cosseno = TrechoORM.embedding.cosine_distance(embedding_pergunta)
        consulta = (
            self.sessao.query(
                TrechoORM.id.label("trecho_id"),
                TrechoORM.documento_id.label("documento_id"),
                DocumentoORM.nome_arquivo.label("nome_arquivo"),
                TrechoORM.conteudo.label("conteudo"),
                TrechoORM.pagina.label("pagina"),
                TrechoORM.secao.label("secao"),
                TrechoORM.titulo_contexto.label("titulo_contexto"),
                TrechoORM.caminho_hierarquico.label("caminho_hierarquico"),
                (1 - distancia_cosseno).label("pontuacao_similaridade"),
            )
            .join(DocumentoORM, DocumentoORM.id == TrechoORM.documento_id)
            .filter(
                DocumentoORM.status_processamento
                == StatusProcessamentoDocumento.INDEXADO.value,
                TrechoORM.embedding.is_not(None),
            )
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
                pagina=registro.pagina,
                secao=registro.secao,
                titulo_contexto=registro.titulo_contexto,
                caminho_hierarquico=registro.caminho_hierarquico,
            )
            for registro in consulta.all()
        ]
