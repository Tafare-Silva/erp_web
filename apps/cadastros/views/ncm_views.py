from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from apps.cadastros.models import NCM
from django import forms


class NCMForm(forms.ModelForm):
    class Meta:
        model = NCM
        fields = ['ncm', 'nome']
        widgets = {
            'ncm': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 8}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }


class NCMListView(ListView):
    model = NCM
    template_name = 'cadastros/reservados/ncm_list.html'
    context_object_name = 'ncms'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            qs = qs.filter(Q(ncm__icontains=search) | Q(nome__icontains=search))
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('q', '')
        return ctx


class NCMCreateView(CreateView):
    model = NCM
    form_class = NCMForm
    template_name = 'cadastros/reservados/ncm_form.html'
    success_url = reverse_lazy('cadastros:ncm_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'NCM cadastrado!')
        return super().form_valid(form)


class NCMUpdateView(UpdateView):
    model = NCM
    form_class = NCMForm
    template_name = 'cadastros/reservados/ncm_form.html'
    success_url = reverse_lazy('cadastros:ncm_list')
    pk_url_kwarg = 'ncm'
    
    def get_object(self):
        return NCM.objects.get(ncm=self.kwargs['ncm'])
    
    def form_valid(self, form):
        messages.success(self.request, 'NCM atualizado!')
        return super().form_valid(form)


class NCMDeleteView(DeleteView):
    model = NCM
    template_name = 'cadastros/reservados/ncm_confirm_delete.html'
    success_url = reverse_lazy('cadastros:ncm_list')
    pk_url_kwarg = 'ncm'
    
    def get_object(self):
        return NCM.objects.get(ncm=self.kwargs['ncm'])
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'NCM excluído!')
        return super().delete(request, *args, **kwargs)
