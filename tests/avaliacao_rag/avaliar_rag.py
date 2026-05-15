from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.consulta_rag import (
    GeradorRespostaContextual,
    MensagemModelo,
    ServicoConsultaRAG,
    ServicoRecuperacaoHibrida,
    TrechoRecuperado,
)

DIRETORIO_BASE = Path(__file__).parent
CAMINHO_CASOS = DIRETORIO_BASE / "casos_avaliacao.json"
DIRETORIO_DOCUMENTOS = DIRETORIO_BASE / "documentos_referencia"
LIMITE_FONTES_PADRAO = 3
QUANTIDADE_EXECUCOES_ESTABILIDADE = 3

PALAVRAS_IGNORADAS = {
    "a",
    "as",
    "ao",
    "aos",
    "cada",
    "com",
    "como",
    "da",
    "das",
    "de",
    "deve",
    "do",
    "dos",
    "durante",
    "e",
    "em",
    "é",
    "o",
    "os",
    "para",
    "por",
    "quando",
    "que",
    "quais",
    "qual",
    "se",
    "são",
    "ter",
    "um",
    "uma",
}


@dataclass(frozen=True)
class DocumentoReferencia:
    documento_id: int
    nome_arquivo: str
    conteudo: str


@dataclass(frozen=True)
class CasoAvaliacao:
    id: str
    pergunta: str
    resposta_esperada_resumida: str
    trechos_esperados: list[str]
    termos_obrigatorios: list[str]
    similaridade_minima: float
    fonte_esperada: str | None
    fontes_uteis_minimas: int
    deve_responder: bool


class ServicoEmbeddingsDeterministico:
    def gerar_embeddings(self, textos: list[str]) -> list[Counter[str]]:
        return [_vetorizar(texto) for texto in textos]


class RepositorioAvaliacaoRAG:
    def __init__(self, documentos: list[DocumentoReferencia], similaridade_minima: float):
        self._trechos = _montar_trechos(documentos)
        self._similaridade_minima = similaridade_minima

    def buscar_trechos_similares(
        self, embedding_pergunta: Counter[str], limite: int, projeto_id: int
    ) -> list[TrechoRecuperado]:
        resultados = []
        termos_pergunta = set(embedding_pergunta)
        for trecho in self._trechos:
            vetor_trecho = _vetorizar(trecho.conteudo)
            sobreposicao = termos_pergunta & set(vetor_trecho)
            similaridade = _similaridade_cosseno(embedding_pergunta, vetor_trecho)
            if len(sobreposicao) >= 2 and similaridade >= self._similaridade_minima:
                resultados.append(
                    _copiar_trecho_com_pontuacao(
                        trecho=trecho, pontuacao_similaridade=similaridade
                    )
                )
        return sorted(
            resultados, key=lambda item: item.pontuacao_similaridade, reverse=True
        )[:limite]

    def buscar_trechos_por_texto(
        self, texto_busca: str, limite: int, projeto_id: int
    ) -> list[TrechoRecuperado]:
        termos_pergunta = set(_vetorizar(texto_busca))
        resultados = []
        for trecho in self._trechos:
            termos_trecho = set(_vetorizar(trecho.conteudo))
            quantidade_termos = len(termos_pergunta & termos_trecho)
            if quantidade_termos >= 2:
                pontuacao = quantidade_termos / max(len(termos_pergunta), 1)
                resultados.append(
                    _copiar_trecho_com_pontuacao(
                        trecho=trecho, pontuacao_similaridade=pontuacao
                    )
                )
        return sorted(
            resultados, key=lambda item: item.pontuacao_similaridade, reverse=True
        )[:limite]


