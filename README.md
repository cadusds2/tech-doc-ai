# Tech Doc AI

API RAG para documentação técnica com FastAPI, ingestão de arquivos, geração de trechos, embeddings e consulta semântica com fontes rastreáveis.

## Estrutura oficial do projeto

A estrutura principal do projeto fica padronizada em módulos em inglês dentro de `app/`:

```text
app/
  api/
    routes/      # endpoints HTTP
    schemas/     # contratos de entrada e saída da API
  services/      # regras de negócio e orquestração de casos de uso
  repositories/  # persistência e consultas ao banco
  domain/        # modelos de domínio independentes de transporte e infraestrutura
  infra/         # banco, ORM e integrações de infraestrutura
  core/          # configuração, logging e tratamento transversal de exceções
  dependencias.py
  main.py

docs/
tests/
```

Os diretórios legados em português (`app/servicos`, `app/repositorios`, `app/rotas` e `app/dominio`) foram removidos. Novos módulos devem ser criados apenas na estrutura oficial acima.

## Mapa de migração dos módulos legados

| Legado removido | Módulo oficial | Decisão |
| --- | --- | --- |
| `app/servicos/chunker.py` | `app/services/chunking.py` | Lógica mantida e expandida com estratégia tipada, índices e validação de parâmetros. |
| `app/servicos/parser_documentos.py` | `app/services/parser_documentos.py` | Lógica mantida com erros específicos, `strip()` e tratamento de indisponibilidade do leitor de PDF. |
| `app/servicos/embeddings.py` | `app/services/embeddings.py` | Lógica mantida sem dependência obrigatória de `numpy`, com provedor determinístico e provedor opcional via `sentence-transformers`. |
| `app/servicos/rag.py` | `app/services/ingestao_documentos.py`, `app/services/indexacao_vetorial.py`, `app/services/consulta_rag.py` | Orquestração monolítica separada em ingestão, indexação, recuperação e geração contextual. |
| `app/repositorios/repositorio_documentos.py` | `app/repositories/repositorio_documentos.py` | Persistência separada em metadados, trechos, atualização de embeddings e busca semântica. |
| `app/rotas/healthcheck.py` | `app/api/routes/health.py` | Rota oficial `GET /health` com metadados da aplicação. |
| `app/rotas/documentos.py` | `app/api/routes/documentos.py` | Rota oficial `POST /documentos/ingestao` integrada ao serviço de ingestão. |
| `app/rotas/perguntas.py` | `app/api/routes/chat.py` | Rota oficial `POST /chat/perguntar` com contrato orientado a chat e fontes. |
| `app/dominio/modelos.py` | `app/domain/documento.py` e `app/api/schemas/*` | Entidade de domínio separada dos contratos HTTP. |
| `app/configuracao.py` | `app/core/config.py` | Configuração centralizada em `core`; o módulo legado permanece apenas como compatibilidade temporária e reexporta a configuração oficial. |

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

3. Crie o arquivo de variáveis de ambiente, se necessário:

```bash
cp .env.example .env
```

4. Suba a aplicação:

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`.

A interface web simples para operar os fluxos principais fica disponível em `http://127.0.0.1:8000/interface`. Ela permite verificar a saúde da API, enviar documentos, acompanhar o status de processamento e fazer perguntas ao chat com exibição das fontes retornadas.

## Endpoints disponíveis

### `GET /health`

Retorna o estado básico da API e metadados da aplicação.

Exemplo de resposta:

```json
{
  "status": "ok",
  "aplicacao": "Tech Doc AI",
  "versao": "0.1.0",
  "ambiente": "desenvolvimento",
  "horario_utc": "2026-05-08T00:00:00Z"
}
```

### `POST /documentos/ingestao`

Cria o registro do documento rapidamente e retorna `201 Created` com `status_processamento=recebido`. O parser, a geração de trechos e a indexação rodam fora da requisição principal por meio de `BackgroundTasks` do FastAPI.

Limites e validações do upload:

- Tamanho máximo padrão: 10 MiB por arquivo (`TAMANHO_MAXIMO_UPLOAD_BYTES=10485760`).
- Tipos aceitos: `.txt`, `.md` e `.pdf`.
- Nomes de arquivo são normalizados e sanitizados antes do processamento.
- Uploads sem nome, vazios, com extensões inválidas ou com extensões suspeitas são rejeitados com mensagens genéricas.
- Os logs registram apenas metadados resumidos, como nome normalizado, tamanho e motivo da rejeição, sem gravar o conteúdo do arquivo.

Estados possíveis de processamento:

1. `recebido`: arquivo aceito e processamento agendado.
2. `texto_extraido`: parser concluiu a extração textual.
3. `trechos_gerados`: chunking concluiu a geração de trechos persistidos.
4. `indexado`: processamento concluído; quando `HABILITAR_PGVECTOR=true`, os embeddings foram persistidos.
5. `erro`: houve falha no parser, chunking ou indexação, com resumo salvo em `mensagem_erro_processamento`.

Exemplo de envio:

```bash
curl -F "arquivo=@docs/arquitetura.md" http://127.0.0.1:8000/documentos/ingestao
```

