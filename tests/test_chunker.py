from app.servicos.chunker import dividir_em_trechos


def test_dividir_em_trechos_deve_respeitar_tamanho_e_sobreposicao():
    texto = "a" * 100

    trechos = dividir_em_trechos(texto, tamanho_trecho=30, sobreposicao=10)

    assert len(trechos) >= 4
    assert all(len(trecho) <= 30 for trecho in trechos)
