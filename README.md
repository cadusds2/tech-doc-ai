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

### `POST /chat/perguntar`

Recebe uma pergunta, busca os trechos mais relevantes semanticamente e retorna uma resposta contextualizada junto das fontes usadas.

Exemplo de requisição:

```json
{
  "pergunta": "Qual é o objetivo do projeto?",
  "limite_fontes": 4
}
```

Exemplo de resposta:

```json
{
  "resposta": "Resposta baseada nos trechos recuperados (...)",
  "fontes": [
    {
      "trecho_id": 12,
      "documento_id": 3,
      "nome_arquivo": "arquitetura.md",
      "conteudo": "...",
      "pontuacao_similaridade": 0.8731
    }
  ]
}
```

## Fluxo ponta a ponta do RAG (consulta)

A primeira versão funcional da consulta segue este fluxo:

1. **Pergunta**: a API recebe a pergunta no endpoint `POST /chat/perguntar`.
2. **Embedding**: o serviço de embeddings gera o vetor da pergunta.
3. **Busca vetorial**: o repositório consulta os chunks indexados no `pgvector`, ordenando por distância de cosseno.
4. **Contexto**: os trechos mais relevantes são organizados em um bloco de contexto com metadados de fonte.
5. **Resposta**: o gerador de resposta produz uma síntese baseada no contexto recuperado, sem prometer precisão absoluta.
6. **Fontes**: a API retorna a lista de fontes utilizadas (chunk, documento, conteúdo e pontuação de similaridade).

## Separação entre recuperação e geração

- **Recuperação (retrieval)**: `ServicoRecuperacaoSemantica` (embedding da pergunta + busca vetorial dos chunks).
- **Geração (generation)**: `GeradorRespostaContextual` (produção da resposta textual a partir do contexto).
- **Orquestração**: `ServicoConsultaRAG` (coordena as duas etapas e monta a resposta final da API).

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


## Contrato da API de consulta

A rota `POST /chat/perguntar` retorna sempre um objeto com dois campos principais:

- `resposta`: texto gerado a partir do contexto recuperado.
- `fontes`: lista de chunks usados na resposta (com metadados e pontuação de similaridade).

Esse contrato evita acoplamento no cliente e deixa explícito o que foi usado como base para a geração.

## Fluxo detalhado da consulta RAG

Fluxo ponta a ponta implementado nesta versão:

`pergunta -> embedding -> busca vetorial -> contexto -> resposta -> fontes`

1. **Pergunta**
   - O usuário envia `pergunta` e `limite_fontes` para `POST /chat/perguntar`.
2. **Embedding**
   - `ServicoRecuperacaoSemantica` gera o embedding da pergunta via `ServicoEmbeddings`.
3. **Busca vetorial**
   - `RepositorioDocumentos.buscar_trechos_similares` consulta os chunks com embedding e ordena por distância de cosseno.
4. **Contexto**
   - `ServicoConsultaRAG` monta um bloco textual com os trechos mais relevantes, mantendo metadados de origem.
5. **Resposta**
   - `GeradorRespostaContextual` envia pergunta + contexto para um provedor de geração textual e adiciona aviso de limitação (sem prometer precisão absoluta).
6. **Fontes**
   - A API devolve a resposta junto da lista de fontes utilizadas para rastreabilidade.

