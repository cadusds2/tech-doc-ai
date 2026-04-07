import pytest

from app.services.chunking import EstrategiaChunkingTamanhoComSobreposicao, ServicoChunkingDocumentos


def test_estrategia_deve_gerar_trechos_com_sobreposicao():
    estrategia = EstrategiaChunkingTamanhoComSobreposicao(tamanho_trecho=10, sobreposicao=2)

    trechos = estrategia.gerar_trechos("abcdefghij1234567890")

    assert len(trechos) == 3
    assert trechos[0].conteudo == "abcdefghij"
    assert trechos[1].conteudo == "ij12345678"
    assert trechos[2].conteudo == "7890"

    assert trechos[0].indice_inicio == 0
    assert trechos[1].indice_inicio == 8
    assert trechos[2].indice_inicio == 16


def test_servico_deve_normalizar_espacos_na_geracao_de_trechos():
    estrategia = EstrategiaChunkingTamanhoComSobreposicao(tamanho_trecho=12, sobreposicao=3)
    servico = ServicoChunkingDocumentos(estrategia=estrategia)

    trechos = servico.chunkar_texto("linha   1\n\nlinha\t2")

    assert len(trechos) == 2
    assert trechos[0].conteudo == "linha 1 linh"
    assert trechos[1].conteudo == "inha 2"


def test_estrategia_deve_retornar_vazio_para_texto_sem_conteudo():
    estrategia = EstrategiaChunkingTamanhoComSobreposicao(tamanho_trecho=10, sobreposicao=2)

    trechos = estrategia.gerar_trechos("   \n\t ")

    assert trechos == []


@pytest.mark.parametrize(
    ("tamanho_trecho", "sobreposicao"),
    [
        (0, 0),
        (10, -1),
        (10, 10),
        (10, 11),
    ],
)
def test_estrategia_deve_validar_parametros_invalidos(tamanho_trecho: int, sobreposicao: int):
    with pytest.raises(ValueError):
        EstrategiaChunkingTamanhoComSobreposicao(tamanho_trecho=tamanho_trecho, sobreposicao=sobreposicao)