class ProvedorRespostaDeterministico:
    def gerar_texto(self, mensagens: list[MensagemModelo]) -> str:
        mensagem_usuario = mensagens[-1].conteudo if mensagens else ""
        contexto = mensagem_usuario.split("Contexto recuperado:", maxsplit=1)[-1]
        contexto = contexto.split("Instruções:", maxsplit=1)[0]
        contexto = re.sub(r"\[Fonte [^\]]+\]", "", contexto)
        sentencas = [
            sentenca.strip()
            for sentenca in re.split(r"(?<=[.!?])\s+", contexto.replace("\n", " "))
            if sentenca.strip() and not sentenca.strip().startswith("[Fonte")
        ]
        evidencias = sentencas[:2]
        if not evidencias:
            return "Não encontrei contexto suficiente para responder com segurança."
        return " ".join(evidencias)


def executar_avaliacao() -> dict[str, Any]:
    documentos = carregar_documentos_referencia()
    casos = carregar_casos_avaliacao()
    resultados = [_avaliar_caso(caso=caso, documentos=documentos) for caso in casos]
    return {
        "total_casos": len(resultados),
        "total_aprovados": sum(1 for resultado in resultados if resultado["aprovado"]),
        "aprovado": all(resultado["aprovado"] for resultado in resultados),
        "resultados": resultados,
    }


def carregar_documentos_referencia() -> list[DocumentoReferencia]:
    documentos = []
    for indice, caminho in enumerate(sorted(DIRETORIO_DOCUMENTOS.glob("*.md")), start=1):
        documentos.append(
            DocumentoReferencia(
                documento_id=indice,
                nome_arquivo=caminho.name,
                conteudo=caminho.read_text(encoding="utf-8"),
            )
        )
    return documentos


def carregar_casos_avaliacao() -> list[CasoAvaliacao]:
    dados = json.loads(CAMINHO_CASOS.read_text(encoding="utf-8"))
    return [CasoAvaliacao(**item) for item in dados]


def _avaliar_caso(caso: CasoAvaliacao, documentos: list[DocumentoReferencia]) -> dict[str, Any]:
    respostas = [_executar_fluxo(caso=caso, documentos=documentos) for _ in range(QUANTIDADE_EXECUCOES_ESTABILIDADE)]
    resposta_referencia = respostas[0]
    resposta_texto = resposta_referencia.resposta
    fontes = resposta_referencia.fontes

    fonte_correta_presente = (
        caso.fonte_esperada is None
        or any(fonte.nome_arquivo == caso.fonte_esperada for fonte in fontes)
    )
    quantidade_fontes_uteis = _contar_fontes_uteis(
        fontes=fontes, trechos_esperados=caso.trechos_esperados
    )
    similaridade_suficiente = (
        not fontes
        if not caso.deve_responder
        else bool(fontes)
        and max(fonte.pontuacao_similaridade for fonte in fontes) >= caso.similaridade_minima
    )
    termos_obrigatorios_presentes = (not caso.deve_responder) or all(
        termo.lower() in resposta_texto.lower() for termo in caso.termos_obrigatorios
    )
    ausencia_resposta_sem_contexto = caso.deve_responder or (
        not fontes
        and "nao encontrei contexto suficiente" in resposta_texto.lower()
    )
    resposta_estavel = all(
        resposta.resposta == resposta_texto
        and [fonte.trecho_id for fonte in resposta.fontes]
        == [fonte.trecho_id for fonte in fontes]
        for resposta in respostas[1:]
    )

    metricas = {
        "fonte_correta_presente": fonte_correta_presente,
        "quantidade_fontes_uteis": quantidade_fontes_uteis,
        "fontes_uteis_suficientes": quantidade_fontes_uteis >= caso.fontes_uteis_minimas,
        "ausencia_resposta_sem_contexto": ausencia_resposta_sem_contexto,
        "resposta_estavel": resposta_estavel,
        "similaridade_suficiente": similaridade_suficiente,
        "termos_obrigatorios_presentes": termos_obrigatorios_presentes,
    }
    metricas_booleanas = [valor for valor in metricas.values() if isinstance(valor, bool)]
    return {
        "id": caso.id,
        "aprovado": all(metricas_booleanas),
        "metricas": metricas,
        "fontes_retornadas": [fonte.nome_arquivo for fonte in fontes],
        "resposta": resposta_texto,
    }


