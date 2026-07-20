from django import forms
from apps.cadastros.models import LocalEstoque


class LocalEstoqueForm(forms.ModelForm):
    class Meta:
        model = LocalEstoque
        fields = ['local', 'descricao', 'ativo']
        widgets = {
            'local': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Loja Principal, Depósito, Filial 01'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do local de estoque'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }