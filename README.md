# Tech Doc AI

Sistema RAG para documentação técnica corporativa com Python, FastAPI e PostgreSQL + pgvector.

## Objetivo do MVP

Este MVP implementa o núcleo do fluxo RAG:

1. Ingestão de documento (`.txt`, `.md`, `.pdf`).
2. Extração de texto e chunking básico.
3. Geração de embeddings.
4. Persistência vetorial no PostgreSQL com pgvector.
5. Busca semântica por similaridade.
6. Resposta com fontes utilizadas.

## Arquitetura em camadas

```text
app/
  configuracao.py
  main.py
  dependencias.py
  dominio/
  rotas/
  servicos/
  repositorios/
  infra/
```

- **rotas**: contratos HTTP e validação de entrada/saída.
- **serviços**: regras de negócio e orquestração do fluxo RAG.
- **repositórios**: acesso a dados com SQLAlchemy.
- **domínio**: modelos Pydantic de request/response.
- **infra**: conexão com banco e modelos ORM.
- **configuração**: centralização de variáveis de ambiente.

## Endpoints

### `GET /healthcheck`
Retorna status da API.

### `POST /documentos/ingestao`
Recebe um arquivo multipart (`arquivo`) e indexa seu conteúdo.

**Resposta esperada:**
```json
{
  "documento_id": 1,
  "nome_arquivo": "guia.md",
  "quantidade_trechos": 12
}
```

### `POST /perguntas`
Busca semanticamente os trechos mais próximos da pergunta.

**Body:**
```json
{
  "pergunta": "Como configurar autenticação?",
  "limite": 4
}
```

## Como executar com Docker

```bash
docker compose up --build
```

API disponível em: `http://localhost:8000`

## Como executar localmente

1. Crie e ative um ambiente virtual.
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Copie variáveis:
   ```bash
   cp .env.exemplo .env
   ```
4. Suba um PostgreSQL com extensão pgvector.
5. Rode a API:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testes

```bash
pytest
```

## Observações técnicas do MVP

- O serviço de embeddings tenta usar `sentence-transformers`.
- Se o modelo não puder ser carregado (ex.: sem internet/modelo), o sistema usa um embedding determinístico de fallback para manter o fluxo funcional.
- A resposta da pergunta neste MVP é formada pela concatenação dos trechos recuperados, priorizando rastreabilidade com fontes.

## Próximas evoluções naturais

- Trocar resposta concatenada por síntese com LLM.
- Adicionar migrações com Alembic.
- Cobrir repositórios e serviços com testes de integração.
- Adicionar autenticação e controle de permissões por documento.
- Instrumentar observabilidade (logs estruturados + métricas).
