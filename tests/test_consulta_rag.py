from app.services.consulta_rag import (
    GeradorRespostaContextual,
    ServicoConsultaRAG,
    ServicoRecuperacaoSemantica,
    TrechoRecuperado,
)


class _RepositorioBuscaFalso:
    def __init__(self, resultados):
        self.resultados = resultados
        self.ultima_busca = None

    def buscar_trechos_similares(self, embedding_pergunta, limite):
        self.ultima_busca = {"embedding_pergunta": embedding_pergunta, "limite": limite}
        return self.resultados[:limite]


class _ServicoEmbeddingsFalso:
    def gerar_embeddings(self, textos):
        return [[0.1, 0.2, 0.3] for _ in textos]


def test_recuperacao_semantica_deve_gerar_embedding_e_consultar_repositorio():
    repositorio = _RepositorioBuscaFalso(resultados=[])
    servico = ServicoRecuperacaoSemantica(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
    )

    servico.recuperar_trechos(pergunta="o que é rag?", limite_fontes=2)

    assert repositorio.ultima_busca == {"embedding_pergunta": [0.1, 0.2, 0.3], "limite": 2}


def test_consulta_rag_deve_retornar_resposta_com_fontes():
    resultados = [
        TrechoRecuperado(
            trecho_id=1,
            documento_id=10,
            nome_arquivo="manual.md",
            conteudo="RAG combina recuperação e geração.",
            pontuacao_similaridade=0.91,
        ),
        TrechoRecuperado(
            trecho_id=2,
            documento_id=10,
            nome_arquivo="manual.md",
            conteudo="A busca vetorial encontra os trechos mais úteis.",
            pontuacao_similaridade=0.87,
        ),
    ]
    recuperacao = ServicoRecuperacaoSemantica(
        repositorio=_RepositorioBuscaFalso(resultados=resultados),
        servico_embeddings=_ServicoEmbeddingsFalso(),
    )
    servico = ServicoConsultaRAG(
        servico_recuperacao=recuperacao,
        gerador_resposta=GeradorRespostaContextual(),
    )

    resposta = servico.responder_pergunta(pergunta="Explique RAG", limite_fontes=2)

    assert "não garante precisão absoluta" in resposta.resposta
    assert len(resposta.fontes) == 2
    assert resposta.fontes[0].nome_arquivo == "manual.md"
    assert resposta.fontes[0].pontuacao_similaridade == 0.91


def test_gerador_deve_sinalizar_falta_de_contexto():
    gerador = GeradorRespostaContextual()

    resposta = gerador.gerar_resposta(pergunta="qualquer", contexto="", total_fontes=0)

    assert "Não encontrei contexto suficiente" in resposta
