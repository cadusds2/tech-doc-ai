# Arquitetura inicial

Este documento descreve a base arquitetural do projeto nesta fase de scaffold.

## Camadas

- **api/routes**: expõe endpoints HTTP.
- **api/schemas**: define contratos de entrada e saída.
- **core**: configurações compartilhadas.
- **services**: orquestração de regras de negócio (futuro).
- **repositories**: acesso a dados (futuro).
- **domain**: entidades e modelos de domínio (futuro).

## Direcionamento futuro

- Integrar PostgreSQL + pgvector para busca vetorial.
- Adicionar pipeline de ingestão e indexação de documentos.
- Implementar estratégia de recuperação (RAG) e respostas baseadas em contexto.