def _executar_fluxo(caso: CasoAvaliacao, documentos: list[DocumentoReferencia]):
    repositorio = RepositorioAvaliacaoRAG(
        documentos=documentos,
        similaridade_minima=caso.similaridade_minima,
    )
    recuperacao = ServicoRecuperacaoHibrida(
        repositorio=repositorio,
        servico_embeddings=ServicoEmbeddingsDeterministico(),
        peso_busca_vetorial=0.7,
        peso_busca_lexical=0.3,
    )
    servico = ServicoConsultaRAG(
        servico_recuperacao=recuperacao,
        gerador_resposta=GeradorRespostaContextual(
            provedor_modelo_linguagem=ProvedorRespostaDeterministico()
        ),
    )
    return servico.responder_pergunta(
        projeto_id=1,
        pergunta=caso.pergunta,
        limite_fontes=LIMITE_FONTES_PADRAO,
    )


def _montar_trechos(documentos: list[DocumentoReferencia]) -> list[TrechoRecuperado]:
    trechos = []
    trecho_id = 1
    for documento in documentos:
        paragrafos = [
            paragrafo.strip()
            for paragrafo in documento.conteudo.split("\n\n")
            if paragrafo.strip() and not paragrafo.startswith("#")
        ]
        for pagina, paragrafo in enumerate(paragrafos, start=1):
            trechos.append(
                TrechoRecuperado(
                    trecho_id=trecho_id,
                    documento_id=documento.documento_id,
                    nome_arquivo=documento.nome_arquivo,
                    conteudo=paragrafo,
                    pontuacao_similaridade=0.0,
                    pagina=pagina,
                    secao=documento.nome_arquivo.replace("_", " ").replace(".md", ""),
                )
            )
            trecho_id += 1
    return trechos


def _copiar_trecho_com_pontuacao(
    trecho: TrechoRecuperado, pontuacao_similaridade: float
) -> TrechoRecuperado:
    return TrechoRecuperado(
        trecho_id=trecho.trecho_id,
        documento_id=trecho.documento_id,
        nome_arquivo=trecho.nome_arquivo,
        conteudo=trecho.conteudo,
        pontuacao_similaridade=pontuacao_similaridade,
        pagina=trecho.pagina,
        secao=trecho.secao,
        titulo_contexto=trecho.titulo_contexto,
        caminho_hierarquico=trecho.caminho_hierarquico,
    )


def _contar_fontes_uteis(fontes, trechos_esperados: list[str]) -> int:
    if not trechos_esperados:
        return 0
    return sum(
        1
        for fonte in fontes
        if any(trecho.lower() in fonte.conteudo.lower() for trecho in trechos_esperados)
    )


def _vetorizar(texto: str) -> Counter[str]:
    termos = re.findall(r"\w+", texto.lower(), flags=re.UNICODE)
    return Counter(termo for termo in termos if termo not in PALAVRAS_IGNORADAS and len(termo) > 2)


def _similaridade_cosseno(vetor_a: Counter[str], vetor_b: Counter[str]) -> float:
    termos = set(vetor_a) | set(vetor_b)
    if not termos:
        return 0.0
    produto = sum(vetor_a[termo] * vetor_b[termo] for termo in termos)
    norma_a = math.sqrt(sum(valor * valor for valor in vetor_a.values()))
    norma_b = math.sqrt(sum(valor * valor for valor in vetor_b.values()))
    if not norma_a or not norma_b:
        return 0.0
    return produto / (norma_a * norma_b)


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa a avaliação local de qualidade RAG.")
    parser.add_argument("--json", action="store_true", help="Exibe o resultado completo em JSON.")
    argumentos = parser.parse_args()
    resumo = executar_avaliacao()
    if argumentos.json:
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
    else:
        estado = "APROVADO" if resumo["aprovado"] else "REPROVADO"
        print(f"Avaliação RAG: {estado} ({resumo['total_aprovados']}/{resumo['total_casos']})")
        for resultado in resumo["resultados"]:
            marcador = "OK" if resultado["aprovado"] else "FALHA"
            print(f"- {marcador}: {resultado['id']}")
    return 0 if resumo["aprovado"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
