"""
Views para Configuração da Empresa.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from apps.cadastros.models import Empresa
from apps.cadastros.forms import EmpresaForm


@login_required
def empresa_config(request):
    empresa = Empresa.objects.first()
    if not empresa:
        from apps.cadastros.models import Pessoa
        pessoa = Pessoa.objects.first()
        if not pessoa:
            messages.error(request, 'Nenhuma pessoa cadastrada. Crie uma pessoa primeiro.')
            return redirect('cadastros:pessoa_list')
        empresa = Empresa.objects.create(pessoa=pessoa)

    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações da empresa salvas com sucesso!')
            return redirect('cadastros:empresa_config')
        else:
            messages.error(request, 'Erro ao salvar. Verifique os campos.')
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, 'cadastros/empresa/form.html', {
        'form': form,
        'empresa': empresa,
        'titulo': 'Configuração da Empresa',
        'botao_texto': 'Salvar Configurações',
    })
