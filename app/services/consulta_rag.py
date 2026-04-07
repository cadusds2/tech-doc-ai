from dataclasses import dataclass

from app.api.schemas.chat import FonteUtilizada, RespostaPergunta
from app.services.embeddings import ServicoEmbeddings


@dataclass(frozen=True)
class TrechoRecuperado:
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao_similaridade: float


class ServicoRecuperacaoSemantica:
    def __init__(self, repositorio, servico_embeddings: ServicoEmbeddings):
        self._repositorio = repositorio
        self._servico_embeddings = servico_embeddings

    def recuperar_trechos(self, pergunta: str, limite_fontes: int) -> list[TrechoRecuperado]:
        embeddings = self._servico_embeddings.gerar_embeddings([pergunta])
        if not embeddings:
            return []
        return self._repositorio.buscar_trechos_similares(embedding_pergunta=embeddings[0], limite=limite_fontes)


class GeradorRespostaContextual:
    def gerar_resposta(self, pergunta: str, contexto: str, total_fontes: int) -> str:
        if not contexto.strip():
            return (
                "Não encontrei contexto suficiente para responder com segurança com base nos documentos indexados. "
                "Tente reformular a pergunta ou ingerir mais conteúdo relevante."
            )

        return (
            "Resposta baseada nos trechos recuperados (pode haver lacunas):\n"
            f"Pergunta: {pergunta}\n\n"
            f"Contexto analisado:\n{contexto}\n\n"
            f"Síntese: a resposta acima considera {total_fontes} fonte(s) recuperada(s) semanticamente e não garante precisão absoluta."
        )


class ServicoConsultaRAG:
    def __init__(
        self,
        servico_recuperacao: ServicoRecuperacaoSemantica,
        gerador_resposta: GeradorRespostaContextual,
    ):
        self._servico_recuperacao = servico_recuperacao
        self._gerador_resposta = gerador_resposta

    def responder_pergunta(self, pergunta: str, limite_fontes: int) -> RespostaPergunta:
        trechos_recuperados = self._servico_recuperacao.recuperar_trechos(
            pergunta=pergunta,
            limite_fontes=limite_fontes,
        )

        contexto = self._montar_contexto(trechos_recuperados)
        resposta = self._gerador_resposta.gerar_resposta(
            pergunta=pergunta,
            contexto=contexto,
            total_fontes=len(trechos_recuperados),
        )

        fontes = [
            FonteUtilizada(
                trecho_id=trecho.trecho_id,
                documento_id=trecho.documento_id,
                nome_arquivo=trecho.nome_arquivo,
                conteudo=trecho.conteudo,
                pontuacao_similaridade=round(trecho.pontuacao_similaridade, 4),
            )
            for trecho in trechos_recuperados
        ]
        return RespostaPergunta(resposta=resposta, fontes=fontes)

    @staticmethod
    def _montar_contexto(trechos_recuperados: list[TrechoRecuperado]) -> str:
        if not trechos_recuperados:
            return ""

        blocos_contexto: list[str] = []
        for indice, trecho in enumerate(trechos_recuperados, start=1):
            blocos_contexto.append(
                f"[Fonte {indice} | {trecho.nome_arquivo} | similaridade={trecho.pontuacao_similaridade:.4f}]\n"
                f"{trecho.conteudo}"
            )

        return "\n\n".join(blocos_contexto)
