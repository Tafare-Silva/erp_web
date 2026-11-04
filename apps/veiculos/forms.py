from django import forms

from .models import Veiculo

INPUT_CLS = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = [
            'chassi', 'renavam', 'placa', 'marca', 'modelo',
            'cor', 'ano_fabricacao', 'ano_modelo', 'motor',
            'combustivel', 'carroceria', 'especie', 'kilometragem',
            'potencia', 'cilindradas', 'peso_liquido', 'peso_bruto',
            'codigo_modelo', 'capacidade',
            'valor_custo', 'preco_venda', 'tabela_fipe', 'status',
            'dono_recibo',
            'ncm', 'cfop', 'origem', 'cst_icms', 'csosn', 'aliquota_icms',
            'cst_pis', 'aliquota_pis', 'cst_cofins', 'aliquota_cofins',
            'local', 'vendedor', 'produto', 'observacoes',
        ]
        widgets = {
            'chassi': forms.TextInput(attrs={'class': INPUT_CLS, 'placeholder': '17 caracteres'}),
            'renavam': forms.TextInput(attrs={'class': INPUT_CLS, 'placeholder': '11 dígitos'}),
            'placa': forms.TextInput(attrs={'class': INPUT_CLS, 'placeholder': 'ABC-1D23'}),
            'marca': forms.Select(attrs={'class': INPUT_CLS}),
            'modelo': forms.Select(attrs={'class': INPUT_CLS}),
            'cor': forms.TextInput(attrs={'class': INPUT_CLS}),
            'ano_fabricacao': forms.NumberInput(attrs={'class': INPUT_CLS}),
            'ano_modelo': forms.NumberInput(attrs={'class': INPUT_CLS}),
            'motor': forms.TextInput(attrs={'class': INPUT_CLS}),
            'combustivel': forms.Select(attrs={'class': INPUT_CLS}),
            'carroceria': forms.Select(attrs={'class': INPUT_CLS}),
            'especie': forms.Select(attrs={'class': INPUT_CLS}),
            'kilometragem': forms.NumberInput(attrs={'class': INPUT_CLS}),
            'potencia': forms.TextInput(attrs={'class': INPUT_CLS, 'placeholder': 'CV'}),
            'cilindradas': forms.TextInput(attrs={'class': INPUT_CLS, 'placeholder': 'cm³'}),
            'peso_liquido': forms.TextInput(attrs={'class': INPUT_CLS}),
            'peso_bruto': forms.TextInput(attrs={'class': INPUT_CLS}),
            'codigo_modelo': forms.TextInput(attrs={'class': INPUT_CLS}),
            'capacidade': forms.TextInput(attrs={'class': INPUT_CLS}),
            'valor_custo': forms.NumberInput(attrs={'class': INPUT_CLS, 'step': '0.01'}),
            'preco_venda': forms.NumberInput(attrs={'class': INPUT_CLS, 'step': '0.01'}),
            'tabela_fipe': forms.NumberInput(attrs={'class': INPUT_CLS, 'step': '0.01'}),
            'status': forms.Select(attrs={'class': INPUT_CLS}),
            'dono_recibo': forms.Select(attrs={'class': INPUT_CLS}),
            'ncm': forms.TextInput(attrs={'class': INPUT_CLS}),
            'cfop': forms.TextInput(attrs={'class': INPUT_CLS}),
            'origem': forms.Select(attrs={'class': INPUT_CLS}, choices=[
                ('0', '0 - Nacional'), ('1', '1 - Estrangeira/Importação direta'),
                ('2', '2 - Estrangeira/Adquirida no mercado interno'), ('3', '3 - Nacional'),
                ('4', '4 - Nacional/Conteúdo importação >40%'), ('5', '5 - Nacional'),
                ('6', '6 - Estrangeira/Importação direta sem similar'), ('7', '7 - Estrangeira'),
                ('8', '8 - Nacional/Conteúdo importação >70%'),
            ]),
            'cst_icms': forms.TextInput(attrs={'class': INPUT_CLS}),
            'csosn': forms.TextInput(attrs={'class': INPUT_CLS}),
            'aliquota_icms': forms.NumberInput(attrs={'class': INPUT_CLS, 'step': '0.01'}),
            'cst_pis': forms.TextInput(attrs={'class': INPUT_CLS}),
            'aliquota_pis': forms.NumberInput(attrs={'class': INPUT_CLS, 'step': '0.0001'}),
            'cst_cofins': forms.TextInput(attrs={'class': INPUT_CLS}),
            'aliquota_cofins': forms.NumberInput(attrs={'class': INPUT_CLS, 'step': '0.0001'}),
            'local': forms.Select(attrs={'class': INPUT_CLS}),
            'vendedor': forms.Select(attrs={'class': INPUT_CLS}),
            'produto': forms.Select(attrs={'class': INPUT_CLS}),
            'observacoes': forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3}),
        }