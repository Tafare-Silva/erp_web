from django.contrib import admin

from .models import MarcaVeiculo, ModeloVeiculo, Veiculo


@admin.register(MarcaVeiculo)
class MarcaVeiculoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(ModeloVeiculo)
class ModeloVeiculoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'marca', 'ano_modelo')
    list_filter = ('marca',)
    search_fields = ('nome',)


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('marca', 'modelo', 'placa', 'chassi', 'ano_modelo',
                    'status', 'preco_venda', 'tabela_fipe')
    list_filter = ('status', 'marca', 'combustivel', 'carroceria')
    search_fields = ('chassi', 'renavam', 'placa')
    readonly_fields = ('criado_em', 'atualizado_em')