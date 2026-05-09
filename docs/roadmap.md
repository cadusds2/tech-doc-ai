# Roadmap técnico

## 1. Visão geral do projeto
O **Tech Doc AI** é uma API para perguntas e respostas sobre documentação técnica usando arquitetura **RAG (Retrieval-Augmented Generation)**. O fluxo principal combina ingestão de arquivos, geração de embeddings, indexação vetorial em PostgreSQL com pgvector e consulta semântica com retorno de fontes para rastreabilidade.

Objetivos centrais do produto:
- reduzir tempo de busca por informação técnica;
- aumentar consistência de respostas com base em fontes internas;
- manter base evolutiva para múltiplos formatos e provedores de geração.

---

## 2. Estado atual
Resumo do estado observado no código e na documentação existente:

### 2.1 Funcionalidades já implementadas
- API FastAPI estruturada em camadas (rotas, schemas, serviços, repositórios e domínio).
- Endpoint de saúde (`GET /health`).
- Pipeline de ingestão de documentos (`POST /documentos/ingestao`) para `.txt`, `.md` e `.pdf`.
- Estratégia inicial de chunking com tamanho e sobreposição configuráveis.
- Indexação vetorial de trechos no PostgreSQL/pgvector.
- Consulta RAG (`POST /chat/perguntar`) com recuperação semântica e retorno de fontes.
- Testes automatizados cobrindo módulos principais (healthcheck, parser, chunking, embeddings, indexação e consulta RAG).

### 2.2 Situação de maturidade técnica
- Base funcional para um MVP técnico já existe.
- Arquitetura e decisões iniciais estão documentadas.
- Há sinais de evolução estrutural em andamento (ex.: coexistência de módulos com nomenclatura em inglês e português), sugerindo necessidade de consolidação arquitetural.

### 2.3 Lacunas imediatas
- Fortalecer estabilidade do ambiente de execução e testes (dependências e padronização de setup local/CI).
- Consolidar convenções de organização de código para reduzir duplicidade de caminhos equivalentes.
- Evoluir observabilidade e políticas operacionais (logs, métricas, falhas e reprocessamento).

---

## 3. Próximas fases

### Fase 1 — Consolidação do MVP técnico (curto prazo)
1. Padronizar estrutura interna (serviços, repositórios e domínio) em um único padrão de pastas e nomenclatura.
2. Garantir execução previsível de testes em ambiente limpo (local e CI).
3. Revisar contratos de API e mensagens de erro para consistência.
4. Formalizar documentação operacional mínima (execução, variáveis, troubleshooting).

### Fase 2 — Robustez de produção (curto/médio prazo)
1. Adicionar observabilidade (métricas de latência, taxa de erro, tempo de ingestão e qualidade de recuperação).
2. Implementar filas e reprocessamento para ingestão/indexação assíncrona.
3. Melhorar idempotência e versionamento de documentos/trechos.
4. Endurecer segurança básica (limites de upload, validações, auditoria de operações).

### Fase 3 — Qualidade de resposta e escala (médio prazo)
1. Evoluir chunking para estratégia orientada por estrutura e/ou tokens.
2. Introduzir reranqueamento e ajustes de recuperação semântica.
3. Adotar avaliação contínua de qualidade (conjunto de perguntas de referência).
4. Otimizar custo/performance de embeddings e consultas vetoriais.

### Fase 4 — Expansão de produto (médio/longo prazo)
1. Suporte ampliado a conectores/fontes de documentos.
2. Gestão de multi-tenant e controle de acesso por workspace.
3. Painel administrativo para ingestão, monitoramento e auditoria.
4. Estratégia de feedback humano para melhoria contínua das respostas.

---

## 4. Backlog técnico priorizado

### Prioridade P0 (crítico)
1. **Consolidar arquitetura de código**: eliminar duplicidades de módulos e definir estrutura canônica.
2. **Estabilizar pipeline de testes**: garantir instalação/validação de dependências em CI e ambiente local.
3. **Padronizar erros e contratos de API**: respostas previsíveis para falhas de upload, parse e consulta.
4. **Definir política de reindexação**: estratégia clara para atualização de documentos já ingeridos.

### Prioridade P1 (alta)
1. **Observabilidade mínima de produção**: logs estruturados, métricas e correlação por requisição.
2. **Ingestão assíncrona**: desacoplamento do tempo de upload e processamento pesado.
3. **Melhorias de chunking**: reduzir perda semântica e fragmentação excessiva.
4. **Testes de integração com banco real**: validar ponta a ponta com pgvector.

### Prioridade P2 (média)
1. **Avaliação de qualidade do RAG**: baseline de precisão/recall para perguntas representativas.
2. **Controle de custo dos modelos**: cache, batching e estratégias de fallback.
3. **Versionamento de documentos**: trilha de mudanças e rollback de conteúdo indexado.
4. **Hardening de segurança**: limites avançados, sanitização e políticas de retenção.

