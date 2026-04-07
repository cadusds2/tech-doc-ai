def dividir_em_trechos(texto: str, tamanho_trecho: int, sobreposicao: int) -> list[str]:
    texto_limpo = " ".join(texto.split())
    if not texto_limpo:
        return []

    passo = max(1, tamanho_trecho - sobreposicao)
    trechos: list[str] = []
    for inicio in range(0, len(texto_limpo), passo):
        trecho = texto_limpo[inicio : inicio + tamanho_trecho].strip()
        if trecho:
            trechos.append(trecho)
        if inicio + tamanho_trecho >= len(texto_limpo):
            break
    return trechos
