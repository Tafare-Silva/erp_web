"""
Views para gerenciamento de códigos de barras de produtos.
"""
from django.views.generic import ListView, CreateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect
from apps.cadastros.models import CodigoBarras, Produto
from django import forms


class CodigoBarrasForm(forms.ModelForm):
    class Meta:
        model = CodigoBarras
        fields = ['codigo_barras']
        widgets = {
            'codigo_barras': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 13,
                'placeholder': 'Digite o código de barras (EAN-13)'
            })
        }


def codigo_barras_list(request, produto_id):
    """Lista códigos de barras usando ORM do Django."""
    produto = get_object_or_404(Produto, pk_chave=produto_id)
    
    # ✅ USANDO ORM - SEM SQL RAW
    codigos = CodigoBarras.objects.filter(produto=produto).order_by('codigo_barras')
    
    return render(request, 'cadastros/produtos/codigo_barras_list.html', {
        'produto': produto,
        'codigos': codigos
    })


def codigo_barras_create(request, produto_id):
    """Adiciona código de barras usando ORM."""
    produto = get_object_or_404(Produto, pk_chave=produto_id)
    
    if request.method == 'POST':
        form = CodigoBarrasForm(request.POST)
        if form.is_valid():
            try:
                # ✅ USANDO ORM - SEM SQL RAW
                codigo_obj = form.save(commit=False)
                codigo_obj.produto = produto
                codigo_obj.save()
                messages.success(request, 'Código de barras adicionado!')
                return redirect('cadastros:codigo_barras_list', produto_id=produto_id)
            except Exception as e:
                messages.error(request, f'Erro: {str(e)}')
    else:
        form = CodigoBarrasForm()
    
    return render(request, 'cadastros/produtos/codigo_barras_form.html', {
        'produto': produto,
        'form': form
    })


def codigo_barras_delete(request, produto_id, codigo):
    """Exclui código de barras usando ORM."""
    produto = get_object_or_404(Produto, pk_chave=produto_id)
    
    if request.method == 'POST':
        try:
            # ✅ USANDO ORM - SEM SQL RAW
            codigo_obj = CodigoBarras.objects.get(produto=produto, codigo_barras=codigo)
            codigo_obj.delete()
            messages.success(request, 'Código de barras excluído!')
        except CodigoBarras.DoesNotExist:
            messages.error(request, 'Código de barras não encontrado!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {str(e)}')
        
        return redirect('cadastros:codigo_barras_list', produto_id=produto_id)
    
    return render(request, 'cadastros/produtos/codigo_barras_confirm_delete.html', {
        'produto': produto,
        'codigo': codigo
    })