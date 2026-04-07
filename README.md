# Tech Doc AI

Scaffold inicial para um projeto RAG de documentação técnica com FastAPI.

## Estrutura de pastas

```text
app/
  api/
    routes/
    schemas/
  core/
  services/
  repositories/
  domain/
  main.py
docs/
tests/
```

## Pré-requisitos

- Python 3.11+
- `pip`
- PostgreSQL com extensão `pgvector` (ex.: imagem `pgvector/pgvector:pg16`)

## Como executar localmente

1. Crie e ative um ambiente virtual.
2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Crie o arquivo de variáveis de ambiente:

```bash
cp .env.example .env
```

4. Suba a aplicação:

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`.

## Endpoints disponíveis

### `GET /health`

Retorna o estado básico da API.

Exemplo de resposta:

```json
{
  "status": "ok"
}
```

### `POST /documentos/ingestao`

Ingere arquivo textual (`.txt`, `.md`, `.pdf`), gera chunks e executa indexação vetorial dos trechos ainda sem embedding.

## Testes

```bash
pytest
```

## Embeddings e indexação vetorial

- A aplicação persiste chunks em PostgreSQL e usa `pgvector` para armazenar embeddings na coluna `trechos.embedding`.
- A geração de embeddings fica isolada em `app/services/embeddings.py`.
- O fluxo de indexação vetorial fica isolado em `app/services/indexacao_vetorial.py`.
- A rotina `indexar_trechos_pendentes` processa apenas chunks sem embedding.
- A rotina `preparar_reindexacao_documento` limpa embeddings de um documento e deixa a estrutura pronta para futura reindexação completa.

## Variáveis de ambiente

As variáveis abaixo devem estar presentes em `.env` (ou no ambiente de execução):

- `URL_BANCO`: URL de conexão com PostgreSQL.
- `HABILITAR_PGVECTOR`: habilita criação da extensão `vector` na inicialização.
- `MODELO_EMBEDDINGS`: nome do modelo de embeddings (quando `sentence-transformers` estiver instalado).
- `DIMENSAO_EMBEDDINGS`: dimensão dos vetores armazenados no `pgvector`.
- `TAMANHO_LOTE_INDEXACAO`: quantidade máxima de chunks processados por rotina.
- `TAMANHO_TRECHO`: tamanho de chunk na ingestão.
- `SOBREPOSICAO_TRECHO`: sobreposição entre chunks.
