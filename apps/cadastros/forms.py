"""
Formulários customizados do módulo Cadastros.
"""

from django import forms
from django.forms import inlineformset_factory
from apps.cadastros.models import Divisao, AgenciaBancaria, ContaBancaria, Banco, CentroCusto, PlanoContas, TipoPagamento, Pessoa, PessoaFisica, Produto, ConversaoUnidade, TituloFinanceiro


class DivisaoForm(forms.ModelForm):
    """
    Formulário de Divisão com campo pai como select.
    """
    pai = forms.ModelChoiceField(
        queryset=Divisao.objects.all(),
        required=False,
        empty_label="Nenhuma (Raiz)",
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Divisão Pai',
        help_text='Selecione a divisão pai para criar uma hierarquia'
    )
    
    class Meta:
        model = Divisao
        fields = ['nome', 'pai', 'controla_lote', 'permitir_estoque_negativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'controla_lote': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'permitir_estoque_negativo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se estiver editando, remover a própria divisão da lista de pais
        if self.instance.pk:
            self.fields['pai'].queryset = Divisao.objects.exclude(nome=self.instance.nome)


class AgenciaBancariaForm(forms.Form):
    """
    Formulário de Agência Bancária.
    Usa Form ao invés de ModelForm por causa da chave composta.
    """
    banco = forms.IntegerField(
        label='Banco (código)',
        help_text='Digite o código do banco',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    agencia = forms.IntegerField(
        label='Agência',
        help_text='Número da agência',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    digito = forms.CharField(
        max_length=1,
        required=False,
        label='Dígito',
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'})
    )
    telefone = forms.CharField(
        max_length=20,
        required=False,
        label='Telefone',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nome_gerente = forms.CharField(
        max_length=255,
        required=False,
        label='Nome do Gerente',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    valor_juros = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        label='Valor Juros (%)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    valor_multa_por_atraso = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        label='Valor Multa (%)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    dias_para_protesto = forms.IntegerField(
        initial=0,
        label='Dias para Protesto',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    carteira = forms.CharField(
        max_length=255,
        required=False,
        label='Carteira',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    codigo_cedente = forms.CharField(
        max_length=255,
        required=False,
        label='Código Cedente',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    convenio = forms.CharField(
        max_length=255,
        required=False,
        label='Convênio',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    especie_documento = forms.CharField(
        max_length=255,
        required=False,
        label='Espécie Documento',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    layout_remessa = forms.ChoiceField(
        choices=[('', '--------'), ('c240', '240 posições'), ('c400', '400 posições')],
        required=False,
        label='Layout Remessa',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    codigo_transmissao = forms.CharField(
        max_length=255,
        required=False,
        label='Código Transmissão',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    modalidade = forms.CharField(
        max_length=255,
        required=False,
        label='Modalidade',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class ContaBancariaForm(forms.ModelForm):
    """
    Formulário de Conta Bancária com agência filtrada por banco.
    """
    banco = forms.IntegerField(
        label='Banco',
        help_text='Selecione o banco',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    agencia = forms.CharField(
        label='Agência',
        help_text='Selecione a agência',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = ContaBancaria
        fields = [
            'banco', 'agencia', 'conta', 'digito', 'tipo_conta_bancaria',
            'saldo_inicial', 'descricao_propria', 'inativo'
        ]
        widgets = {
            'conta': forms.NumberInput(attrs={'class': 'form-control'}),
            'digito': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'}),
            'tipo_conta_bancaria': forms.Select(attrs={'class': 'form-control'}),
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descricao_propria': forms.TextInput(attrs={'class': 'form-control'}),
            'inativo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    def clean_agencia(self):
        """Parse do valor composto banco-agencia."""
        agencia_value = self.cleaned_data.get('agencia')
        
        if agencia_value and '-' in agencia_value:
            # Valor é "banco-agencia", pegar só a agência
            parts = agencia_value.split('-')
            if len(parts) >= 2:
                return int(parts[1])  # Retorna apenas o número da agência
        
        # Se não tem hífen, tentar converter direto
        try:
            return int(agencia_value)
        except (ValueError, TypeError):
            raise forms.ValidationError('Selecione uma agência válida.')
    
    def clean(self):
        cleaned_data = super().clean()
        banco = cleaned_data.get('banco')
        agencia_num = cleaned_data.get('agencia')
        
        # Validar se a agência existe para o banco selecionado
        if banco and agencia_num:
            try:
                AgenciaBancaria.objects.get(banco=banco, agencia=agencia_num)
            except AgenciaBancaria.DoesNotExist:
                raise forms.ValidationError(
                    f'Agência {agencia_num} não encontrada para o banco {banco}. '
                    'Por favor, cadastre a agência primeiro.'
                )
        
        return cleaned_data


class CentroCustoForm(forms.ModelForm):
    """
    Formulário de Centro de Custo com campo pai como select.
    O código é gerado automaticamente.
    """
    pai = forms.ModelChoiceField(
        queryset=CentroCusto.objects.all(),
        required=False,
        empty_label="Nenhum (Raiz)",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Centro de Custo Pai',
        help_text='Selecione o centro de custo pai para criar uma hierarquia'
    )
    
    class Meta:
        model = CentroCusto
        fields = ['nome', 'pai']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se estiver editando, remover o próprio centro de custo da lista de pais
        if self.instance.pk:
            self.fields['pai'].queryset = CentroCusto.objects.exclude(chave=self.instance.chave)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Se não tem código, gerar automaticamente
        if not instance.codigo:
            if instance.pai:
                # Se tem pai, gerar código baseado no pai (ex: pai=1.1 -> filho=1.1.1)
                irmãos = CentroCusto.objects.filter(pai=instance.pai).exclude(chave=instance.chave)
                if irmãos.exists():
                    # Pegar o último irmão e incrementar
                    ultimo_codigo = irmãos.order_by('codigo').last().codigo
                    partes = ultimo_codigo.split('.')
                    partes[-1] = str(int(partes[-1]) + 1)
                    instance.codigo = '.'.join(partes)
                else:
                    # Primeiro filho
                    instance.codigo = f"{instance.pai.codigo}.1"
            else:
                # Centro de custo raiz, pegar próximo número
                raizes = CentroCusto.objects.filter(pai__isnull=True).exclude(chave=instance.chave)
                if raizes.exists():
                    ultimo = raizes.order_by('codigo').last()
                    try:
                        proximo = int(ultimo.codigo.split('.')[0]) + 1
                    except:
                        proximo = 1
                    instance.codigo = str(proximo)
                else:
                    instance.codigo = "1"
        
        if commit:
            instance.save()
        return instance


class PlanoContasForm(forms.ModelForm):
    """
    Formulário de Plano de Contas com geração automática de código.
    """
    pai = forms.ModelChoiceField(
        queryset=PlanoContas.objects.all(),
        required=False,
        empty_label="Nenhuma (Raiz)",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Conta Pai',
        help_text='Selecione a conta pai para criar uma hierarquia'
    )
    
    centro_custo_padrao = forms.ModelChoiceField(
        queryset=CentroCusto.objects.all(),
        required=False,
        empty_label="Nenhum",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Centro de Custo Padrão',
        help_text='Centro de custo padrão para lançamentos desta conta'
    )
    
    class Meta:
        model = PlanoContas
        fields = [
            'nome', 'pai', 'tipo_conta', 'observacoes',
            'fixo', 'dia_do_lancamento', 'apenas_previsao',
            'valor_padrao', 'obs_padrao',
            'centro_custo_padrao',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fixo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'dia_do_lancamento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'apenas_previsao': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'valor_padrao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'obs_padrao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se estiver editando, remover a própria conta da lista de pais
        if self.instance.pk:
            self.fields['pai'].queryset = PlanoContas.objects.exclude(chave=self.instance.chave)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Se não tem código, gerar automaticamente
        if not instance.codigo:
            if instance.pai:
                # Se tem pai, gerar código baseado no pai
                irmãos = PlanoContas.objects.filter(pai=instance.pai).exclude(chave=instance.chave)
                if irmãos.exists():
                    # Pegar o último irmão e incrementar
                    ultimo_codigo = irmãos.order_by('codigo').last().codigo
                    partes = ultimo_codigo.split('.')
                    partes[-1] = str(int(partes[-1]) + 1)
                    instance.codigo = '.'.join(partes)
                else:
                    # Primeiro filho
                    instance.codigo = f"{instance.pai.codigo}.1"
            else:
                # Conta raiz - usar 1.x, 2.x, 3.x baseado no tipo
                tipo_prefixo = {'R': '3', 'D': '4', 'A': '5'}
                prefixo = tipo_prefixo.get(instance.tipo_conta, '9')
                
                raizes = PlanoContas.objects.filter(
                    pai__isnull=True, 
                    tipo_conta=instance.tipo_conta
                ).exclude(chave=instance.chave)
                
                if raizes.exists():
                    codigos = [c.codigo for c in raizes if c.codigo.startswith(prefixo)]
                    if codigos:
                        ultimo = max(codigos)
                        try:
                            num = int(ultimo.split('.')[1]) + 1
                        except:
                            num = 1
                        instance.codigo = f"{prefixo}.{num}"
                    else:
                        instance.codigo = f"{prefixo}.1"
                else:
                    instance.codigo = f"{prefixo}.1"
        
        if commit:
            instance.save()
        return instance


class TipoPagamentoForm(forms.ModelForm):
    """
    Formulário de Tipo de Pagamento.
    """
    class Meta:
        model = TipoPagamento
        fields = [
            'tipo_pagamento', 'nome', 'prazo_padrao', 'qtd_parcelas_padrao',
            'situacoes_permitidas', 'tipos_titulos_permitidos', 'tipos_parcelamentos_permitidos',
            'chamar_tef', 'exigir_conta_bancaria', 'entrar_caixa_usuario',
            'controle_cheque', 'modalidade', 'taxa_administracao',
            'centavos_por_ultimo_nas_parcelas',
        ]
        widgets = {
            'tipo_pagamento': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'prazo_padrao': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'qtd_parcelas_padrao': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'situacoes_permitidas': forms.Select(attrs={'class': 'form-control'}),
            'tipos_titulos_permitidos': forms.Select(attrs={'class': 'form-control'}),
            'tipos_parcelamentos_permitidos': forms.Select(attrs={'class': 'form-control'}),
            'chamar_tef': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'exigir_conta_bancaria': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'entrar_caixa_usuario': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'controle_cheque': forms.Select(attrs={'class': 'form-control'}),
            'modalidade': forms.Select(attrs={'class': 'form-control'}),
            'taxa_administracao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'centavos_por_ultimo_nas_parcelas': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


# Estilos inline para garantir visibilidade independente do Tailwind
_S = "width:100%;padding:7px 10px;border:1.5px solid #9ca3af;border-radius:6px;font-size:13.5px;background:#fff;color:#111827;outline:none;box-sizing:border-box;min-height:36px;"
_S_SEL = _S + "cursor:pointer;"
_S_MONO = _S + "font-family:monospace;letter-spacing:0.5px;"
_S_NUM = _S + "text-align:right;"
_S_TA = _S + "min-height:90px;resize:vertical;"
_S_GREEN = _S + "border-color:#16a34a;"
_S_BLUE = _S + "border-color:#2563eb;"


class PessoaForm(forms.ModelForm):
    situacao_cadastro = forms.ChoiceField(
        choices=[
            ('', 'Selecione...'),
            ('NORMAL', 'Normal'),
            ('SUSPEITO', 'Suspeito'),
            ('INATIVO', 'Inativo'),
            ('EXCLUIDO', 'Excluído'),
        ],
        required=False,
        widget=forms.Select(attrs={'style': _S_SEL}),
    )

    class Meta:
        model = Pessoa
        fields = [
            'tipo_pessoa', 'nome', 'cpf_cnpj', 'rg_ie', 'isento_ie', 'indicador_ie',
            'nome_fantasia', 'email', 'email_nfe', 'telefone_fixo', 'celular_principal',
            'cliente', 'fornecedor', 'funcionario', 'vendedor',
            'transportador', 'motorista', 'inativo', 'observacoes',
            'ins_municipal', 'situacao_cadastro', 'consumidor_final',
            'limite_credito', 'suframa', 'vendedor_padrao', 'condicao_pagamento_padrao',
            'somar_frete_bc_icms_st', 'somar_ipi_bc_icms_st',
            'somar_oda_bc_icms_st', 'nao_destacar_impostos_nfse',
        ]
        widgets = {
            'tipo_pessoa': forms.Select(attrs={'style': _S_SEL}),
            'nome': forms.TextInput(attrs={'style': _S, 'placeholder': 'Nome completo ou Razão Social'}),
            'cpf_cnpj': forms.TextInput(attrs={'style': _S_MONO, 'placeholder': 'Opcional - 000.000.000-00 ou 00.000.000/0000-00'}),
            'rg_ie': forms.TextInput(attrs={'style': _S_MONO, 'placeholder': 'RG ou Inscrição Estadual'}),
            'isento_ie': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'indicador_ie': forms.Select(attrs={'style': _S_SEL}),
            'nome_fantasia': forms.TextInput(attrs={'style': _S, 'placeholder': 'Nome Fantasia ou Apelido'}),
            'email': forms.EmailInput(attrs={'style': _S, 'placeholder': 'contato@email.com'}),
            'email_nfe': forms.EmailInput(attrs={'style': _S, 'placeholder': 'nfe@email.com (para envio de XML/PDF)'}),
            'telefone_fixo': forms.TextInput(attrs={'style': _S, 'placeholder': '(00) 0000-0000'}),
            'celular_principal': forms.TextInput(attrs={'style': _S, 'placeholder': '(00) 90000-0000'}),
            'observacoes': forms.Textarea(attrs={'style': _S_TA, 'rows': 3, 'placeholder': 'Observações internas sobre o cliente...'}),
            'ins_municipal': forms.TextInput(attrs={'style': _S_MONO, 'placeholder': 'Inscrição Municipal'}),
            'consumidor_final': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'limite_credito': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'suframa': forms.TextInput(attrs={'style': _S_MONO, 'placeholder': 'Inscrição Suframa'}),
            'vendedor_padrao': forms.Select(attrs={'style': _S_SEL}),
            'condicao_pagamento_padrao': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: À vista, 30 dias, 30/60'}),
            'cliente': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'fornecedor': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'funcionario': forms.CheckboxInput(attrs={'class': 'form-checkbox', 'x-model': 'isFuncionario'}),
            'vendedor': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'transportador': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'motorista': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'inativo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'somar_frete_bc_icms_st': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'somar_ipi_bc_icms_st': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'somar_oda_bc_icms_st': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'nao_destacar_impostos_nfse': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_cpf_cnpj(self):
        cpf_cnpj = (self.cleaned_data.get('cpf_cnpj') or '').strip()
        return cpf_cnpj or None


from apps.cadastros.models import FuncionarioDetalhes, Empresa

class FuncionarioDetalhesForm(forms.ModelForm):
    class Meta:
        model = FuncionarioDetalhes
        fields = ['e_vendedor']
        widgets = {
            'e_vendedor': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class PessoaFisicaForm(forms.ModelForm):
    class Meta:
        model = PessoaFisica
        fields = ['data_nascimento', 'estado_civil', 'nome_pai', 'nome_mae',
                  'empresa_trabalho', 'profissao', 'renda_familiar']
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado_civil': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_pai': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_mae': forms.TextInput(attrs={'class': 'form-control'}),
            'empresa_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'profissao': forms.TextInput(attrs={'class': 'form-control'}),
            'renda_familiar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


from django.core.exceptions import ValidationError
from apps.cadastros.models import Produto, CodigoBarras, ConversaoUnidade, ProdutoVariacao, ProdutoCanal


class ProdutoForm(forms.ModelForm):
    estoque_inicial = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=4,
        min_value=0,
        initial=0,
        label='Estoque inicial',
        widget=forms.NumberInput(attrs={
            'style': _S_NUM,
            'step': '0.0001',
            'min': '0',
            'placeholder': '0,0000',
        }),
    )
    codigos_barras = forms.CharField(
        widget=forms.Textarea(attrs={
            'style': _S_TA,
            'placeholder': 'Um código EAN por linha\n7891234567890\n7897654321098',
        }),
        required=False,
        label='Códigos de Barras (EAN)',
    )

    class Meta:
        model = Produto
        fields = [
            'nome', 'descricao_reduzida', 'codigo', 'referencia',
            'marca', 'divisao', 'fabricante', 'unidade_venda', 'tipo_produto',
            'tipo_regulatorio', 'referencia_fabrica', 'inativo',
            'preco_venda', 'custo_referencia', 'pode_alterar_preco_venda',
            'fornecedor_principal',
            'controla_estoque', 'controla_lote', 'controla_serie',
            'estoque_minimo', 'ponto_reposicao', 'estoque_maximo',
            'permitir_estoque_negativo', 'local_padrao',
            'permite_venda', 'permite_compra',
            'descricao', 'descricao_comercial',
            'ncm', 'cest', 'cest_isento', 'origem',
            'cst_icms', 'cfop_venda_estadual', 'cfop_venda_interestadual',
            'aliquota_icms', 'reducao_bc_icms', 'modalidade_bc_icms',
            'aliquota_icms_st', 'aliquota_mva', 'reducao_bc_icms_st',
            'cst_pis', 'aliquota_pis',
            'cst_cofins', 'aliquota_cofins',
            'cst_ipi', 'aliquota_ipi',
            'divisao_impostos_saida',
            'aplicacao', 'tamanho', 'cor', 'genero', 'colecao', 'categoria',
            'peso_liquido', 'peso_bruto', 'comprimento', 'largura', 'altura',
            'cubagem', 'tipo_embalagem', 'multiplo_venda', 'qtd_embalagem',
            'prazo_separacao_dias',
            'visibilidade', 'produto_destaque', 'seo_titulo', 'seo_descricao',
            'palavras_chave', 'url_amigavel',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'style': _S, 'placeholder': 'Nome do produto', 'autofocus': True}),
            'descricao_reduzida': forms.TextInput(attrs={'style': _S, 'placeholder': 'Descrição para PDV, cupom e etiquetas'}),
            'codigo': forms.TextInput(attrs={'style': _S, 'placeholder': 'Código interno / SKU'}),
            'referencia': forms.TextInput(attrs={'style': _S, 'placeholder': 'Referência do catálogo'}),
            'marca': forms.Select(attrs={'style': _S_SEL}),
            'divisao': forms.Select(attrs={'style': _S_SEL}),
            'fabricante': forms.TextInput(attrs={'style': _S, 'placeholder': 'Fabricante'}),
            'unidade_venda': forms.Select(attrs={'style': _S_SEL}),
            'tipo_produto': forms.Select(attrs={'style': _S_SEL}),
            'tipo_regulatorio': forms.Select(attrs={'style': _S_SEL}),
            'referencia_fabrica': forms.TextInput(attrs={'style': _S, 'placeholder': 'Código do fabricante'}),
            'inativo': forms.CheckboxInput(attrs={'style': 'width:16px;height:16px;cursor:pointer;accent-color:#dc2626;'}),
            'preco_venda': forms.NumberInput(attrs={'style': _S_GREEN, 'step': '0.0001', 'min': '0', 'id': 'id_preco_venda', 'placeholder': '0,00'}),
            'custo_referencia': forms.NumberInput(attrs={'style': _S_BLUE, 'step': '0.0001', 'min': '0', 'id': 'id_custo_referencia', 'placeholder': '0,00'}),
            'pode_alterar_preco_venda': forms.CheckboxInput(attrs={'style': 'width:16px;height:16px;cursor:pointer;accent-color:#2563eb;'}),
            'fornecedor_principal': forms.Select(attrs={'style': _S_SEL}),
            'controla_estoque': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'controla_lote': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'controla_serie': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'estoque_minimo': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'placeholder': '0,00'}),
            'ponto_reposicao': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'placeholder': '0,00'}),
            'estoque_maximo': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'placeholder': '0,00'}),
            'permitir_estoque_negativo': forms.CheckboxInput(attrs={'style': 'width:16px;height:16px;cursor:pointer;accent-color:#2563eb;'}),
            'local_padrao': forms.Select(attrs={'style': _S_SEL}),
            'permite_venda': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'permite_compra': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'descricao': forms.Textarea(attrs={'style': _S_TA, 'rows': 3, 'placeholder': 'Descrição interna / técnica do produto...'}),
            'descricao_comercial': forms.Textarea(attrs={'style': _S_TA, 'rows': 3, 'placeholder': 'Descrição comercial para orçamentos, vendas e catálogo...'}),
            # Fiscal
            'ncm': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '8', 'placeholder': 'Só números (8 dígitos)', 'autocomplete': 'off'}),
            'cest': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '7', 'placeholder': 'Só números (7 dígitos)'}),
            'cest_isento': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'origem': forms.Select(attrs={'style': _S_SEL}),
            'cst_icms': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '3', 'placeholder': 'Ex: 00, 40, 102'}),
            'cfop_venda_estadual': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '4', 'placeholder': 'Ex: 5102'}),
            'cfop_venda_interestadual': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '4', 'placeholder': 'Ex: 6102'}),
            'aliquota_icms': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'max': '100'}),
            'reducao_bc_icms': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'max': '100'}),
            'modalidade_bc_icms': forms.Select(attrs={'style': _S_SEL}),
            'aliquota_icms_st': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'max': '100'}),
            'aliquota_mva': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0'}),
            'reducao_bc_icms_st': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'max': '100'}),
            'cst_pis': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '2', 'placeholder': 'Ex: 01, 07'}),
            'aliquota_pis': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'max': '100'}),
            'cst_cofins': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '2', 'placeholder': 'Ex: 01, 07'}),
            'aliquota_cofins': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'max': '100'}),
            'cst_ipi': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '2', 'placeholder': 'Ex: 50, 99'}),
            'aliquota_ipi': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0', 'max': '100'}),
            'divisao_impostos_saida': forms.Select(attrs={'style': _S_SEL}),
            # Características
            'aplicacao': forms.Textarea(attrs={'style': _S_TA, 'placeholder': 'Descrição técnica ou notas de aplicação'}),
            'tamanho': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: P, M, G, 38'}),
            'cor': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: Azul, Vermelho'}),
            'genero': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: Masculino, Feminino'}),
            'colecao': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: Verão 2025'}),
            'categoria': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: Calçados'}),
            # Logística
            'peso_liquido': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'placeholder': '0.0000'}),
            'peso_bruto': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'placeholder': '0.0000'}),
            'comprimento': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'placeholder': '0.0000', 'id': 'id_comprimento'}),
            'largura': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'placeholder': '0.0000', 'id': 'id_largura'}),
            'altura': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0', 'placeholder': '0.0000', 'id': 'id_altura'}),
            'cubagem': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.000001', 'min': '0', 'placeholder': '0.000000', 'id': 'id_cubagem'}),
            'tipo_embalagem': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: Caixa, Pacote'}),
            'multiplo_venda': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0.01', 'placeholder': '1.00'}),
            'qtd_embalagem': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0.01', 'placeholder': '1.00'}),
            'prazo_separacao_dias': forms.NumberInput(attrs={'style': _S_NUM, 'step': '1', 'min': '0', 'placeholder': '0'}),
            # Canais e Marketing
            'visibilidade': forms.Select(attrs={'style': _S_SEL}),
            'produto_destaque': forms.CheckboxInput(attrs={'style': 'width:16px;height:16px;cursor:pointer;accent-color:#059669;'}),
            'seo_titulo': forms.TextInput(attrs={'style': _S, 'placeholder': 'Título exibido em lojas online e buscadores'}),
            'seo_descricao': forms.Textarea(attrs={'style': _S_TA, 'placeholder': 'Descrição curta e atrativa do produto'}),
            'palavras_chave': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: tênis, corrida, esporte'}),
            'url_amigavel': forms.TextInput(attrs={'style': _S_MONO, 'placeholder': 'tenis-runner-2025'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modalidade_bc_icms'].widget.choices = [
            ('', '---------'),
            (0, '0 - MVA'),
            (1, '1 - Pauta'),
            (2, '2 - Preço Tabelado'),
            (3, '3 - Valor da Operação'),
        ]
        if self.instance.pk:
            codigos = CodigoBarras.objects.filter(produto=self.instance).values_list('codigo_barras', flat=True)
            self.initial['codigos_barras'] = '\n'.join(codigos)
        elif not self.is_bound:
            try:
                empresa = Empresa.objects.first()
            except Exception:
                empresa = None
            if empresa:
                if empresa.marca_padrao_xml_id:
                    self.fields['marca'].initial = empresa.marca_padrao_xml_id
                if empresa.divisao_padrao_xml_id:
                    self.fields['divisao'].initial = empresa.divisao_padrao_xml_id
                if empresa.unidade_venda_padrao_xml_id:
                    self.fields['unidade_venda'].initial = empresa.unidade_venda_padrao_xml_id
                if empresa.ncm_padrao_id:
                    self.fields['ncm'].initial = empresa.ncm_padrao_id
                if empresa.divisao_impostos_saida_padrao_id:
                    self.fields['divisao_impostos_saida'].initial = empresa.divisao_impostos_saida_padrao_id
                local_padrao = empresa.local_padrao or empresa.local_padrao_xml
                if local_padrao:
                    self.fields['local_padrao'].initial = local_padrao.pk

    def clean_ncm(self):
        ncm = self.cleaned_data.get('ncm')
        if ncm:
            if hasattr(ncm, 'ncm'):
                return ncm
            ncm_str = ''.join(filter(str.isdigit, str(ncm)))
            if len(ncm_str) != 8:
                raise ValidationError('NCM deve ter exatamente 8 dígitos.')
        return ncm

    def clean_cest(self):
        cest = self.cleaned_data.get('cest')
        cest_isento = self.cleaned_data.get('cest_isento')
        if cest_isento:
            return '0000000'
        if cest:
            cest = ''.join(filter(str.isdigit, str(cest)))
            if cest and len(cest) != 7:
                raise ValidationError('CEST deve ter exatamente 7 dígitos.')
        return cest

    def clean_cfop_venda_estadual(self):
        cfop = self.cleaned_data.get('cfop_venda_estadual', '').strip()
        if cfop:
            cfop = ''.join(filter(str.isdigit, cfop))
            if cfop and len(cfop) != 4:
                raise ValidationError('CFOP deve ter 4 dígitos.')
        return cfop

    def clean_cfop_venda_interestadual(self):
        cfop = self.cleaned_data.get('cfop_venda_interestadual', '').strip()
        if cfop:
            cfop = ''.join(filter(str.isdigit, cfop))
            if cfop and len(cfop) != 4:
                raise ValidationError('CFOP deve ter 4 dígitos.')
        return cfop

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            codigos_texto = self.cleaned_data.get('codigos_barras', '').strip()
            CodigoBarras.objects.filter(produto=instance).delete()
            if codigos_texto:
                for linha in codigos_texto.split('\n'):
                    codigo = linha.strip()
                    if codigo and len(codigo) <= 14 and codigo.isdigit():
                        CodigoBarras.objects.get_or_create(produto=instance, codigo_barras=codigo)
        return instance


class ConversaoUnidadeForm(forms.ModelForm):
    class Meta:
        model = ConversaoUnidade
        fields = ['unidade', 'fator_conversao', 'fator_preco', 'sem_gtin', 'codigo_barras', 'sku', 'permite_compra', 'permite_venda']
        widgets = {
            'unidade': forms.Select(attrs={'style': _S_SEL}),
            'fator_conversao': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0.0001', 'placeholder': '1,0000'}),
            'fator_preco': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0.0001', 'placeholder': '1,0000'}),
            'sem_gtin': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'codigo_barras': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '20', 'placeholder': 'EAN / DUN'}),
            'sku': forms.TextInput(attrs={'style': _S, 'placeholder': 'SKU'}),
            'permite_compra': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'permite_venda': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_codigo_barras(self):
        codigo = (self.cleaned_data.get('codigo_barras') or '').strip()
        sem_gtin = self.cleaned_data.get('sem_gtin', False)
        if sem_gtin:
            return None
        if codigo and (not codigo.isdigit() or len(codigo) > 20):
            raise forms.ValidationError('Código de barras deve conter apenas números.')
        return codigo or None


