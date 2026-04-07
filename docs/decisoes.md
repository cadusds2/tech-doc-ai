# Decisões técnicas iniciais

## 1) FastAPI como base
FastAPI foi escolhido por produtividade, tipagem e documentação automática.

## 2) Organização em camadas
A estrutura separa responsabilidades desde o início para facilitar evolução sem acoplamento excessivo.

## 3) Configuração centralizada
As variáveis de ambiente ficam em `app/core/config.py`, simplificando a troca de ambiente.

## 4) Preparação para PostgreSQL + pgvector
Dependências e variáveis de ambiente já estão presentes, mas sem conexão ativa obrigatória nesta etapa.