Exemplo de resposta inicial:

```json
{
  "documento_id": 1,
  "nome_arquivo": "arquitetura.md",
  "tipo_arquivo": "md",
  "tamanho_bytes": 2048,
  "quantidade_caracteres": 0,
  "status_processamento": "recebido",
  "mensagem_erro_processamento": null,
  "criado_em": "2026-05-09T12:00:00Z",
  "atualizado_em": "2026-05-09T12:00:00Z"
}
```

### `GET /documentos/{documento_id}`

Consulta metadados e status atual de processamento do documento. Use esse endpoint para acompanhar a transição de `recebido` até `indexado` ou identificar falhas persistidas em `erro`.

Exemplo:

```bash
curl http://127.0.0.1:8000/documentos/1
```

Exemplo de falha persistida:

```json
{
  "documento_id": 1,
  "nome_arquivo": "planilha.csv",
  "tipo_arquivo": "csv",
  "tamanho_bytes": 128,
  "quantidade_caracteres": 0,
  "status_processamento": "erro",
  "mensagem_erro_processamento": "Tipo de arquivo não suportado: csv",
  "criado_em": "2026-05-09T12:00:00Z",
  "atualizado_em": "2026-05-09T12:00:02Z"
}
```

A arquitetura já separa o agendamento (`AgendadorProcessamentoDocumentos`) do processamento (`ProcessadorDocumentos`), permitindo substituir o agendador baseado em `BackgroundTasks` por fila externa, como Redis, Celery ou equivalente, sem mudar o contrato HTTP.

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
  "resposta": "Resposta baseada nos trechos recuperados (...) ",
  "fontes": [
    {
      "trecho_id": 12,
      "documento_id": 3,
      "nome_arquivo": "arquitetura.md",
      "conteudo": "...",
      "pontuacao_similaridade": 0.8731,
      "pagina": 2,
      "secao": "Recuperação híbrida",
      "titulo_contexto": "Recuperação híbrida",
      "caminho_hierarquico": "Arquitetura > Recuperação híbrida"
    }
  ]
}
```

## Fluxo ponta a ponta do RAG

1. **Pergunta**: a API recebe `pergunta` e `limite_fontes` no endpoint `POST /chat/perguntar`.
2. **Embedding**: `ServicoRecuperacaoHibrida` gera o vetor da pergunta por meio de `ServicoEmbeddings` para manter a busca vetorial existente.
3. **Busca vetorial**: `RepositorioDocumentos.buscar_trechos_similares` consulta os trechos indexados no `pgvector`, ordenando por distância de cosseno.
4. **Busca lexical**: `RepositorioDocumentos.buscar_trechos_por_texto` procura termos da pergunta em `TrechoORM.conteudo`, pontuando a cobertura dos termos e dando bônus para frase exata.
5. **Combinação**: o serviço remove duplicidades por `trecho_id` e calcula `pontuacao_combinada = peso_busca_vetorial * pontuacao_vetorial + peso_busca_lexical * pontuacao_lexical`.
6. **Contexto**: `ServicoConsultaRAG` organiza os trechos combinados em um bloco textual com metadados de origem.
7. **Resposta**: `GeradorRespostaContextual` produz uma síntese baseada no contexto recuperado e explicita limitações.
8. **Fontes**: a API retorna a lista de fontes utilizadas, com documento, trecho, conteúdo, pontuação híbrida e metadados opcionais de origem (`pagina`, `secao`, `titulo_contexto` e `caminho_hierarquico`) quando extraídos de Markdown ou PDF.


## Configuração do provedor de modelo de linguagem

Por padrão, o projeto usa `PROVEDOR_MODELO_LINGUAGEM=heuristico`, uma alternativa local e determinística para testes e desenvolvimento. Esse modo não chama APIs externas e mantém a consulta RAG funcional mesmo sem chave de API.

Para usar OpenAI, configure as variáveis abaixo no `.env` ou no ambiente de execução:

```env
PROVEDOR_MODELO_LINGUAGEM=openai
MODELO_LINGUAGEM=gpt-4.1-mini
CHAVE_API_MODELO_LINGUAGEM=sua-chave-aqui
TEMPERATURA_MODELO_LINGUAGEM=0.2
TEMPO_LIMITE_MODELO_LINGUAGEM=30
```

Para usar Groq, crie uma chave no painel do Groq e configure:

```env
PROVEDOR_MODELO_LINGUAGEM=groq
MODELO_LINGUAGEM=llama-3.3-70b-versatile
CHAVE_API_MODELO_LINGUAGEM=sua-chave-da-groq
TEMPERATURA_MODELO_LINGUAGEM=0.2
TEMPO_LIMITE_MODELO_LINGUAGEM=30
```

O Groq possui plano gratuito para criação e testes, mas esse plano tem limites de requisições e tokens. Ao exceder os limites, o provedor pode retornar erro HTTP `429`; consulte os limites atuais no painel e na documentação oficial do Groq antes de usar em produção.

Também é possível usar outro provedor compatível informando a URL completa da API:

```env
PROVEDOR_MODELO_LINGUAGEM=openai_compativel
MODELO_LINGUAGEM=modelo-do-provedor
CHAVE_API_MODELO_LINGUAGEM=sua-chave-aqui
URL_API_MODELO_LINGUAGEM=https://provedor.exemplo/v1/chat/completions
TEMPERATURA_MODELO_LINGUAGEM=0.2
TEMPO_LIMITE_MODELO_LINGUAGEM=30
```

O prompt da consulta RAG exige resposta em português brasileiro e restringe a geração ao contexto recuperado. Se o provedor externo falhar, a aplicação registra logs estruturados e retorna uma mensagem segura sem expor detalhes internos ou a chave de API.

## Variáveis de ambiente

As variáveis abaixo podem ser definidas em `.env` ou no ambiente de execução. Elas correspondem diretamente aos campos reais de `app/core/config.py` e, por padrão, o banco local usa o nome `tech_doc_ai`, igual ao `docker-compose.yml`:

- `NOME_APP`: nome exibido pela API. Padrão: `Tech Doc AI`.
- `VERSAO_APP`: versão exibida pela API. Padrão: `0.1.0`.
- `AMBIENTE`: ambiente atual. Padrão: `desenvolvimento`.
- `HOST_API`: host sugerido para execução local. Padrão: `0.0.0.0`.
- `PORTA_API`: porta sugerida para execução local. Padrão: `8000`.
- `PREFIXO_API`: prefixo opcional para todas as rotas. Padrão: vazio.
- `NIVEL_LOG`: nível de logging. Padrão: `INFO`.
- `FORMATO_LOG`: formato das mensagens de logging. Padrão: inclui `identificador_requisicao`.
- `URL_BANCO`: URL de conexão com PostgreSQL. Padrão: `postgresql+psycopg://postgres:postgres@localhost:5432/tech_doc_ai`.
- `HABILITAR_PGVECTOR`: habilita criação da extensão `vector` na inicialização e indexação durante ingestão. Padrão: `true`.
- `MODELO_EMBEDDINGS`: nome do modelo de embeddings quando `sentence-transformers` estiver instalado. Padrão: `sentence-transformers/all-MiniLM-L6-v2`.
- `DIMENSAO_EMBEDDINGS`: dimensão dos vetores armazenados no `pgvector`. Padrão: `384`.
- `TAMANHO_LOTE_INDEXACAO`: quantidade máxima de trechos processados por rotina. Padrão: `100`.
- `TAMANHO_TRECHO`: tamanho de trecho por caracteres na ingestão quando `USAR_CHUNKING_POR_TOKENS=false`. Padrão: `800`.
- `SOBREPOSICAO_TRECHO`: sobreposição por caracteres entre trechos quando `USAR_CHUNKING_POR_TOKENS=false`. Padrão: `120`.
- `TAMANHO_MAXIMO_TOKENS_TRECHO`: tamanho máximo aproximado de cada trecho em tokens quando `USAR_CHUNKING_POR_TOKENS=true`. Padrão: `256`.
- `SOBREPOSICAO_TOKENS_TRECHO`: sobreposição aproximada em tokens entre trechos quando `USAR_CHUNKING_POR_TOKENS=true`. Padrão: `40`.
- `USAR_CHUNKING_POR_TOKENS`: alterna a estratégia de chunking para medição aproximada por tokens. Padrão: `false`.
- `LIMITE_BUSCA_PADRAO`: limite padrão para buscas RAG. Padrão: `4`.
- `PESO_BUSCA_VETORIAL`: peso da pontuação vetorial na recuperação híbrida. Padrão: `0.7`.
- `PESO_BUSCA_LEXICAL`: peso da pontuação lexical na recuperação híbrida. Padrão: `0.3`.
- `HABILITAR_RERANQUEAMENTO`: habilita reranqueamento heurístico antes da geração. Padrão: `true`.
- `TAMANHO_MAXIMO_UPLOAD_BYTES`: limite máximo de upload por arquivo. Padrão: `10485760` (10 MiB).
- `PROVEDOR_MODELO_LINGUAGEM`: seleciona o provedor de geração (`heuristico`, `local`, `openai`, `groq` ou `openai_compativel`). Padrão: `heuristico`.
- `MODELO_LINGUAGEM`: modelo usado pelo provedor externo compatível com completação de conversa. Padrão: `gpt-4.1-mini`.
- `CHAVE_API_MODELO_LINGUAGEM`: chave de API do provedor externo; obrigatória quando `PROVEDOR_MODELO_LINGUAGEM` for `openai`, `groq` ou `openai_compativel`. Padrão: não definida.
- `TEMPERATURA_MODELO_LINGUAGEM`: temperatura enviada ao provedor externo. Padrão: `0.2`.
- `TEMPO_LIMITE_MODELO_LINGUAGEM`: tempo limite, em segundos, para chamadas ao provedor externo. Padrão: `30.0`.
- `URL_API_MODELO_LINGUAGEM`: URL opcional para sobrescrever o endereço padrão do provedor externo, útil para provedores compatíveis. Padrão: não definida.

## Testes

```bash
pytest
```
