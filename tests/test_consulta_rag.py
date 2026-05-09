from app.services.consulta_rag import (
    GeradorRespostaContextual,
    MensagemModelo,
    ServicoConsultaRAG,
    ServicoRecuperacaoHibrida,
    ServicoRecuperacaoSemantica,
    TrechoRecuperado,
)


class _RepositorioBuscaFalso:
    def __init__(self, resultados, resultados_lexicais=None):
        self.resultados = resultados
        self.resultados_lexicais = resultados_lexicais or []
        self.ultima_busca = None
        self.ultima_busca_lexical = None

    def buscar_trechos_similares(self, embedding_pergunta, limite):
        self.ultima_busca = {"embedding_pergunta": embedding_pergunta, "limite": limite}
        return self.resultados[:limite]

    def buscar_trechos_por_texto(self, texto_busca, limite):
        self.ultima_busca_lexical = {"texto_busca": texto_busca, "limite": limite}
        return self.resultados_lexicais[:limite]


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


class _ReranqueadorInvertidoFalso:
    def reranquear(self, pergunta, trechos):
        return list(reversed(trechos))


def test_recuperacao_semantica_deve_gerar_embedding_e_consultar_repositorio():
    repositorio = _RepositorioBuscaFalso(resultados=[])
    servico = ServicoRecuperacaoSemantica(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
    )

    servico.recuperar_trechos(pergunta="o que é rag?", limite_fontes=2)

    assert repositorio.ultima_busca == {
        "embedding_pergunta": [0.1, 0.2, 0.3],
        "limite": 2,
    }


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
        gerador_resposta=GeradorRespostaContextual(
            provedor_modelo_linguagem=provedor_modelo
        ),
    )

    resposta = servico.responder_pergunta(pergunta="Explique RAG", limite_fontes=2)

    assert "sem garantia de precisão absoluta" in resposta.resposta
    assert len(resposta.fontes) == 2
    assert resposta.fontes[0].nome_arquivo == "manual.md"
    assert resposta.fontes[0].pontuacao_similaridade == 0.91
    assert provedor_modelo.mensagens_recebidas[0].papel == "sistema"
    assert "português brasileiro" in provedor_modelo.mensagens_recebidas[0].conteudo
    assert (
        "Use exclusivamente o contexto recuperado"
        in provedor_modelo.mensagens_recebidas[0].conteudo
    )
    assert provedor_modelo.mensagens_recebidas[1].papel == "usuario"
    assert "Contexto recuperado" in provedor_modelo.mensagens_recebidas[1].conteudo
    assert (
        "use exclusivamente o contexto recuperado"
        in provedor_modelo.mensagens_recebidas[1].conteudo
    )


