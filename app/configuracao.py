"""Compatibilidade temporária para imports legados de configuração.

Novos códigos devem importar `Configuracoes` e `obter_configuracoes` de
`app.core.config`.
"""

from app.core.config import Configuracoes, obter_configuracoes

__all__ = ["Configuracoes", "obter_configuracoes"]
