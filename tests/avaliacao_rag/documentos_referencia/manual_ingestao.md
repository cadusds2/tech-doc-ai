# Manual de ingestão

A ingestão aceita arquivos PDF e Markdown. Cada arquivo enviado é validado antes de entrar na fila de processamento.

Durante a ingestão, o texto é extraído, dividido em trechos e enriquecido com metadados de página, seção e caminho hierárquico.

Quando a extração falha, o documento deve permanecer com status de erro para permitir reprocessamento controlado.
