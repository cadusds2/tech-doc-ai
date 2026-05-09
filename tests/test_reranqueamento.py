from app.services.consulta_rag import TrechoRecuperado
from app.services.reranqueamento import ReranqueadorHeuristicoTrechos


def _trecho(trecho_id: int, conteudo: str, pontuacao: float) -> TrechoRecuperado:
    return TrechoRecuperado(
        trecho_id=trecho_id,
        documento_id=1,
        nome_arquivo="manual.md",
        conteudo=conteudo,
        pontuacao_similaridade=pontuacao,
    )


def test_reranqueador_heuristico_deve_priorizar_termos_da_pergunta_e_tamanho_util():
    trechos = [
        _trecho(
            trecho_id=1,
            conteudo="Texto muito curto sobre outro assunto.",
            pontuacao=0.95,
        ),
        _trecho(
            trecho_id=2,
            conteudo=(
                "O reranqueamento avalia termos da pergunta, tamanho útil do trecho e pontuação original "
                "para escolher o melhor contexto antes da resposta."
            ),
            pontuacao=0.70,
        ),
        _trecho(
            trecho_id=3,
            conteudo="A pontuação vetorial original continua sendo considerada na ordenação final.",
            pontuacao=0.80,
        ),
    ]
    reranqueador = ReranqueadorHeuristicoTrechos()

    trechos_reranqueados = reranqueador.reranquear(
        pergunta="Como o reranqueamento usa termos da pergunta e tamanho útil?",
        trechos=trechos,
    )

    assert [trecho.trecho_id for trecho in trechos_reranqueados] == [2, 3, 1]


def test_reranqueador_heuristico_deve_manter_pontuacao_original_como_desempate_relevante():
    trechos = [
        _trecho(
            trecho_id=1,
            conteudo="RAG usa recuperação e geração para responder perguntas.",
            pontuacao=0.40,
        ),
        _trecho(
            trecho_id=2,
            conteudo="RAG usa recuperação e geração para responder perguntas.",
            pontuacao=0.90,
        ),
    ]
    reranqueador = ReranqueadorHeuristicoTrechos()

    trechos_reranqueados = reranqueador.reranquear(
        pergunta="RAG recuperação geração", trechos=trechos
    )

    assert [trecho.trecho_id for trecho in trechos_reranqueados] == [2, 1]


def test_reranqueador_heuristico_deve_comparar_termos_por_tokens_inteiros():
    trechos = [
        _trecho(
            trecho_id=1,
            conteudo=(
                "A capitalização do texto é frágil e descreve apicultura, "
                "mas não menciona os termos técnicos da pergunta."
            ),
            pontuacao=0.95,
        ),
        _trecho(
            trecho_id=2,
            conteudo="A API do RAG consulta SQL para recuperar contexto relevante.",
            pontuacao=0.50,
        ),
    ]
    reranqueador = ReranqueadorHeuristicoTrechos()

    trechos_reranqueados = reranqueador.reranquear(
        pergunta="API RAG SQL", trechos=trechos
    )

    assert [trecho.trecho_id for trecho in trechos_reranqueados] == [2, 1]
