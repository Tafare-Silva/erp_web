from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Max
from apps.cadastros.models import DivisaoImpostosSaida, CFOP, CST, Estado
from django import forms


class DivisaoImpostosForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ✅ Carregar estados dinamicamente
        self.fields['uf'] = forms.ChoiceField(
            choices=[('', 'Selecione o Estado')] + [(e.uf, f'{e.uf} - {e.nome}') for e in Estado.objects.all().order_by('uf')],
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'}),
            label='UF'
        )
        
        # ✅ TORNAR CAMPOS OPCIONAIS NO FORM
        self.fields['divisao'].required = False  # Será gerado automaticamente
        self.fields['nome'].required = True  # Nome agora é obrigatório
        self.fields['descricao'].required = False  # Será preenchido com o nome
        self.fields['cfop_fora_estado'].required = False  # Será preenchido automaticamente
        self.fields['reducao_bc_icms'].required = False
        self.fields['aliquota_mva'].required = False
        self.fields['aliquota_icms_st'].required = False
    
    # CFOPs
    cfop_dentro_estado = forms.ModelChoiceField(
        queryset=CFOP.objects.all().order_by('cfop'),
        required=True,
        empty_label="Selecione o CFOP",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CFOP Dentro do Estado'
    )
    
    cfop_fora_estado = forms.ModelChoiceField(
        queryset=CFOP.objects.all().order_by('cfop'),
        required=False,  # ✅ OPCIONAL no form
        empty_label="Selecione o CFOP (opcional - usará o mesmo de dentro do estado)",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CFOP Fora do Estado'
    )
    
    cfop_fora_estado_contribuinte = forms.ModelChoiceField(
        queryset=CFOP.objects.all().order_by('cfop'),
        required=False,
        empty_label="Selecione o CFOP",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CFOP Fora do Estado (Contribuinte)'
    )
    
    cfop_fora_estado_nao_contribuinte = forms.ModelChoiceField(
        queryset=CFOP.objects.all().order_by('cfop'),
        required=False,
        empty_label="Selecione o CFOP",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CFOP Fora do Estado (Não Contribuinte)'
    )
    
    cfop_fora_pais = forms.ModelChoiceField(
        queryset=CFOP.objects.all().order_by('cfop'),
        required=False,
        empty_label="Selecione o CFOP",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CFOP Fora do País'
    )
    
    # CSTs
    cst_icms = forms.ModelChoiceField(
        queryset=CST.objects.filter(tipo_imposto='ICMS').order_by('cst'),
        required=True,
        empty_label="Selecione o CST ICMS",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CST ICMS'
    )
    
    cst_pis = forms.ModelChoiceField(
        queryset=CST.objects.filter(tipo_imposto='PIS').order_by('cst'),
        required=True,
        empty_label="Selecione o CST PIS",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CST PIS'
    )
    
    cst_cofins = forms.ModelChoiceField(
        queryset=CST.objects.filter(tipo_imposto='COFINS').order_by('cst'),
        required=True,
        empty_label="Selecione o CST COFINS",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CST COFINS'
    )
    
    cst_ipi = forms.ModelChoiceField(
        queryset=CST.objects.filter(tipo_imposto='IPI').order_by('cst'),
        required=False,
        empty_label="Selecione o CST IPI",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='CST IPI'
    )
    
    class Meta:
        model = DivisaoImpostosSaida
        fields = [
            'divisao', 'nome', 'descricao', 'uf',
            'cfop_dentro_estado', 
            'cfop_fora_estado',
            'cfop_fora_estado_contribuinte', 
            'cfop_fora_estado_nao_contribuinte',
            'cfop_fora_pais',
            'cst_icms', 'aliquota_icms', 'reducao_bc_icms', 'percentual_reducao_base_calculo_icms',
            'cst_pis', 'aliquota_pis',
            'cst_cofins', 'aliquota_cofins',
            'cst_ipi', 'aliquota_ipi',
            'aliquota_mva', 'aliquota_icms_st',
        ]
        widgets = {
            'divisao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Deixe vazio para gerar automaticamente',
                'maxlength': 5
            }),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Opcional - será preenchido com o nome se vazio'
            }),
            'aliquota_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reducao_bc_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0'}),
            'percentual_reducao_base_calculo_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'aliquota_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'aliquota_ipi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_mva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0'}),
            'aliquota_icms_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0'}),
        }


class DivisaoImpostosListView(ListView):
    model = DivisaoImpostosSaida
    template_name = 'cadastros/reservados/divisao_impostos_list.html'
    context_object_name = 'divisoes'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(descricao__icontains=search))
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('q', '')
        return ctx


