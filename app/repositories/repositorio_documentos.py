from app.infra.modelos_orm import DocumentoORM


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
