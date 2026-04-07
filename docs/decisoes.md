# Decisões técnicas iniciais

## 1) FastAPI como base
FastAPI foi escolhido por produtividade, tipagem e documentação automática.

## 2) Organização em camadas
A estrutura separa responsabilidades desde o início para facilitar evolução sem acoplamento excessivo.

## 3) Configuração centralizada
As variáveis de ambiente ficam em `app/core/config.py`, simplificando a troca de ambiente.

## 4) Preparação para PostgreSQL + pgvector
Dependências e variáveis de ambiente já estão presentes, mas sem conexão ativa obrigatória nesta etapa.

## 5) Estratégia inicial de chunking (tamanho com sobreposição)
Foi adotada uma estratégia simples de chunking por número de caracteres, com sobreposição configurável entre trechos.

### Limitações conhecidas
- O corte é cego ao contexto semântico (pode quebrar frases, listas e blocos de código).
- Não há variação por tipo de documento (PDF, Markdown e TXT usam a mesma regra).
- A estratégia considera caracteres, não tokens do modelo de embeddings.
- A normalização de espaços reduz ruídos, mas pode alterar formatação relevante.

### Melhorias futuras sugeridas
- Chunking orientado por estrutura (títulos, seções, parágrafos e blocos de código).
- Chunking por contagem de tokens para aderência ao modelo de embeddings.
- Estratégias híbridas com fallback (estrutura + tamanho).
- Metadados extras por trecho (página, seção, caminho hierárquico do documento).
- Pós-processamento para evitar trechos muito curtos no final.