class DivisaoImpostosCreateView(CreateView):
    model = DivisaoImpostosSaida
    form_class = DivisaoImpostosForm
    template_name = 'cadastros/reservados/divisao_impostos_form.html'
    success_url = reverse_lazy('cadastros:divisao_impostos_list')
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nova Divisão de Impostos'
        ctx['botao_texto'] = 'Salvar'
        return ctx
    
    def form_valid(self, form):
        print("✅ FORM VÁLIDO!")
        
        # ✅ NÃO SALVAR AINDA - commit=False
        instance = form.save(commit=False)
        
        # ✅ 1. GERAR CÓDIGO DA DIVISÃO SE VAZIO
        if not instance.divisao:
            # Pegar o maior código existente e somar 1
            ultimo = DivisaoImpostosSaida.objects.aggregate(Max('divisao'))['divisao__max']
            if ultimo:
                try:
                    proximo = int(ultimo) + 1
                    instance.divisao = str(proximo).zfill(5)  # Ex: 00001, 00002
                except ValueError:
                    # Se não for número, usar timestamp
                    from django.utils import timezone
                    instance.divisao = str(timezone.now().timestamp())[:5]
            else:
                instance.divisao = '00001'  # Primeiro registro
        
        # ✅ 2. PREENCHER DESCRIÇÃO SE VAZIA
        if not instance.descricao:
            instance.descricao = instance.nome or 'Sem descrição'
        
        # ✅ 3. PREENCHER CFOP FORA DO ESTADO SE VAZIO
        # USA cfop_fora_estado_id em vez de cfop_fora_estado
        if not instance.cfop_fora_estado_id:
            instance.cfop_fora_estado = instance.cfop_dentro_estado
        
        # ✅ 4. PREENCHER CAMPOS NUMÉRICOS SE VAZIOS
        if instance.reducao_bc_icms is None:
            instance.reducao_bc_icms = 0
        
        if instance.aliquota_mva is None:
            instance.aliquota_mva = 0
        
        if instance.aliquota_icms_st is None:
            instance.aliquota_icms_st = 0
        
        # ✅ AGORA SIM, SALVAR NO BANCO
        instance.save()
        
        print(f"✅ Divisão criada: {instance.divisao} - {instance.nome}")
        messages.success(self.request, f'Divisão de impostos "{instance.nome}" cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        print("❌ FORM INVÁLIDO!")
        print("Erros:", form.errors)
        messages.error(self.request, 'Erro ao salvar. Verifique os campos.')
        return super().form_invalid(form)


class DivisaoImpostosUpdateView(UpdateView):
    model = DivisaoImpostosSaida
    form_class = DivisaoImpostosForm
    template_name = 'cadastros/reservados/divisao_impostos_form.html'
    success_url = reverse_lazy('cadastros:divisao_impostos_list')
    pk_url_kwarg = 'divisao'
    
    def get_object(self):
        return DivisaoImpostosSaida.objects.get(divisao=self.kwargs['divisao'])
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Editar Divisão de Impostos'
        ctx['botao_texto'] = 'Atualizar'
        return ctx
    
    def form_valid(self, form):
        print("✅ FORM VÁLIDO!")
        
        instance = form.save(commit=False)
        
        # ✅ PREENCHER DESCRIÇÃO SE VAZIA
        if not instance.descricao:
            instance.descricao = instance.nome or 'Sem descrição'
        
        # ✅ PREENCHER CFOP FORA DO ESTADO SE VAZIO
        # USA cfop_fora_estado_id em vez de cfop_fora_estado
        if not instance.cfop_fora_estado_id:
            instance.cfop_fora_estado = instance.cfop_dentro_estado
        
        # ✅ PREENCHER CAMPOS NUMÉRICOS SE VAZIOS
        if instance.reducao_bc_icms is None:
            instance.reducao_bc_icms = 0
        
        if instance.aliquota_mva is None:
            instance.aliquota_mva = 0
        
        if instance.aliquota_icms_st is None:
            instance.aliquota_icms_st = 0
        
        instance.save()
        
        messages.success(self.request, f'Divisão de impostos "{instance.nome}" atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        print("❌ FORM INVÁLIDO!")
        print("Erros:", form.errors)
        messages.error(self.request, 'Erro ao atualizar. Verifique os campos.')
        return super().form_invalid(form)

class DivisaoImpostosDeleteView(DeleteView):
    model = DivisaoImpostosSaida
    template_name = 'cadastros/reservados/divisao_impostos_confirm_delete.html'
    success_url = reverse_lazy('cadastros:divisao_impostos_list')
    pk_url_kwarg = 'divisao'
    
    def get_object(self):
        return DivisaoImpostosSaida.objects.get(divisao=self.kwargs['divisao'])
    
    def delete(self, request, *args, **kwargs):
        divisao_nome = self.get_object().nome
        messages.success(self.request, f'Divisão de impostos "{divisao_nome}" excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

def api_divisao_impostos_detalhe(request, pk):
    """API: Retorna os detalhes de uma divisão de impostos para auto-preenchimento."""
    divisao = get_object_or_404(DivisaoImpostosSaida, divisao=pk)
    data = {
        'cst_icms': divisao.cst_icms.cst if divisao.cst_icms else '',
        'cst_pis': divisao.cst_pis.cst if divisao.cst_pis else '',
        'cst_cofins': divisao.cst_cofins.cst if divisao.cst_cofins else '',
        'cst_ipi': divisao.cst_ipi.cst if divisao.cst_ipi else '',
        'cfop_venda_estadual': divisao.cfop_dentro_estado.cfop if divisao.cfop_dentro_estado else '',
        'cfop_venda_interestadual': divisao.cfop_fora_estado.cfop if divisao.cfop_fora_estado else '',
        'aliquota_icms': float(divisao.aliquota_icms),
        'aliquota_pis': float(divisao.aliquota_pis),
        'aliquota_cofins': float(divisao.aliquota_cofins),
        'aliquota_ipi': float(divisao.aliquota_ipi),
        'reducao_bc_icms': float(divisao.reducao_bc_icms),
        'modalidade_bc_icms': divisao.modalidade_bc_icms,
        'aliquota_mva': float(divisao.aliquota_mva),
        'aliquota_icms_st': float(divisao.aliquota_icms_st),
        'reducao_bc_icms_st': float(divisao.reducao_bc_icms_st),
    }
    return JsonResponse(data)