ConversaoUnidadeFormSet = inlineformset_factory(
    Produto,
    ConversaoUnidade,
    form=ConversaoUnidadeForm,
    fields=['unidade', 'fator_conversao', 'fator_preco', 'sem_gtin', 'codigo_barras', 'sku', 'permite_compra', 'permite_venda'],
    extra=1,
    can_delete=True,
)


class ProdutoVariacaoForm(forms.ModelForm):
    class Meta:
        model = ProdutoVariacao
        fields = ['descricao', 'codigo', 'referencia', 'sku', 'codigo_barras', 'ativo', 'preco_venda', 'estoque_atual']
        widgets = {
            'descricao': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: Tamanho G - Azul'}),
            'codigo': forms.TextInput(attrs={'style': _S, 'placeholder': 'Código'}),
            'referencia': forms.TextInput(attrs={'style': _S, 'placeholder': 'Referência'}),
            'sku': forms.TextInput(attrs={'style': _S, 'placeholder': 'SKU'}),
            'codigo_barras': forms.TextInput(attrs={'style': _S_MONO, 'placeholder': 'EAN / GTIN'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'preco_venda': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'placeholder': 'R$ 0,00'}),
            'estoque_atual': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'placeholder': '0'}),
        }


ProdutoVariacaoFormSet = inlineformset_factory(
    Produto,
    ProdutoVariacao,
    form=ProdutoVariacaoForm,
    fields=['descricao', 'codigo', 'referencia', 'sku', 'codigo_barras', 'ativo', 'preco_venda', 'estoque_atual'],
    extra=1,
    can_delete=True,
)


