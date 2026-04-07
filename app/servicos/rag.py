from app.configuracao import Configuracao
from app.dominio.modelos import FonteResposta, RespostaPergunta
from app.repositorios.repositorio_documentos import RepositorioDocumentos
from app.servicos.chunker import dividir_em_trechos
from app.servicos.embeddings import ServicoEmbeddings
from app.servicos.parser_documentos import ParserDocumentos


class ServicoRAG:
    def __init__(
        self,
        config: Configuracao,
        repositorio: RepositorioDocumentos,
        parser: ParserDocumentos,
        servico_embeddings: ServicoEmbeddings,
    ):
        self._config = config
        self._repositorio = repositorio
        self._parser = parser
        self._servico_embeddings = servico_embeddings

    def ingerir_documento(self, nome_arquivo: str, conteudo_bytes: bytes):
        texto = self._parser.extrair_texto(nome_arquivo, conteudo_bytes)
        trechos = dividir_em_trechos(texto, self._config.tamanho_trecho, self._config.sobreposicao_trecho)
        if not trechos:
            raise ValueError("Documento sem conteúdo textual útil para indexação")

        embeddings = self._servico_embeddings.gerar(trechos)
        return self._repositorio.salvar_documento_com_trechos(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=nome_arquivo.split(".")[-1].lower(),
            trechos=trechos,
            embeddings=embeddings,
        )

    def responder_pergunta(self, pergunta: str, limite: int) -> RespostaPergunta:
        embedding_pergunta = self._servico_embeddings.gerar([pergunta])[0]
        resultados = self._repositorio.buscar_trechos_similares(embedding_pergunta, limite)

        fontes = [
            FonteResposta(
                trecho_id=item.trecho_id,
                documento_id=item.documento_id,
                nome_arquivo=item.nome_arquivo,
                conteudo=item.conteudo,
                pontuacao=round(item.pontuacao, 4),
            )
            for item in resultados
        ]

        resposta = "\n\n".join(f"[{idx}] {fonte.conteudo}" for idx, fonte in enumerate(fontes, start=1))
        if not resposta:
            resposta = "Não encontrei contexto suficiente nos documentos indexados."

        return RespostaPergunta(pergunta=pergunta, resposta=resposta, fontes=fontes)