---

## 5. Melhorias futuras
- Busca híbrida (vetorial + lexical) para consultas ambíguas.
- Reranqueador dedicado para elevar precisão do contexto recuperado.
- Suporte a citação enriquecida (seção/página/bloco de origem).
- Cache semântico para perguntas recorrentes.
- Avaliação automática de alucinação e cobertura de fontes.
- Estratégias de personalização por domínio técnico (devops, backend, dados etc.).

---

## 6. Riscos conhecidos
1. **Risco de inconsistência arquitetural**: manutenção mais cara enquanto coexistirem padrões de organização diferentes.
2. **Risco de qualidade semântica**: chunking simplificado pode degradar contexto recuperado.
3. **Risco operacional**: ingestão síncrona pode gerar gargalo sob carga.
4. **Risco de confiabilidade**: ausência de métricas robustas dificulta diagnóstico rápido.
5. **Risco de custo**: crescimento de volume pode elevar custo de embeddings e armazenamento vetorial.
6. **Risco de segurança/compliance**: uploads sem governança completa podem expor dados sensíveis.

---

## 7. Critérios para considerar o MVP concluído
O MVP será considerado concluído quando **todos** os critérios abaixo forem atendidos:

1. **Fluxo ponta a ponta funcional**
   - Upload/ingestão de documentos suportados.
   - Geração e indexação de embeddings concluídas sem intervenção manual.
   - Consulta RAG retornando resposta e fontes rastreáveis.

2. **Confiabilidade mínima comprovada**
   - Testes automatizados de unidade e integração executando de forma reprodutível em CI.
   - Taxa de falha operacional dentro de limite definido pelo time.

3. **Operação básica pronta**
   - Logs estruturados para rastrear requisição, ingestão e consulta.
   - Procedimento documentado para reindexação e recuperação de falhas.

4. **Qualidade mínima de resposta validada**
   - Conjunto de perguntas de referência com desempenho aceitável definido previamente.
   - Respostas com transparência de fontes e limitação explícita quando necessário.

5. **Documentação essencial entregue**
   - Guia de execução.
   - Guia de configuração.
   - Documento arquitetural e roadmap técnico atualizados.
---

## 8. Critérios de avaliação RAG

A avaliação automatizada de RAG deve ser executada antes de mudanças grandes em recuperação, chunking, reranqueamento, prompt, geração de resposta ou contratos de fontes. O conjunto inicial fica em `tests/avaliacao_rag/` e usa documentos pequenos de referência para manter revisão rápida e reprodutível sem provedor externo real.

### 8.1 Conjunto inicial de referência
1. **Documentos pequenos**: manter arquivos Markdown curtos em `tests/avaliacao_rag/documentos_referencia/`, cada um cobrindo um comportamento específico do RAG.
2. **Casos esperados**: registrar perguntas em `tests/avaliacao_rag/casos_avaliacao.json` com resposta esperada resumida, trechos esperados, termos obrigatórios, fonte esperada, quantidade mínima de fontes úteis e nível mínimo de similaridade aceitável.
3. **Perguntas negativas**: incluir pelo menos um caso sem contexto suficiente para validar que o sistema não inventa resposta quando os documentos não cobrem a pergunta.

### 8.2 Métricas mínimas obrigatórias
1. **Presença da fonte correta**: a fonte esperada deve aparecer entre as fontes retornadas para perguntas respondíveis.
2. **Quantidade de fontes úteis**: cada pergunta deve atingir a quantidade mínima de fontes com evidência direta nos trechos esperados.
3. **Ausência de resposta sem contexto**: perguntas fora do escopo devem retornar zero fontes e mensagem explícita de contexto insuficiente.
4. **Estabilidade da resposta**: a mesma pergunta deve produzir resposta textual e ordenação de fontes iguais em execuções repetidas.
5. **Similaridade mínima**: a melhor fonte retornada deve atingir o valor `similaridade_minima` definido para o caso.
6. **Termos obrigatórios**: a resposta deve conter os termos críticos definidos no caso de avaliação.

### 8.3 Processo de revisão
1. Executar `python -m tests.avaliacao_rag.avaliar_rag` localmente antes de abrir mudanças grandes no RAG.
2. Executar `pytest tests/avaliacao_rag` para garantir que a avaliação continue integrada à suíte automatizada.
3. Quando uma mudança alterar comportamento esperado, atualizar primeiro os documentos/casos de avaliação e explicar o motivo na revisão.
4. Bloquear a revisão quando houver regressão em fonte correta, ausência de resposta sem contexto ou estabilidade, salvo decisão explícita documentada pelo time.