class ProdutoCanalForm(forms.ModelForm):
    class Meta:
        model = ProdutoCanal
        fields = ['canal', 'titulo', 'status', 'preco', 'unidade', 'sku_canal', 'url']
        widgets = {
            'canal': forms.Select(attrs={'style': _S_SEL}),
            'titulo': forms.TextInput(attrs={'style': _S, 'placeholder': 'Título do anúncio'}),
            'status': forms.Select(attrs={'style': _S_SEL}),
            'preco': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'placeholder': 'R$ 0,00'}),
            'unidade': forms.TextInput(attrs={'style': _S, 'placeholder': 'Padrão'}),
            'sku_canal': forms.TextInput(attrs={'style': _S, 'placeholder': 'SKU no canal'}),
            'url': forms.TextInput(attrs={'style': _S, 'placeholder': 'https://...'}),
        }


ProdutoCanalFormSet = inlineformset_factory(
    Produto,
    ProdutoCanal,
    form=ProdutoCanalForm,
    fields=['canal', 'titulo', 'status', 'preco', 'unidade', 'sku_canal', 'url'],
    extra=1,
    can_delete=True,
)


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            # Identificação
            'nome_fantasia', 'telefone_principal', 'logo_fundo',
            # Fiscal NF-e
            'crt_nfe', 'regime_tributacao_federal', 'cnae_fiscal',
            'uf_web_service_nfe', 'ambiente_destino',
            'serie_nfe', 'serie_nfce', 'caminho_arquivos_xml',
            'ncm_padrao',
            # Certificado Digital e CSC
            'certificado_digital', 'csc', 'csc_id',
            # Sede
            'cidade_sede',
            # Financeiro
            'plano_contas_receita_venda', 'centro_custo_venda',
            'plano_contas_receita_compra', 'centro_custo_compra',
            'juros_mes', 'multa_por_atraso',
            # Vendas
            'dias_vencimento_padrao_orcamento', 'valor_frete_padrao',
            'nao_alterar_valor_frete_padrao',
            # Responsável Técnico
            'resp_tec_cnpj', 'resp_tec_contato', 'resp_tec_email', 'resp_tec_fone',
            'resp_tec_csrt', 'resp_tec_csrt_id',
            # PDV
            'cliente_padrao', 'vendedor_padrao', 'consumidor_final',
            'bloquear_crediario_consumidor',
            # Estoque
            'configuracao_estoque_negativo', 'local_padrao',
            # Padrões de produto / XML Import
            'marca_padrao_xml', 'divisao_padrao_xml',
            'unidade_venda_padrao_xml', 'local_padrao_xml',
            'divisao_impostos_saida_padrao',
        ]
        widgets = {
            'nome_fantasia': forms.TextInput(attrs={'style': _S, 'placeholder': 'Nome Fantasia da Empresa'}),
            'telefone_principal': forms.TextInput(attrs={'style': _S}),
            'crt_nfe': forms.Select(attrs={'style': _S_SEL}),
            'regime_tributacao_federal': forms.Select(attrs={'style': _S_SEL}),
            'cnae_fiscal': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '7', 'placeholder': '0000000'}),
            'uf_web_service_nfe': forms.Select(attrs={'style': _S_SEL}),
            'ambiente_destino': forms.Select(attrs={'style': _S_SEL}),
            'serie_nfe': forms.NumberInput(attrs={'style': _S_NUM, 'min': '0'}),
            'serie_nfce': forms.NumberInput(attrs={'style': _S_NUM, 'min': '0'}),
            'caminho_arquivos_xml': forms.TextInput(attrs={'style': _S, 'placeholder': 'C:\\NFe\\xml'}),
            'ncm_padrao': forms.Select(attrs={'style': _S_SEL}),
            'certificado_digital': forms.Select(attrs={'style': _S_SEL}),
            'csc': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '36'}),
            'csc_id': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '6'}),
            'cidade_sede': forms.Select(attrs={'style': _S_SEL}),
            'plano_contas_receita_venda': forms.Select(attrs={'style': _S_SEL}),
            'centro_custo_venda': forms.Select(attrs={'style': _S_SEL}),
            'plano_contas_receita_compra': forms.Select(attrs={'style': _S_SEL}),
            'centro_custo_compra': forms.Select(attrs={'style': _S_SEL}),
            'juros_mes': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0'}),
            'multa_por_atraso': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.0001', 'min': '0'}),
            'dias_vencimento_padrao_orcamento': forms.NumberInput(attrs={'style': _S_NUM, 'min': '0'}),
            'valor_frete_padrao': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0'}),
            'nao_alterar_valor_frete_padrao': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'cliente_padrao': forms.Select(attrs={'style': _S_SEL}),
            'vendedor_padrao': forms.Select(attrs={'style': _S_SEL}),
            'consumidor_final': forms.Select(attrs={'style': _S_SEL}),
            'resp_tec_cnpj': forms.TextInput(attrs={'style': _S, 'placeholder': 'CNPJ do desenvolvedor do sistema'}),
            'resp_tec_contato': forms.TextInput(attrs={'style': _S, 'placeholder': 'Nome do contato'}),
            'resp_tec_email': forms.EmailInput(attrs={'style': _S, 'placeholder': 'Email do contato'}),
            'resp_tec_fone': forms.TextInput(attrs={'style': _S, 'placeholder': 'Telefone do contato'}),
            'resp_tec_csrt': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '32', 'placeholder': 'CSRT (32 caracteres hexadecimais)'}),
            'resp_tec_csrt_id': forms.TextInput(attrs={'style': _S_MONO, 'maxlength': '6', 'placeholder': 'ID do CSRT'}),
            'configuracao_estoque_negativo': forms.Select(attrs={'style': _S_SEL}),
            'local_padrao': forms.Select(attrs={'style': _S_SEL}),
            'marca_padrao_xml': forms.Select(attrs={'style': _S_SEL}),
            'divisao_padrao_xml': forms.Select(attrs={'style': _S_SEL}),
            'unidade_venda_padrao_xml': forms.Select(attrs={'style': _S_SEL}),
            'local_padrao_xml': forms.Select(attrs={'style': _S_SEL}),
            'divisao_impostos_saida_padrao': forms.Select(attrs={'style': _S_SEL}),
            'bloquear_crediario_consumidor': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['uf_web_service_nfe'].widget.choices = [
            ('', 'Selecione a UF'),
            ('AC', 'AC - Acre'), ('AL', 'AL - Alagoas'), ('AP', 'AP - Amapá'),
            ('AM', 'AM - Amazonas'), ('BA', 'BA - Bahia'), ('CE', 'CE - Ceará'),
            ('DF', 'DF - Distrito Federal'), ('ES', 'ES - Espírito Santo'),
            ('GO', 'GO - Goiás'), ('MA', 'MA - Maranhão'), ('MT', 'MT - Mato Grosso'),
            ('MS', 'MS - Mato Grosso do Sul'), ('MG', 'MG - Minas Gerais'),
            ('PA', 'PA - Pará'), ('PB', 'PB - Paraíba'), ('PR', 'PR - Paraná'),
            ('PE', 'PE - Pernambuco'), ('PI', 'PI - Piauí'), ('RJ', 'RJ - Rio de Janeiro'),
            ('RN', 'RN - Rio Grande do Norte'), ('RS', 'RS - Rio Grande do Sul'),
            ('RO', 'RO - Rondônia'), ('RR', 'RR - Roraima'), ('SC', 'SC - Santa Catarina'),
            ('SP', 'SP - São Paulo'), ('SE', 'SE - Sergipe'), ('TO', 'TO - Tocantins'),
        ]


