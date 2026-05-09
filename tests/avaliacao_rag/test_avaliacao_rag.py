from tests.avaliacao_rag.avaliar_rag import executar_avaliacao


def test_avaliacao_rag_deve_atender_criterios_minimos():
    resumo = executar_avaliacao()

    assert resumo["aprovado"], resumo["resultados"]
    assert resumo["total_casos"] >= 4


def test_avaliacao_rag_deve_medir_metricas_obrigatorias():
    resumo = executar_avaliacao()

    for resultado in resumo["resultados"]:
        metricas = resultado["metricas"]
        assert "fonte_correta_presente" in metricas
        assert "quantidade_fontes_uteis" in metricas
        assert "ausencia_resposta_sem_contexto" in metricas
        assert "resposta_estavel" in metricas
