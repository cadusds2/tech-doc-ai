from app.services.consulta_rag import (
    GeradorRespostaContextual,
    MensagemModelo,
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


class _ProvedorModeloFalso:
    def __init__(self):
        self.mensagens_recebidas: list[MensagemModelo] = []

    def gerar_texto(self, mensagens):
        self.mensagens_recebidas = mensagens
        return "Resposta sintética baseada no contexto recuperado."


class _ProvedorModeloComErroFalso:
    def gerar_texto(self, mensagens):
        raise RuntimeError("falha simulada")


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
    provedor_modelo = _ProvedorModeloFalso()
    servico = ServicoConsultaRAG(
        servico_recuperacao=recuperacao,
        gerador_resposta=GeradorRespostaContextual(provedor_modelo_linguagem=provedor_modelo),
    )

    resposta = servico.responder_pergunta(pergunta="Explique RAG", limite_fontes=2)

    assert "sem garantia de precisão absoluta" in resposta.resposta
    assert len(resposta.fontes) == 2
    assert resposta.fontes[0].nome_arquivo == "manual.md"
    assert resposta.fontes[0].pontuacao_similaridade == 0.91
    assert provedor_modelo.mensagens_recebidas[0].papel == "sistema"
    assert "português brasileiro" in provedor_modelo.mensagens_recebidas[0].conteudo
    assert "Use exclusivamente o contexto recuperado" in provedor_modelo.mensagens_recebidas[0].conteudo
    assert provedor_modelo.mensagens_recebidas[1].papel == "usuario"
    assert "Contexto recuperado" in provedor_modelo.mensagens_recebidas[1].conteudo
    assert "use exclusivamente o contexto recuperado" in provedor_modelo.mensagens_recebidas[1].conteudo


def test_gerador_deve_sinalizar_falta_de_contexto():
    gerador = GeradorRespostaContextual()

    resposta = gerador.gerar_resposta(pergunta="qualquer", contexto="", total_fontes=0)

    assert "Não encontrei contexto suficiente" in resposta


def test_gerador_deve_retornar_resposta_segura_quando_provedor_falhar(caplog):
    gerador = GeradorRespostaContextual(provedor_modelo_linguagem=_ProvedorModeloComErroFalso())

    resposta = gerador.gerar_resposta(
        pergunta="Explique RAG",
        contexto="[Fonte 1 | manual.md | similaridade=0.9000]\nRAG usa contexto recuperado.",
        total_fontes=1,
    )

    assert "Não foi possível gerar uma resposta com segurança" in resposta
    assert "falha simulada" not in resposta
    assert "falha_geracao_resposta_contextual" in caplog.text