class TituloFinanceiroForm(forms.ModelForm):
    """
    Formulário para lançamento individual e edição de Títulos a Pagar e a Receber.
    """
    class Meta:
        model = TituloFinanceiro
        fields = [
            'tipo', 'pessoa', 'numero_documento', 'data_emissao', 'data_vencimento',
            'valor_documento', 'tipo_pagamento', 'plano_contas', 'centro_custo',
            'conta_bancaria', 'historico', 'situacao'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'style': _S_SEL}),
            'pessoa': forms.Select(attrs={'style': _S_SEL}),
            'numero_documento': forms.TextInput(attrs={'style': _S, 'placeholder': 'Ex: NF-1234, BOL-987'}),
            'data_emissao': forms.DateInput(attrs={'style': _S, 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'style': _S, 'type': 'date'}),
            'valor_documento': forms.NumberInput(attrs={'style': _S_NUM, 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'tipo_pagamento': forms.Select(attrs={'style': _S_SEL}),
            'plano_contas': forms.Select(attrs={'style': _S_SEL}),
            'centro_custo': forms.Select(attrs={'style': _S_SEL}),
            'conta_bancaria': forms.Select(attrs={'style': _S_SEL}),
            'situacao': forms.Select(attrs={'style': _S_SEL}),
            'historico': forms.Textarea(attrs={'style': _S_TA, 'rows': 3, 'placeholder': 'Observações, contrato ou detalhes...'}),
        }

    def __init__(self, *args, tipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        t = tipo or (self.instance.tipo if self.instance.pk else None)
        if t:
            self.fields['tipo'].initial = t
            if t == 'P':
                self.fields['pessoa'].queryset = Pessoa.objects.filter(fornecedor=True).order_by('nome')
                self.fields['plano_contas'].queryset = PlanoContas.objects.filter(tipo_conta__in=['D', 'A']).order_by('codigo')
            elif t == 'R':
                self.fields['pessoa'].queryset = Pessoa.objects.filter(cliente=True).order_by('nome')
                self.fields['plano_contas'].queryset = PlanoContas.objects.filter(tipo_conta__in=['R', 'A']).order_by('codigo')
        self.fields['pessoa'].empty_label = "Selecione o parceiro..."
        self.fields['tipo_pagamento'].empty_label = "Selecione a forma de pagamento..."
        self.fields['plano_contas'].empty_label = "Selecione a categoria contábil..."
        self.fields['centro_custo'].empty_label = "Selecione o centro de custo..."
        self.fields['conta_bancaria'].empty_label = "Selecione a conta bancária..."