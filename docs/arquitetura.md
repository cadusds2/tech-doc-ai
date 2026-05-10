# Arquitetura do projeto

Este documento define a arquitetura oficial do Tech Doc AI após a consolidação dos módulos legados.

## Estrutura oficial

```text
app/
  api/
    routes/
    schemas/
  services/
  repositories/
  domain/
  infra/
  core/
  dependencias.py
  main.py
```

## Responsabilidades por camada

- **`app/api`**: camada HTTP. Contém roteadores FastAPI em `routes` e contratos Pydantic de entrada e saída em `schemas`.
- **`app/services`**: casos de uso e regras de negócio. Coordena parsing, chunking, ingestão, indexação, recuperação semântica e geração contextual.
- **`app/repositories`**: acesso a dados. Centraliza persistência de documentos, trechos, embeddings e consultas semânticas.
- **`app/domain`**: modelos de domínio independentes da API e da infraestrutura.
- **`app/infra`**: infraestrutura de banco, sessão SQLAlchemy, criação de extensão `pgvector` e modelos ORM.
- **`app/core`**: recursos transversais, como configuração, logging e tratadores globais de exceção.

## Módulos legados removidos

Os itens legados abaixo foram removidos ou mantidos apenas como compatibilidade temporária para evitar duplicidade de responsabilidades e divergência de imports:

- `app/servicos/`
- `app/repositorios/`
- `app/rotas/`
- `app/dominio/`
- `app/configuracao.py` (compatibilidade temporária que reexporta `app/core/config.py`)

## Comparação de responsabilidades

| Responsabilidade | Implementação legada | Implementação oficial |
| --- | --- | --- |
| Chunking | Função simples em `app/servicos/chunker.py`. | Estratégia validada e serviço dedicado em `app/services/chunking.py`. |
| Parsing | Parser direto em `app/servicos/parser_documentos.py`. | Parser com exceções específicas e fallback explícito em `app/services/parser_documentos.py`. |
| Embeddings | Classe única com fallback usando `numpy`. | Serviço com protocolo de provedor, implementação determinística sem `numpy` e integração opcional com `sentence-transformers`. |
| RAG | Serviço monolítico em `app/servicos/rag.py`. | Serviços separados em ingestão, indexação vetorial, recuperação semântica e geração contextual. |
| Repositório | Salvamento de documento e trechos em uma única operação. | Persistência granular de metadados, trechos, embeddings, limpeza e busca semântica. |
| Rotas | Rotas em `app/rotas` com contratos misturados ao domínio. | Rotas em `app/api/routes` e schemas em `app/api/schemas`. |
| Domínio | Modelos HTTP e modelos de resposta no mesmo arquivo. | Modelo de domínio `DocumentoIngerido` separado dos schemas da API. |
| Configuração | Configuração duplicada em `app/configuracao.py`. | Configuração única em `app/core/config.py`, com `app/configuracao.py` apenas como compatibilidade temporária. |

## Fluxo de ingestão

1. `POST /documentos/ingestao` recebe um arquivo.
2. `ServicoParserDocumentos` extrai texto do arquivo.
3. `ServicoIngestaoDocumentos` salva os metadados do documento.
4. `ServicoChunkingDocumentos` gera trechos normalizados.
5. `RepositorioDocumentos` persiste os trechos.
6. `ServicoIndexacaoVetorial` gera embeddings e atualiza os trechos pendentes quando a indexação está habilitada.

## Fluxo de consulta RAG

1. `POST /chat/perguntar` recebe a pergunta.
2. `ServicoRecuperacaoHibrida` gera embedding da pergunta para a busca vetorial.
3. `RepositorioDocumentos.buscar_trechos_similares` busca trechos similares no `pgvector`.
4. `RepositorioDocumentos.buscar_trechos_por_texto` executa busca lexical em `TrechoORM.conteudo` com os termos da pergunta.
5. `ServicoRecuperacaoHibrida` combina os resultados com a fórmula `peso_busca_vetorial * pontuacao_vetorial + peso_busca_lexical * pontuacao_lexical`, remove duplicidades por `trecho_id` e ordena pela pontuação final.
6. `ServicoConsultaRAG` monta o contexto com fontes.
7. `GeradorRespostaContextual` gera a resposta final.
8. A API retorna resposta e fontes utilizadas com pontuação híbrida.

Os pesos são configuráveis por `PESO_BUSCA_VETORIAL` e `PESO_BUSCA_LEXICAL`. Os valores padrão são `0.7` e `0.3`, respectivamente, para favorecer a busca semântica sem descartar correspondências exatas.

## Regra para novos módulos

Novas funcionalidades devem respeitar a estrutura oficial. Não devem ser recriados diretórios em português para serviços, repositórios, rotas ou domínio.

## Estratégia de logs e rastreabilidade

1. Toda requisição HTTP passa pelo `MiddlewareIdentificadorRequisicao`, que reutiliza o cabeçalho `X-Request-ID` quando informado ou gera um identificador novo quando ele não existe.
2. O identificador fica disponível em contexto local da execução por `contextvars`, é devolvido no cabeçalho `X-Request-ID` da resposta e é anexado aos registros pelo filtro de logging.
3. Tarefas de processamento em background recebem uma cópia do identificador da requisição que as agendou, mantendo a correlação entre upload, processamento, chunking e indexação.
4. As mensagens de log são padronizadas em português brasileiro e registram apenas metadados operacionais, como identificador do documento, nome do arquivo, quantidades, tempos e tipo do erro.
5. Conteúdo completo de documentos, trechos recuperados e perguntas de usuários não deve ser registrado em logs para reduzir exposição de dados sensíveis.
6. Pontos principais observados:
   - recebimento e agendamento da ingestão;
   - início e fim do processamento de ingestão;
   - falhas de parser;
   - quantidade de trechos gerados;
   - quantidade de embeddings indexados;
   - tempo da busca vetorial;
   - quantidade de fontes retornadas pela consulta RAG.
