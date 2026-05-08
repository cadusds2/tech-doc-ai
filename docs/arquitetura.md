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

Os diretórios abaixo foram removidos para evitar duplicidade de responsabilidades e divergência de imports:

- `app/servicos/`
- `app/repositorios/`
- `app/rotas/`
- `app/dominio/`
- `app/configuracao.py`

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
| Configuração | Configuração duplicada em `app/configuracao.py`. | Configuração única em `app/core/config.py`. |

## Fluxo de ingestão

1. `POST /documentos/ingestao` recebe um arquivo.
2. `ServicoParserDocumentos` extrai texto do arquivo.
3. `ServicoIngestaoDocumentos` salva os metadados do documento.
4. `ServicoChunkingDocumentos` gera trechos normalizados.
5. `RepositorioDocumentos` persiste os trechos.
6. `ServicoIndexacaoVetorial` gera embeddings e atualiza os trechos pendentes quando a indexação está habilitada.

## Fluxo de consulta RAG

1. `POST /chat/perguntar` recebe a pergunta.
2. `ServicoRecuperacaoSemantica` gera embedding da pergunta.
3. `RepositorioDocumentos` busca trechos similares no `pgvector`.
4. `ServicoConsultaRAG` monta o contexto com fontes.
5. `GeradorRespostaContextual` gera a resposta final.
6. A API retorna resposta e fontes utilizadas.

## Regra para novos módulos

Novas funcionalidades devem respeitar a estrutura oficial. Não devem ser recriados diretórios em português para serviços, repositórios, rotas ou domínio.
