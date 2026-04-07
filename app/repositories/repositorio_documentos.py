from app.infra.modelos_orm import DocumentoORM, TrechoORM
from app.services.chunking import TrechoGerado


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
