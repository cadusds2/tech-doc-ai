import logging
from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

from app.api.schemas.chat import FonteUtilizada, RespostaPergunta
from app.services.embeddings import ServicoEmbeddings
from app.services.reranqueamento import ReranqueadorTrechos

logger = logging.getLogger(__name__)

LIMITE_MENSAGENS_CONVERSA_PADRAO = 6
QUANTIDADE_PERGUNTAS_HISTORICO_RECUPERACAO_PADRAO = 3


@dataclass(frozen=True)
class TrechoRecuperado:
    trecho_id: int
    documento_id: int
    nome_arquivo: str
    conteudo: str
    pontuacao_similaridade: float
    pagina: int | None = None
    secao: str | None = None
    titulo_contexto: str | None = None
    caminho_hierarquico: str | None = None


@dataclass(frozen=True)
class MensagemModelo:
    papel: str
    conteudo: str


class ProvedorModeloLinguagem(Protocol):
    def gerar_texto(self, mensagens: list[MensagemModelo]) -> str: ...


class MemoriaConversa(Protocol):
    def listar_mensagens(self, conversation_id: str) -> list[MensagemModelo]: ...

    def registrar_interacao(
        self, conversation_id: str, pergunta: str, resposta: str
    ) -> None: ...


class MemoriaConversasEmMemoria:
    def __init__(self, limite_mensagens: int = LIMITE_MENSAGENS_CONVERSA_PADRAO):
        self._limite_mensagens = max(0, limite_mensagens)
        self._conversas: dict[str, deque[MensagemModelo]] = {}
        self._trava = Lock()

    def listar_mensagens(self, conversation_id: str) -> list[MensagemModelo]:
        with self._trava:
            mensagens = self._conversas.get(conversation_id)
            if mensagens is None:
                return []
            return list(mensagens)

    def registrar_interacao(
        self, conversation_id: str, pergunta: str, resposta: str
    ) -> None:
        with self._trava:
            fila = self._conversas.setdefault(
                conversation_id,
                deque(maxlen=self._limite_mensagens or None),
            )
            if self._limite_mensagens == 0:
                return
            fila.append(MensagemModelo(papel="usuario", conteudo=pergunta))
            fila.append(MensagemModelo(papel="assistente", conteudo=resposta))