def test_consulta_rag_deve_reranquear_trechos_antes_de_montar_contexto():
    resultados = [
        TrechoRecuperado(
            trecho_id=1,
            documento_id=10,
            nome_arquivo="manual.md",
            conteudo="Primeiro trecho recuperado.",
            pontuacao_similaridade=0.91,
        ),
        TrechoRecuperado(
            trecho_id=2,
            documento_id=10,
            nome_arquivo="manual.md",
            conteudo="Segundo trecho recuperado.",
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
        gerador_resposta=GeradorRespostaContextual(
            provedor_modelo_linguagem=provedor_modelo
        ),
        reranqueador_trechos=_ReranqueadorInvertidoFalso(),
    )

    resposta = servico.responder_pergunta(pergunta="Explique RAG", limite_fontes=2)

    assert [fonte.trecho_id for fonte in resposta.fontes] == [2, 1]
    contexto_enviado = provedor_modelo.mensagens_recebidas[1].conteudo
    assert contexto_enviado.index(
        "Segundo trecho recuperado."
    ) < contexto_enviado.index("Primeiro trecho recuperado.")


def test_gerador_deve_sinalizar_falta_de_contexto():
    gerador = GeradorRespostaContextual()

    resposta = gerador.gerar_resposta(pergunta="qualquer", contexto="", total_fontes=0)

    assert "Não encontrei contexto suficiente" in resposta


def test_gerador_deve_retornar_resposta_segura_quando_provedor_falhar(caplog):
    gerador = GeradorRespostaContextual(
        provedor_modelo_linguagem=_ProvedorModeloComErroFalso()
    )

    resposta = gerador.gerar_resposta(
        pergunta="Explique RAG",
        contexto="[Fonte 1 | manual.md | similaridade=0.9000]\nRAG usa contexto recuperado.",
        total_fontes=1,
    )

    assert "Não foi possível gerar uma resposta com segurança" in resposta
    assert "falha simulada" not in resposta
    assert "falha_geracao_resposta_contextual" in caplog.text


def test_recuperacao_hibrida_deve_recuperar_por_termo_exato_lexical():
    resultado_lexical = TrechoRecuperado(
        trecho_id=10,
        documento_id=1,
        nome_arquivo="glossario.md",
        conteudo="O termo pgvector aparece explicitamente no glossário.",
        pontuacao_similaridade=1.0,
    )
    repositorio = _RepositorioBuscaFalso(
        resultados=[], resultados_lexicais=[resultado_lexical]
    )
    servico = ServicoRecuperacaoHibrida(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
        peso_busca_vetorial=0.7,
        peso_busca_lexical=0.3,
    )

    trechos = servico.recuperar_trechos(pergunta="pgvector", limite_fontes=3)

    assert repositorio.ultima_busca_lexical == {"texto_busca": "pgvector", "limite": 3}
    assert [trecho.trecho_id for trecho in trechos] == [10]
    assert trechos[0].pontuacao_similaridade == 0.3


def test_recuperacao_hibrida_deve_manter_resultado_semantico_sem_termo_exato():
    resultado_vetorial = TrechoRecuperado(
        trecho_id=20,
        documento_id=2,
        nome_arquivo="conceitos.md",
        conteudo="Recuperação aumentada por geração combina contexto e síntese.",
        pontuacao_similaridade=0.9,
    )
    repositorio = _RepositorioBuscaFalso(
        resultados=[resultado_vetorial], resultados_lexicais=[]
    )
    servico = ServicoRecuperacaoHibrida(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
        peso_busca_vetorial=0.7,
        peso_busca_lexical=0.3,
    )

    trechos = servico.recuperar_trechos(
        pergunta="como responder com documentos", limite_fontes=2
    )

    assert repositorio.ultima_busca == {
        "embedding_pergunta": [0.1, 0.2, 0.3],
        "limite": 2,
    }
    assert [trecho.trecho_id for trecho in trechos] == [20]
    assert round(trechos[0].pontuacao_similaridade, 2) == 0.63


def test_recuperacao_hibrida_deve_combinar_resultados_e_remover_duplicidades():
    trecho_compartilhado_vetorial = TrechoRecuperado(
        trecho_id=30,
        documento_id=3,
        nome_arquivo="manual.md",
        conteudo="RAG usa recuperação híbrida para montar contexto.",
        pontuacao_similaridade=0.8,
    )
    trecho_apenas_vetorial = TrechoRecuperado(
        trecho_id=31,
        documento_id=3,
        nome_arquivo="manual.md",
        conteudo="Busca semântica aproxima significados relacionados.",
        pontuacao_similaridade=0.7,
    )
    trecho_compartilhado_lexical = TrechoRecuperado(
        trecho_id=30,
        documento_id=3,
        nome_arquivo="manual.md",
        conteudo="RAG usa recuperação híbrida para montar contexto.",
        pontuacao_similaridade=1.0,
    )
    trecho_apenas_lexical = TrechoRecuperado(
        trecho_id=32,
        documento_id=4,
        nome_arquivo="faq.md",
        conteudo="A expressão recuperação híbrida está documentada no FAQ.",
        pontuacao_similaridade=0.9,
    )
    repositorio = _RepositorioBuscaFalso(
        resultados=[trecho_compartilhado_vetorial, trecho_apenas_vetorial],
        resultados_lexicais=[trecho_compartilhado_lexical, trecho_apenas_lexical],
    )
    servico = ServicoRecuperacaoHibrida(
        repositorio=repositorio,
        servico_embeddings=_ServicoEmbeddingsFalso(),
        peso_busca_vetorial=0.7,
        peso_busca_lexical=0.3,
    )

    trechos = servico.recuperar_trechos(pergunta="recuperação híbrida", limite_fontes=3)

    assert [trecho.trecho_id for trecho in trechos] == [30, 31, 32]
    assert round(trechos[0].pontuacao_similaridade, 2) == 0.86
    assert round(trechos[1].pontuacao_similaridade, 2) == 0.49
    assert round(trechos[2].pontuacao_similaridade, 2) == 0.27


def test_consulta_rag_deve_incluir_metadados_nas_fontes_e_no_contexto():
    resultados = [
        TrechoRecuperado(
            trecho_id=7,
            documento_id=4,
            nome_arquivo="manual.pdf",
            conteudo="Detalhes de instalação do agente.",
            pontuacao_similaridade=0.93219,
            pagina=5,
            secao="Instalação",
            titulo_contexto="Instalação",
            caminho_hierarquico="Guia > Instalação",
        )
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

    resposta = servico.responder_pergunta(pergunta="Como instalar?", limite_fontes=1)

    fonte = resposta.fontes[0]
    assert fonte.pagina == 5
    assert fonte.secao == "Instalação"
    assert fonte.titulo_contexto == "Instalação"
    assert fonte.caminho_hierarquico == "Guia > Instalação"
    contexto_enviado = provedor_modelo.mensagens_recebidas[1].conteudo
    assert "página=5" in contexto_enviado
    assert "seção=Instalação" in contexto_enviado
    assert "caminho=Guia > Instalação" in contexto_enviado


def test_consulta_rag_deve_omitir_metadados_ausentes_no_contexto():
    trecho = TrechoRecuperado(
        trecho_id=8,
        documento_id=5,
        nome_arquivo="notas.txt",
        conteudo="Conteúdo sem metadados.",
        pontuacao_similaridade=0.5,
    )

    contexto = ServicoConsultaRAG._montar_contexto([trecho])

    assert contexto.startswith("[Fonte 1 | notas.txt | similaridade=0.5000]")
    assert "página=" not in contexto
    assert "seção=" not in contexto
