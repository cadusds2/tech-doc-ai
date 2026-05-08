# Decisões técnicas

## 1) FastAPI como base

FastAPI foi escolhido por produtividade, tipagem, validação com Pydantic e documentação automática.

## 2) Estrutura oficial em camadas

A estrutura principal fica padronizada em:

- `app/api`
- `app/services`
- `app/repositories`
- `app/domain`
- `app/infra`
- `app/core`

Essa decisão evita duplicidade entre módulos em português e módulos em inglês, reduz ambiguidade nos imports e facilita a evolução do projeto.

## 3) Remoção de módulos legados

Foram removidos os diretórios `app/servicos`, `app/repositorios`, `app/rotas` e `app/dominio`. As responsabilidades úteis já estavam representadas nos módulos oficiais ou foram consolidadas neles.

## 4) Configuração centralizada

Todas as configurações ficam em `app/core/config.py`, incluindo metadados da API, logging, banco de dados, embeddings, chunking e indexação. A duplicidade com `app/configuracao.py` foi eliminada.

## 5) PostgreSQL + pgvector como infraestrutura vetorial

A aplicação usa SQLAlchemy e `pgvector` para armazenar embeddings em `trechos.embedding`. A criação da extensão `vector` é controlada por `HABILITAR_PGVECTOR`.

## 6) Estratégia inicial de chunking por tamanho com sobreposição

Foi adotada uma estratégia simples de chunking por número de caracteres, com sobreposição configurável entre trechos.

### Limitações conhecidas

- O corte é cego ao contexto semântico e pode quebrar frases, listas e blocos de código.
- Não há variação por tipo de documento; PDF, Markdown e TXT usam a mesma regra.
- A estratégia considera caracteres, não tokens do modelo de embeddings.
- A normalização de espaços reduz ruídos, mas pode alterar formatação relevante.

### Melhorias futuras sugeridas

- Chunking orientado por estrutura, como títulos, seções, parágrafos e blocos de código.
- Chunking por contagem de tokens para aderência ao modelo de embeddings.
- Estratégias híbridas com fallback entre estrutura e tamanho.
- Metadados extras por trecho, como página, seção e caminho hierárquico do documento.
- Pós-processamento para evitar trechos muito curtos no final.

## 7) Separação entre recuperação e geração

A consulta RAG fica dividida em três papéis:

- `ServicoRecuperacaoSemantica`: gera embedding da pergunta e recupera trechos similares.
- `GeradorRespostaContextual`: gera a resposta textual a partir do contexto recuperado.
- `ServicoConsultaRAG`: orquestra recuperação, montagem de contexto, resposta e fontes.

Essa separação permite substituir futuramente o provedor de modelo de linguagem sem alterar a rota HTTP ou a busca vetorial.
