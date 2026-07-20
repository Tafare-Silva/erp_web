"""
Models de Estoque - Reutiliza models do app cadastros
"""
#  Importar os models que já existem em cadastros
from apps.cadastros.models import (
    LocalEstoque,
    SaldoEstoque,
    MovimentacaoEstoque,
    ItemMovimentacaoEstoque,  
    TipoMovimentacao,
)

__all__ = [
    'LocalEstoque',
    'SaldoEstoque',
    'MovimentacaoEstoque',
    'ItemMovimentacaoEstoque', 
    'TipoMovimentacao',
]