from app.services.embeddings import ProvedorEmbeddingsDeterministico, ServicoEmbeddings


def test_servico_embeddings_deve_gerar_vetores_com_dimensao_configurada():
    servico = ServicoEmbeddings(provedor=ProvedorEmbeddingsDeterministico(dimensao=8))

    embeddings = servico.gerar_embeddings(["trecho 1", "trecho 2"])

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 8
    assert len(embeddings[1]) == 8


def test_servico_embeddings_deve_ignorar_textos_vazios():
    servico = ServicoEmbeddings(provedor=ProvedorEmbeddingsDeterministico(dimensao=8))

    embeddings = servico.gerar_embeddings(["", "   ", "conteudo"])

    assert len(embeddings) == 1
