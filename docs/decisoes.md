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

## 6) Estratégia estrutural de chunking com limite e sobreposição

A aplicação passou a usar `EstrategiaChunkingEstrutural` como estratégia padrão de chunking. A estratégia mantém os limites configuráveis por `tamanho_trecho` e `sobreposicao_trecho`, mas prioriza pontos de quebra que preservam a estrutura do documento antes de recorrer a cortes por tamanho.

Para conteúdo com características de Markdown, a ordem de preferência das unidades estruturais é:

- títulos e subtítulos;
- parágrafos;
- listas;
- blocos de código cercados por crases ou tils.

Para textos simples, a estratégia prioriza parágrafos e frases, preservando trechos curtos em uma única unidade sempre que o conteúdo couber no limite configurado. Blocos ou frases maiores que `tamanho_trecho` ainda podem ser divididos por caracteres para garantir o limite máximo do trecho.

A geração continua preenchendo os metadados de `TrechoGerado`, incluindo `indice_trecho`, `indice_inicio`, `indice_fim` e `tamanho_caracteres`. A estratégia antiga, `EstrategiaChunkingTamanhoComSobreposicao`, permanece disponível para casos em que um corte puramente posicional seja suficiente.

### Limitações conhecidas

- A detecção de Markdown é heurística e se baseia em títulos, listas e cercas de código.
- A estratégia considera caracteres, não tokens do modelo de embeddings.
- A sobreposição pode começar no meio de uma palavra quando for necessário reaproveitar o final do trecho anterior.
- Blocos de código maiores que o limite máximo ainda precisam ser quebrados por tamanho.

### Melhorias futuras sugeridas

- Chunking por contagem de tokens para aderência ao modelo de embeddings.
- Metadados extras por trecho, como página, seção e caminho hierárquico do documento.
- Pós-processamento para evitar trechos muito curtos no final.
- Detecção explícita do tipo de arquivo para reduzir dependência de heurísticas.

## 7) Separação entre recuperação e geração

A consulta RAG fica dividida em três papéis:

- `ServicoRecuperacaoSemantica`: gera embedding da pergunta e recupera trechos similares.
- `GeradorRespostaContextual`: gera a resposta textual a partir do contexto recuperado.
- `ServicoConsultaRAG`: orquestra recuperação, montagem de contexto, resposta e fontes.

Essa separação permite substituir futuramente o provedor de modelo de linguagem sem alterar a rota HTTP ou a busca vetorial.

## 8) Reranqueamento heurístico antes da geração

A consulta RAG passa a aceitar um `ReranqueadorTrechos` entre a recuperação híbrida e a montagem do contexto. A primeira implementação, `ReranqueadorHeuristicoTrechos`, usa sinais simples e explicáveis:

- presença de termos da pergunta no trecho;
- tamanho útil do conteúdo, penalizando trechos vazios, curtos demais ou longos demais;
- pontuação original da recuperação vetorial ou híbrida.

O reranqueamento fica habilitado por padrão pela configuração `HABILITAR_RERANQUEAMENTO`, mas pode ser desligado para comparar resultados, investigar regressões ou preservar estritamente a ordenação original da recuperação. A interface foi isolada em `app/services/reranqueamento.py` para permitir a troca futura por um reranqueador baseado em modelo sem alterar a rota HTTP nem o contrato principal de `ServicoConsultaRAG`.
