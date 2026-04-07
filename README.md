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

## Endpoint disponível

### `GET /health`

Retorna o estado básico da API.

Exemplo de resposta:

```json
{
  "status": "ok"
}
```

## Testes

```bash
pytest
```

## Escopo desta etapa

- Scaffold do projeto criado.
- FastAPI configurado com endpoint de saúde.
- Preparação para PostgreSQL e pgvector apenas na configuração.
- Sem implementação de ingestão de documentos e sem embeddings nesta etapa.
