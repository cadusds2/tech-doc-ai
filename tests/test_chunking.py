import pytest

from app.services.chunking import (
    ContadorTokensAproximadoPorPalavras,
    EstrategiaChunkingEstrutural,
    EstrategiaChunkingPorMedidaComSobreposicao,
    EstrategiaChunkingTamanhoComSobreposicao,
    ServicoChunkingDocumentos,
    TrechoGerado,
    UnidadeMedidaTrecho,
)


class MedidorComUnidadeSobredimensionada:
    def medir(self, texto: str) -> int:
        return sum(unidade.tamanho for unidade in self.gerar_unidades(texto))

    def gerar_unidades(self, texto: str) -> list[UnidadeMedidaTrecho]:
        unidades = []
        inicio = 0
        for parte, tamanho in [("enorme", 100), ("medio", 10), ("pequeno", 1)]:
            indice_inicio = texto.index(parte, inicio)
            indice_fim = indice_inicio + len(parte)
            unidades.append(
                UnidadeMedidaTrecho(
                    indice_inicio=indice_inicio,
                    indice_fim=indice_fim,
                    tamanho=tamanho,
                )
            )
            inicio = indice_fim
        return unidades


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


def test_estrategia_estrutural_deve_priorizar_estrutura_markdown():
    texto = "# Guia\n\nTexto introdutório.\n\n## Instalação\n\n- Baixar pacote\n- Executar instalador\n\nParágrafo final."
    estrategia = EstrategiaChunkingEstrutural(tamanho_trecho=45, sobreposicao_trecho=0)

    trechos = estrategia.gerar_trechos(texto)

    assert [trecho.conteudo for trecho in trechos] == [
        "# Guia\n\nTexto introdutório.\n\n## Instalação",
        "- Baixar pacote\n- Executar instalador",
        "Parágrafo final.",
    ]
    assert [trecho.indice_trecho for trecho in trechos] == [0, 1, 2]
    assert all(trecho.tamanho_caracteres <= 45 for trecho in trechos)
    assert trechos[0].indice_inicio == 0
    assert trechos[0].indice_fim == len(trechos[0].conteudo)


def test_estrategia_estrutural_deve_quebrar_texto_longo_por_frases_e_manter_sobreposicao():
    texto = (
        "Primeira frase curta. Segunda frase com detalhes úteis. "
        "Terceira frase encerra o primeiro parágrafo.\n\n"
        "Quarto período abre outro parágrafo. Quinto período fecha o texto."
    )
    estrategia = EstrategiaChunkingEstrutural(tamanho_trecho=70, sobreposicao_trecho=10)

    trechos = estrategia.gerar_trechos(texto)

    assert len(trechos) == 4
    assert trechos[0].conteudo == "Primeira frase curta. Segunda frase com detalhes úteis."
    assert "Terceira frase encerra" in trechos[1].conteudo
    assert "Quarto período" in trechos[2].conteudo
    assert "Quinto período fecha o texto." in trechos[3].conteudo
    assert trechos[1].indice_inicio == trechos[0].indice_fim - 10
    assert all(trecho.tamanho_caracteres <= 70 for trecho in trechos)


def test_estrategia_estrutural_deve_retornar_trecho_unico_para_texto_curto():
    texto = "Texto curto com uma única ideia."
    estrategia = EstrategiaChunkingEstrutural(tamanho_trecho=200, sobreposicao_trecho=30)

    trechos = estrategia.gerar_trechos(texto)

    assert trechos == [
        TrechoGerado(
            indice_trecho=0,
            conteudo=texto,
            indice_inicio=0,
            indice_fim=len(texto),
            tamanho_caracteres=len(texto),
        )
    ]


def test_estrategia_estrutural_deve_exigir_cerca_de_fechamento_com_tamanho_compativel():
    texto = (
        "# Exemplo\n\n"
        "Antes.\n\n"
        "````markdown\n"
        "```python\n"
        "print('interno')\n"
        "```\n"
        "````\n\n"
        "Depois."
    )
    estrategia = EstrategiaChunkingEstrutural(tamanho_trecho=70, sobreposicao_trecho=0)

    trechos = estrategia.gerar_trechos(texto)

    assert len(trechos) == 2
    assert "````markdown\n```python\nprint('interno')\n```\n````" in trechos[0].conteudo
    assert trechos[0].conteudo.endswith("````")
    assert trechos[1].conteudo == "Depois."


def test_estrategia_estrutural_deve_preservar_bloco_de_codigo_markdown_quando_couber_no_limite():
    texto = "# Exemplo\n\nAntes do código.\n\n```python\ndef ola():\n    return 'oi'\n```\n\nDepois do código."
    estrategia = EstrategiaChunkingEstrutural(tamanho_trecho=80, sobreposicao_trecho=0)

    trechos = estrategia.gerar_trechos(texto)

    assert len(trechos) == 2
    assert "```python\ndef ola():\n    return 'oi'\n```" in trechos[0].conteudo
    assert trechos[0].conteudo.endswith("```")
    assert trechos[1].conteudo == "Depois do código."
    assert all(trecho.tamanho_caracteres <= 80 for trecho in trechos)


def test_contador_tokens_aproximado_deve_medir_palavras():
    medidor = ContadorTokensAproximadoPorPalavras()

    assert medidor.medir("um  dois\ntrês") == 3


def test_estrategia_por_tokens_deve_respeitar_tamanho_maximo_aproximado():
    medidor = ContadorTokensAproximadoPorPalavras()
    estrategia = EstrategiaChunkingPorMedidaComSobreposicao(
        tamanho_maximo=4,
        sobreposicao=1,
        medidor=medidor,
    )

    trechos = estrategia.gerar_trechos("um dois três quatro cinco seis sete oito nove")

    assert [medidor.medir(trecho.conteudo) for trecho in trechos] == [4, 4, 3]
    assert all(medidor.medir(trecho.conteudo) <= 4 for trecho in trechos)


def test_estrategia_por_tokens_deve_manter_sobreposicao_aproximada():
    estrategia = EstrategiaChunkingPorMedidaComSobreposicao(
        tamanho_maximo=4,
        sobreposicao=2,
        medidor=ContadorTokensAproximadoPorPalavras(),
    )

    trechos = estrategia.gerar_trechos("um dois três quatro cinco seis sete")

    palavras_por_trecho = [trecho.conteudo.split() for trecho in trechos]
    assert palavras_por_trecho == [
        ["um", "dois", "três", "quatro"],
        ["três", "quatro", "cinco", "seis"],
        ["cinco", "seis", "sete"],
    ]
    assert palavras_por_trecho[0][-2:] == palavras_por_trecho[1][:2]
    assert palavras_por_trecho[1][-2:] == palavras_por_trecho[2][:2]


def test_estrategia_por_medida_deve_avancar_apos_unidade_sobredimensionada():
    estrategia = EstrategiaChunkingPorMedidaComSobreposicao(
        tamanho_maximo=50,
        sobreposicao=40,
        medidor=MedidorComUnidadeSobredimensionada(),
    )

    trechos = estrategia.gerar_trechos("enorme medio pequeno")

    assert [trecho.conteudo for trecho in trechos] == [
        "enorme",
        "medio pequeno",
    ]
    assert [trecho.indice_inicio for trecho in trechos] == [0, 7]