class ProvedorModeloLinguagemHeuristico:
    def gerar_texto(self, mensagens: list[MensagemModelo]) -> str:
        if not mensagens:
            return "Nao foi possivel gerar uma resposta no momento."

        mensagem_usuario = mensagens[-1].conteudo
        inicio_contexto = mensagem_usuario.find("Contexto recuperado:")
        contexto = (
            mensagem_usuario[inicio_contexto:]
            if inicio_contexto >= 0
            else mensagem_usuario
        )

        return (
            "Com base nos trechos recuperados, segue uma resposta preliminar: "
            "os documentos indicam que a pergunta pode ser respondida pelo contexto abaixo. "
            "Use as fontes para validacao adicional quando necessario.\n\n"
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

    def recuperar_trechos(
        self, pergunta: str, limite_fontes: int
    ) -> list[TrechoRecuperado]:
        if limite_fontes <= 0:
            return []

        resultados_por_trecho_id: dict[int, dict[str, Any]] = {}

        for trecho in self._buscar_trechos_vetoriais(
            pergunta=pergunta, limite_fontes=limite_fontes
        ):
            self._registrar_resultado(
                resultados_por_trecho_id=resultados_por_trecho_id,
                trecho=trecho,
                pontuacao_vetorial=trecho.pontuacao_similaridade,
            )

        for trecho in self._repositorio.buscar_trechos_por_texto(
            texto_busca=pergunta, limite=limite_fontes
        ):
            self._registrar_resultado(
                resultados_por_trecho_id=resultados_por_trecho_id,
                trecho=trecho,
                pontuacao_lexical=trecho.pontuacao_similaridade,
            )

        trechos_combinados = [
            self._montar_trecho_combinado(dados_trecho)
            for dados_trecho in resultados_por_trecho_id.values()
        ]
        trechos_combinados.sort(
            key=lambda trecho: trecho.pontuacao_similaridade, reverse=True
        )
        return trechos_combinados[:limite_fontes]

    def _buscar_trechos_vetoriais(
        self, pergunta: str, limite_fontes: int
    ) -> list[TrechoRecuperado]:
        inicio_busca = perf_counter()
        embeddings = self._servico_embeddings.gerar_embeddings([pergunta])
        if not embeddings:
            logger.info(
                "Busca vetorial concluida sem embedding para pergunta.",
                extra={
                    "tempo_busca_vetorial_ms": round(
                        (perf_counter() - inicio_busca) * 1000, 2
                    ),
                    "quantidade_resultados_vetoriais": 0,
                },
            )
            return []
        resultados = self._repositorio.buscar_trechos_similares(
            embedding_pergunta=embeddings[0], limite=limite_fontes
        )
        logger.info(
            "Busca vetorial concluida.",
            extra={
                "tempo_busca_vetorial_ms": round(
                    (perf_counter() - inicio_busca) * 1000, 2
                ),
                "quantidade_resultados_vetoriais": len(resultados),
                "limite_fontes": limite_fontes,
            },
        )
        return resultados

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
        dados_trecho["pontuacao_vetorial"] = max(
            float(dados_trecho["pontuacao_vetorial"]), pontuacao_vetorial
        )
        dados_trecho["pontuacao_lexical"] = max(
            float(dados_trecho["pontuacao_lexical"]), pontuacao_lexical
        )

    def _montar_trecho_combinado(
        self, dados_trecho: dict[str, Any]
    ) -> TrechoRecuperado:
        trecho = dados_trecho["trecho"]
        pontuacao_combinada = self._peso_busca_vetorial * float(
            dados_trecho["pontuacao_vetorial"]
        ) + self._peso_busca_lexical * float(dados_trecho["pontuacao_lexical"])
        return TrechoRecuperado(
            trecho_id=trecho.trecho_id,
            documento_id=trecho.documento_id,
            nome_arquivo=trecho.nome_arquivo,
            conteudo=trecho.conteudo,
            pontuacao_similaridade=pontuacao_combinada,
            pagina=trecho.pagina,
            secao=trecho.secao,
            titulo_contexto=trecho.titulo_contexto,
            caminho_hierarquico=trecho.caminho_hierarquico,
        )


class ServicoRecuperacaoSemantica:
    def __init__(self, repositorio, servico_embeddings: ServicoEmbeddings):
        self._repositorio = repositorio
        self._servico_embeddings = servico_embeddings

    def recuperar_trechos(
        self, pergunta: str, limite_fontes: int
    ) -> list[TrechoRecuperado]:
        embeddings = self._servico_embeddings.gerar_embeddings([pergunta])
        if not embeddings:
            return []
        return self._repositorio.buscar_trechos_similares(
            embedding_pergunta=embeddings[0], limite=limite_fontes
        )


class GeradorRespostaContextual:
    def __init__(
        self, provedor_modelo_linguagem: ProvedorModeloLinguagem | None = None
    ):
        self._provedor_modelo_linguagem = (
            provedor_modelo_linguagem or ProvedorModeloLinguagemHeuristico()
        )

    def gerar_resposta(
        self,
        pergunta: str,
        contexto: str,
        total_fontes: int,
        historico: list[MensagemModelo] | None = None,
    ) -> str:
        if not contexto.strip():
            return (
                "Nao encontrei contexto suficiente para responder com seguranca com base nos documentos indexados. "
                "Tente reformular a pergunta ou ingerir mais conteudo relevante."
            )

        mensagens = self._montar_prompt(
            pergunta=pergunta,
            contexto=contexto,
            historico=historico or [],
        )
        try:
            resposta_modelo = self._provedor_modelo_linguagem.gerar_texto(
                mensagens
            ).strip()
        except Exception as erro:
            logger.error(
                "Falha ao gerar resposta contextual. evento=falha_geracao_resposta_contextual",
                extra={
                    "total_fontes": total_fontes,
                    "tipo_erro": type(erro).__name__,
                },
            )
            resposta_modelo = (
                "Nao foi possivel gerar uma resposta com seguranca no momento. "
                "As fontes recuperadas continuam disponiveis para consulta."
            )

        if not resposta_modelo:
            resposta_modelo = (
                "Nao consegui gerar uma resposta textual com o contexto disponivel."
            )

        return (
            f"{resposta_modelo}\n\n"
            f"Aviso: resposta gerada a partir de {total_fontes} fonte(s) recuperada(s) por busca hibrida e sem garantia de precisao absoluta."
        )

    @staticmethod
    def _montar_prompt(
        pergunta: str,
        contexto: str,
        historico: list[MensagemModelo] | None = None,
    ) -> list[MensagemModelo]:
        mensagens = [
            MensagemModelo(
                papel="sistema",
                conteudo=(
                    "Voce responde sempre em portugues brasileiro. "
                    "Use exclusivamente o contexto recuperado para responder. "
                    "Se houver lacunas, deixe isso explicito e nao invente fatos, exemplos ou referencias."
                ),
            )
        ]
        mensagens.extend(historico or [])
        mensagens.append(
            MensagemModelo(
                papel="usuario",
                conteudo=(
                    "Pergunta do usuario:\n"
                    f"{pergunta}\n\n"
                    "Contexto recuperado:\n"
                    f"{contexto}\n\n"
                    "Instrucoes: responda em portugues brasileiro, de forma objetiva, "
                    "use exclusivamente o contexto recuperado e deixe claro quando o contexto nao for suficiente."
                ),
            )
        )
        return mensagens


class ServicoConsultaRAG:
    def __init__(
        self,
        servico_recuperacao: ServicoRecuperacaoHibrida,
        gerador_resposta: GeradorRespostaContextual,
        reranqueador_trechos: ReranqueadorTrechos | None = None,
        memoria_conversa: MemoriaConversa | None = None,
        quantidade_perguntas_historico_recuperacao: int = QUANTIDADE_PERGUNTAS_HISTORICO_RECUPERACAO_PADRAO,
    ):
        self._servico_recuperacao = servico_recuperacao
        self._gerador_resposta = gerador_resposta
        self._reranqueador_trechos = reranqueador_trechos
        self._memoria_conversa = memoria_conversa
        self._quantidade_perguntas_historico_recuperacao = max(
            0, quantidade_perguntas_historico_recuperacao
        )

    def responder_pergunta(
        self,
        pergunta: str,
        limite_fontes: int,
        conversation_id: str | None = None,
    ) -> RespostaPergunta:
        conversation_id_resolvido = self._resolver_conversation_id(conversation_id)
        historico = self._obter_historico_conversa(conversation_id_resolvido)
        pergunta_para_recuperacao = self._montar_pergunta_para_recuperacao(
            pergunta=pergunta,
            historico=historico,
        )
        trechos_recuperados = self._servico_recuperacao.recuperar_trechos(
            pergunta=pergunta_para_recuperacao,
            limite_fontes=limite_fontes,
        )

        if self._reranqueador_trechos is not None:
            trechos_recuperados = self._reranqueador_trechos.reranquear(
                pergunta=pergunta,
                trechos=trechos_recuperados,
            )

        contexto = self._montar_contexto(trechos_recuperados)
        resposta = self._gerador_resposta.gerar_resposta(
            pergunta=pergunta,
            contexto=contexto,
            total_fontes=len(trechos_recuperados),
            historico=historico,
        )
        self._registrar_interacao_conversa(
            conversation_id=conversation_id_resolvido,
            pergunta=pergunta,
            resposta=resposta,
        )

        fontes = [
            FonteUtilizada(
                trecho_id=trecho.trecho_id,
                documento_id=trecho.documento_id,
                nome_arquivo=trecho.nome_arquivo,
                conteudo=trecho.conteudo,
                pontuacao_similaridade=round(trecho.pontuacao_similaridade, 4),
                pagina=trecho.pagina,
                secao=trecho.secao,
                titulo_contexto=trecho.titulo_contexto,
                caminho_hierarquico=trecho.caminho_hierarquico,
            )
            for trecho in trechos_recuperados
        ]
        logger.info(
            "Fontes retornadas para resposta.",
            extra={
                "quantidade_fontes_retornadas": len(fontes),
                "limite_fontes": limite_fontes,
                "conversation_id": conversation_id_resolvido,
            },
        )
        return RespostaPergunta(
            resposta=resposta,
            fontes=fontes,
            conversation_id=conversation_id_resolvido,
        )

    def _obter_historico_conversa(
        self, conversation_id: str
    ) -> list[MensagemModelo]:
        if self._memoria_conversa is None:
            return []
        return self._memoria_conversa.listar_mensagens(conversation_id)

    def _registrar_interacao_conversa(
        self, conversation_id: str, pergunta: str, resposta: str
    ) -> None:
        if self._memoria_conversa is None:
            return
        self._memoria_conversa.registrar_interacao(
            conversation_id=conversation_id,
            pergunta=pergunta,
            resposta=resposta,
        )

    def _montar_pergunta_para_recuperacao(
        self, pergunta: str, historico: list[MensagemModelo]
    ) -> str:
        if self._quantidade_perguntas_historico_recuperacao == 0:
            return pergunta

        perguntas_anteriores = [
            mensagem.conteudo
            for mensagem in historico
            if mensagem.papel == "usuario"
        ][-self._quantidade_perguntas_historico_recuperacao :]

        if not perguntas_anteriores:
            return pergunta

        blocos = ["Historico recente da conversa:"]
        blocos.extend(
            f"- Pergunta anterior {indice}: {conteudo}"
            for indice, conteudo in enumerate(perguntas_anteriores, start=1)
        )
        blocos.append(f"Pergunta atual: {pergunta}")
        return "\n".join(blocos)

    @staticmethod
    def _resolver_conversation_id(conversation_id: str | None) -> str:
        if conversation_id and conversation_id.strip():
            return conversation_id.strip()
        return uuid4().hex

    @staticmethod
    def _montar_contexto(trechos_recuperados: list[TrechoRecuperado]) -> str:
        if not trechos_recuperados:
            return ""

        blocos_contexto: list[str] = []
        for indice, trecho in enumerate(trechos_recuperados, start=1):
            metadados = ServicoConsultaRAG._formatar_metadados_contexto(trecho)
            blocos_contexto.append(
                f"[Fonte {indice} | {trecho.nome_arquivo} | similaridade={trecho.pontuacao_similaridade:.4f}{metadados}]\n"
                f"{trecho.conteudo}"
            )

        return "\n\n".join(blocos_contexto)

    @staticmethod
    def _formatar_metadados_contexto(trecho: TrechoRecuperado) -> str:
        metadados: list[str] = []
        if trecho.pagina is not None:
            metadados.append(f"pagina={trecho.pagina}")
        if trecho.secao:
            metadados.append(f"secao={trecho.secao}")
        if trecho.titulo_contexto and trecho.titulo_contexto != trecho.secao:
            metadados.append(f"titulo={trecho.titulo_contexto}")
        if trecho.caminho_hierarquico:
            metadados.append(f"caminho={trecho.caminho_hierarquico}")
        return " | " + " | ".join(metadados) if metadados else ""
