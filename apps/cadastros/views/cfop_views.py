from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from apps.cadastros.models import CFOP
from django import forms


class CFOPForm(forms.ModelForm):
    class Meta:
        model = CFOP
        fields = ['cfop', 'nome', 'descricao']
        widgets = {
            'cfop': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 4}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class CFOPListView(ListView):
    model = CFOP
    template_name = 'cadastros/reservados/cfop_list.html'
    context_object_name = 'cfops'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            qs = qs.filter(Q(cfop__icontains=search) | Q(nome__icontains=search))
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('q', '')
        return ctx


class CFOPCreateView(CreateView):
    model = CFOP
    form_class = CFOPForm
    template_name = 'cadastros/reservados/cfop_form.html'
    success_url = reverse_lazy('cadastros:cfop_list')
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Novo CFOP'
        ctx['botao_texto'] = 'Salvar'
        return ctx
    
    def form_valid(self, form):
        messages.success(self.request, 'CFOP cadastrado!')
        return super().form_valid(form)


class CFOPUpdateView(UpdateView):
    model = CFOP
    form_class = CFOPForm
    template_name = 'cadastros/reservados/cfop_form.html'
    success_url = reverse_lazy('cadastros:cfop_list')
    pk_url_kwarg = 'cfop'
    
    def get_object(self):
        return CFOP.objects.get(cfop=self.kwargs['cfop'])
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Editar CFOP'
        ctx['botao_texto'] = 'Atualizar'
        return ctx
    
    def form_valid(self, form):
        messages.success(self.request, 'CFOP atualizado!')
        return super().form_valid(form)


class CFOPDeleteView(DeleteView):
    model = CFOP
    template_name = 'cadastros/reservados/cfop_confirm_delete.html'
    success_url = reverse_lazy('cadastros:cfop_list')
    pk_url_kwarg = 'cfop'
    
    def get_object(self):
        return CFOP.objects.get(cfop=self.kwargs['cfop'])
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'CFOP excluído!')
        return super().delete(request, *args, **kwargs)
