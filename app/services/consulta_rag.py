import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.api.schemas.chat import FonteUtilizada, RespostaPergunta
from app.services.embeddings import ServicoEmbeddings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrechoRecuperado:
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao_similaridade: float


@dataclass(frozen=True)
class MensagemModelo:
    papel: str
    conteudo: str


class ProvedorModeloLinguagem(Protocol):
    def gerar_texto(self, mensagens: list[MensagemModelo]) -> str:
        ...


class ProvedorModeloLinguagemHeuristico:
    def gerar_texto(self, mensagens: list[MensagemModelo]) -> str:
        if not mensagens:
            return "Não foi possível gerar uma resposta no momento."

        mensagem_usuario = mensagens[-1].conteudo
        inicio_contexto = mensagem_usuario.find("Contexto recuperado:")
        contexto = mensagem_usuario[inicio_contexto:] if inicio_contexto >= 0 else mensagem_usuario

        return (
            "Com base nos trechos recuperados, segue uma resposta preliminar: "
            "os documentos indicam que a pergunta pode ser respondida pelo contexto abaixo. "
            "Use as fontes para validação adicional quando necessário.\n\n"
            f"{contexto}"
        )


class ServicoRecuperacaoHibrida:
    def __init__(
        self,
        repositorio,
        servico_embeddings: ServicoEmbeddings,
        peso_busca_vetorial: float = 0.7,
        peso_busca_lexical: float = 0.3,
    ):
        self._repositorio = repositorio
        self._servico_embeddings = servico_embeddings
        self._peso_busca_vetorial = peso_busca_vetorial
        self._peso_busca_lexical = peso_busca_lexical

    def recuperar_trechos(self, pergunta: str, limite_fontes: int) -> list[TrechoRecuperado]:
        if limite_fontes <= 0:
            return []

        resultados_por_trecho_id: dict[int, dict[str, Any]] = {}

        for trecho in self._buscar_trechos_vetoriais(pergunta=pergunta, limite_fontes=limite_fontes):
            self._registrar_resultado(
                resultados_por_trecho_id=resultados_por_trecho_id,
                trecho=trecho,
                pontuacao_vetorial=trecho.pontuacao_similaridade,
            )

        for trecho in self._repositorio.buscar_trechos_por_texto(texto_busca=pergunta, limite=limite_fontes):
            self._registrar_resultado(
                resultados_por_trecho_id=resultados_por_trecho_id,
                trecho=trecho,
                pontuacao_lexical=trecho.pontuacao_similaridade,
            )

        trechos_combinados = [
            self._montar_trecho_combinado(dados_trecho) for dados_trecho in resultados_por_trecho_id.values()
        ]
        trechos_combinados.sort(key=lambda trecho: trecho.pontuacao_similaridade, reverse=True)
        return trechos_combinados[:limite_fontes]

    def _buscar_trechos_vetoriais(self, pergunta: str, limite_fontes: int) -> list[TrechoRecuperado]:
        embeddings = self._servico_embeddings.gerar_embeddings([pergunta])
        if not embeddings:
            return []
        return self._repositorio.buscar_trechos_similares(embedding_pergunta=embeddings[0], limite=limite_fontes)

    @staticmethod
    def _registrar_resultado(
        resultados_por_trecho_id: dict[int, dict[str, Any]],
        trecho: TrechoRecuperado,
        pontuacao_vetorial: float = 0.0,
        pontuacao_lexical: float = 0.0,
    ) -> None:
        dados_trecho = resultados_por_trecho_id.setdefault(
            trecho.trecho_id,
            {
                "trecho": trecho,
                "pontuacao_vetorial": 0.0,
                "pontuacao_lexical": 0.0,
            },
        )
        dados_trecho["pontuacao_vetorial"] = max(float(dados_trecho["pontuacao_vetorial"]), pontuacao_vetorial)
        dados_trecho["pontuacao_lexical"] = max(float(dados_trecho["pontuacao_lexical"]), pontuacao_lexical)

    def _montar_trecho_combinado(self, dados_trecho: dict[str, Any]) -> TrechoRecuperado:
        trecho = dados_trecho["trecho"]
        pontuacao_combinada = (
            self._peso_busca_vetorial * float(dados_trecho["pontuacao_vetorial"])
            + self._peso_busca_lexical * float(dados_trecho["pontuacao_lexical"])
        )
        return TrechoRecuperado(
            trecho_id=trecho.trecho_id,
            documento_id=trecho.documento_id,
            nome_arquivo=trecho.nome_arquivo,
            conteudo=trecho.conteudo,
            pontuacao_similaridade=pontuacao_combinada,
        )


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
    def __init__(self, provedor_modelo_linguagem: ProvedorModeloLinguagem | None = None):
        self._provedor_modelo_linguagem = provedor_modelo_linguagem or ProvedorModeloLinguagemHeuristico()

    def gerar_resposta(self, pergunta: str, contexto: str, total_fontes: int) -> str:
        if not contexto.strip():
            return (
                "Não encontrei contexto suficiente para responder com segurança com base nos documentos indexados. "
                "Tente reformular a pergunta ou ingerir mais conteúdo relevante."
            )

        mensagens = self._montar_prompt(pergunta=pergunta, contexto=contexto)
        try:
            resposta_modelo = self._provedor_modelo_linguagem.gerar_texto(mensagens).strip()
        except Exception as erro:
            logger.exception(
                "falha_geracao_resposta_contextual",
                extra={
                    "total_fontes": total_fontes,
                    "tipo_erro": type(erro).__name__,
                },
            )
            resposta_modelo = (
                "Não foi possível gerar uma resposta com segurança no momento. "
                "As fontes recuperadas continuam disponíveis para consulta."
            )

        if not resposta_modelo:
            resposta_modelo = "Não consegui gerar uma resposta textual com o contexto disponível."

        return (
            f"{resposta_modelo}\n\n"
            f"Aviso: resposta gerada a partir de {total_fontes} fonte(s) recuperada(s) por busca híbrida e sem garantia de precisão absoluta."
        )

    @staticmethod
    def _montar_prompt(pergunta: str, contexto: str) -> list[MensagemModelo]:
        return [
            MensagemModelo(
                papel="sistema",
                conteudo=(
                    "Você responde sempre em português brasileiro. "
                    "Use exclusivamente o contexto recuperado para responder. "
                    "Se houver lacunas, deixe isso explícito e não invente fatos, exemplos ou referências."
                ),
            ),
            MensagemModelo(
                papel="usuario",
                conteudo=(
                    "Pergunta do usuário:\n"
                    f"{pergunta}\n\n"
                    "Contexto recuperado:\n"
                    f"{contexto}\n\n"
                    "Instruções: responda em português brasileiro, de forma objetiva, "
                    "use exclusivamente o contexto recuperado e deixe claro quando o contexto não for suficiente."
                ),
            ),
        ]


class ServicoConsultaRAG:
    def __init__(
        self,
        servico_recuperacao: ServicoRecuperacaoHibrida,
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
