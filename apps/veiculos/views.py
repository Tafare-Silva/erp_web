from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.urls import reverse

from .models import MarcaVeiculo, ModeloVeiculo, Veiculo
from .forms import VeiculoForm
from .services import FipeClient, ConsultaPlacaClient, normalizar_placa


@login_required
def dashboard(request):
    total = Veiculo.objects.count()
    por_status = (
        Veiculo.objects.values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )
    status_resumo = {item['status']: item['total'] for item in por_status}
    valor_estoque = Veiculo.objects.filter(
        status__in=['EM_ESTOQUE', 'RESERVADO']
    ).aggregate(total=Sum('preco_venda'))['total'] or 0

    context = {
        'total': total,
        'status_resumo': status_resumo,
        'valor_estoque': valor_estoque,
        'recentes': Veiculo.objects.select_related('marca', 'modelo')[:10],
    }
    return render(request, 'veiculos/dashboard.html', context)


@login_required
def veiculo_list(request):
    veiculos = Veiculo.objects.select_related('marca', 'modelo', 'local')
    filtro_status = request.GET.get('status', '')
    busca = request.GET.get('q', '')
    if filtro_status:
        veiculos = veiculos.filter(status=filtro_status)
    if busca:
        from django.db.models import Q
        veiculos = veiculos.filter(
            Q(chassi__icontains=busca) |
            Q(placa__icontains=busca) |
            Q(renavam__icontains=busca)
        )
    from apps.cadastros.models import Pessoa, TipoPagamento
    context = {
        'veiculos': veiculos,
        'filtro_status': filtro_status,
        'busca': busca,
        'status_choices': Veiculo.STATUS_CHOICES,
        'clientes': Pessoa.objects.filter(cliente=True)[:100],
        'tipos_pagamento': TipoPagamento.objects.filter(ativo=True),
        'veiculos_entrada': Veiculo.objects.filter(status__in=['EM_ESTOQUE', 'EM_AVALIACAO'])
                                  .select_related('marca', 'modelo'),
    }
    return render(request, 'veiculos/veiculo_list.html', context)


@login_required
def veiculo_create(request):
    if request.method == 'POST':
        form = VeiculoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Veículo cadastrado com sucesso.')
            return redirect('veiculos:veiculo_list')
    else:
        form = VeiculoForm()
    return render(request, 'veiculos/veiculo_form.html', {'form': form})


@login_required
def veiculo_update(request, pk):
    veiculo = get_object_or_404(Veiculo, pk=pk)
    if request.method == 'POST':
        form = VeiculoForm(request.POST, instance=veiculo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Veículo atualizado com sucesso.')
            return redirect('veiculos:veiculo_list')
    else:
        form = VeiculoForm(instance=veiculo)
    return render(request, 'veiculos/veiculo_form.html', {'form': form, 'veiculo': veiculo})


@login_required
def veiculo_delete(request, pk):
    veiculo = get_object_or_404(Veiculo, pk=pk)
    if request.method == 'POST':
        veiculo.delete()
        messages.success(request, 'Veículo excluído com sucesso.')
        return redirect('veiculos:veiculo_list')
    return render(request, 'veiculos/veiculo_confirm_delete.html', {'veiculo': veiculo})


@login_required
def api_marcas(request):
    return JsonResponse(list(MarcaVeiculo.objects.values('id', 'nome')), safe=False)


@login_required
def api_modelos_por_marca(request, marca_id):
    modelos = ModeloVeiculo.objects.filter(marca_id=marca_id).values('id', 'nome', 'ano_modelo')
    return JsonResponse(list(modelos), safe=False)


@login_required
def api_fipe(request):
    """Consulta o preço FIPE e preenche a tabela_fipe."""
    marca_nome = request.GET.get('marca', '').strip()
    modelo_nome = request.GET.get('modelo', '').strip()
    ano = request.GET.get('ano', '').strip()
    if not marca_nome or not modelo_nome:
        return JsonResponse({'erro': 'Informe marca e modelo antes de buscar o preço na FIPE.'}, status=400)

    import unicodedata

    def _norm(s):
        s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode('ascii')
        return s.upper().strip()

    try:
        client = FipeClient()
        marcas = client.listar_marcas()
        target = _norm(marca_nome)
        marca_sel = next(
            (m for m in marcas if target in _norm(m['nome'])),
            None
        )
        if not marca_sel:
            return JsonResponse({'erro': f'Marca "{marca_nome}" não encontrada na FIPE. '
                                         'Verifique se o nome da marca está correto (ex.: Volkswagen, VW, Fiat).'}, status=404)

        modelos_data = client.listar_modelos(marca_sel['codigo'])
        t_modelo = _norm(modelo_nome)
        modelo_sel = next(
            (m for m in modelos_data['modelos'] if t_modelo in _norm(m['nome'])),
            None
        )
        if not modelo_sel:
            return JsonResponse({'erro': f'Modelo "{modelo_nome}" não encontrado na FIPE para {marca_sel["nome"]}.'}, status=404)

        anos = client.listar_anos(marca_sel['codigo'], modelo_sel['codigo'])
        if ano:
            ano_sel = next(
                (a for a in anos if a['codigo'].endswith(ano.strip())),
                None
            )
        else:
            ano_sel = anos[0] if anos else None
        if not ano_sel:
            return JsonResponse({'erro': 'Ano não encontrado na FIPE.'}, status=404)

        preco = client.consultar_preco(
            marca_sel['codigo'], modelo_sel['codigo'], ano_sel['codigo']
        )
        return JsonResponse({
            'tabela_fipe': preco.get('Valor', '0').replace('R$', '').replace('.', '').replace(',', '.').strip(),
            'ano_modelo': preco.get('AnoModelo'),
            'combustivel': preco.get('Combustivel', ''),
            'referencia': preco.get('MesReferencia', ''),
        })
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao consultar FIPE: {str(e)}'}, status=500)


@login_required
def api_consulta_placa(request):
    """Consulta dados do veículo pela placa. Depende de provedor configurado."""
    placa = normalizar_placa(request.GET.get('placa', ''))
    if not placa:
        return JsonResponse({'erro': 'Informe a placa.'}, status=400)

    client = ConsultaPlacaClient()
    if not client.is_configured():
        return JsonResponse(
            {'erro': 'A consulta de dados pela placa ainda não está configurada. '
                     'Defina APIBRASIL_BEARER_TOKEN no .env (app.apibrasil.io > Minhas APIs). '
                     'Para obter o preço de referência, use a consulta FIPE selecionando marca e modelo.'},
            status=501
        )
    try:
        dados = client.consultar_por_placa(placa)
        if not dados:
            return JsonResponse({'erro': 'Nenhum dado retornado para esta placa.'}, status=404)

        marca_obj = None
        modelo_obj = None
        if dados.get('marca'):
            marca_obj, _ = MarcaVeiculo.objects.get_or_create(
                nome=dados['marca'].strip().title()
            )
            dados['marca_id'] = marca_obj.pk
            if dados.get('modelo'):
                ano_modelo = dados.get('ano_modelo') or None
                try:
                    modelo_obj, _ = ModeloVeiculo.objects.get_or_create(
                        marca=marca_obj,
                        nome=dados['modelo'].strip().title(),
                        ano_modelo=ano_modelo,
                    )
                    dados['modelo_id'] = modelo_obj.pk
                except Exception:
                    dados['modelo_id'] = None
        return JsonResponse(dados)
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao consultar placa: {str(e)}'}, status=500)


# ---------- Marca e Modelo ----------


@login_required
def marca_list(request):
    marcas = MarcaVeiculo.objects.prefetch_related('modelos')
    return render(request, 'veiculos/marca_list.html', {'marcas': marcas})


@login_required
def marca_importar(request):
    """Importa as marcas de veículos diretamente da tabela FIPE."""
    from .services import FipeClient
    try:
        client = FipeClient()
        marcas_api = client.listar_marcas()
        criadas = 0
        for m in marcas_api:
            _, created = MarcaVeiculo.objects.get_or_create(nome=m['nome'].strip())
            if created:
                criadas += 1
        if criadas:
            messages.success(request, f'{criadas} marcas importadas da FIPE.')
        else:
            messages.info(request, 'Marcas já cadastradas. Nenhuma nova importada.')
    except Exception as e:
        messages.error(request, f'Erro ao importar marcas: {str(e)}')
    return redirect('veiculos:marca_list')


@login_required
def marca_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if nome:
            MarcaVeiculo.objects.get_or_create(nome=nome)
            messages.success(request, f'Marca "{nome}" cadastrada.')
            return redirect('veiculos:marca_list')
        messages.error(request, 'Informe o nome da marca.')
    return render(request, 'veiculos/marca_form.html', {})


@login_required
def marca_update(request, pk):
    marca = get_object_or_404(MarcaVeiculo, pk=pk)
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if nome:
            marca.nome = nome
            marca.save()
            messages.success(request, 'Marca atualizada.')
            return redirect('veiculos:marca_list')
        messages.error(request, 'Informe o nome da marca.')
    return render(request, 'veiculos/marca_form.html', {'marca': marca})


@login_required
def marca_delete(request, pk):
    marca = get_object_or_404(MarcaVeiculo, pk=pk)
    if request.method == 'POST':
        marca.delete()
        messages.success(request, 'Marca excluída.')
        return redirect('veiculos:marca_list')
    return render(request, 'veiculos/marca_confirm_delete.html', {'marca': marca})


@login_required
def modelo_list(request, marca_id=None):
    modelos = ModeloVeiculo.objects.select_related('marca').order_by('marca__nome', 'nome')
    if marca_id:
        modelos = modelos.filter(marca_id=marca_id)
    return render(request, 'veiculos/modelo_list.html', {
        'modelos': modelos,
        'marca': marca_id and get_object_or_404(MarcaVeiculo, pk=marca_id),
    })


@login_required
def modelo_importar(request, marca_id):
    """Importa os modelos de uma marca diretamente da tabela FIPE."""
    from .services import FipeClient
    marca = get_object_or_404(MarcaVeiculo, pk=marca_id)
    try:
        client = FipeClient()
        marcas_api = client.listar_marcas()
        m_api = next((m for m in marcas_api if m['nome'].strip().upper() == marca.nome.upper()), None)
        if not m_api:
            messages.error(request, f'Marca "{marca.nome}" não encontrada na FIPE.')
            return redirect('veiculos:modelo_list_por_marca', marca_id=marca.pk)
        modelos = client.listar_modelos(m_api['codigo'])
        criados = 0
        for mod in modelos.get('modelos', []):
            _, created = ModeloVeiculo.objects.get_or_create(
                marca=marca, nome=mod['nome'].strip(), ano_modelo=None
            )
            if created:
                criados += 1
        messages.success(request, f'{criados} modelos importados da FIPE para {marca.nome}.')
    except Exception as e:
        messages.error(request, f'Erro ao importar modelos: {str(e)}')
    return redirect('veiculos:modelo_list_por_marca', marca_id=marca.pk)


@login_required
def modelo_create(request, marca_id=None):
    marcas = MarcaVeiculo.objects.all()
    if request.method == 'POST':
        marca = MarcaVeiculo.objects.filter(pk=request.POST.get('marca')).first()
        nome = request.POST.get('nome', '').strip()
        ano = request.POST.get('ano_modelo') or None
        if marca and nome:
            ModeloVeiculo.objects.create(marca=marca, nome=nome, ano_modelo=ano)
            messages.success(request, f'Modelo "{nome}" cadastrado.')
            return redirect('veiculos:modelo_list')
        messages.error(request, 'Selecione a marca e informe o modelo.')
    return render(request, 'veiculos/modelo_form.html', {'marcas': marcas, 'marca_id': marca_id})


@login_required
def modelo_update(request, pk):
    modelo = get_object_or_404(ModeloVeiculo, pk=pk)
    marcas = MarcaVeiculo.objects.all()
    if request.method == 'POST':
        marca = MarcaVeiculo.objects.filter(pk=request.POST.get('marca')).first()
        nome = request.POST.get('nome', '').strip()
        ano = request.POST.get('ano_modelo') or None
        if marca and nome:
            modelo.marca = marca
            modelo.nome = nome
            modelo.ano_modelo = ano
            modelo.save()
            messages.success(request, 'Modelo atualizado.')
            return redirect('veiculos:modelo_list')
        messages.error(request, 'Selecione a marca e informe o modelo.')
    return render(request, 'veiculos/modelo_form.html', {'marca': marca, 'marcas': marcas, 'modelo': modelo})


@login_required
def modelo_delete(request, pk):
    modelo = get_object_or_404(ModeloVeiculo, pk=pk)
    if request.method == 'POST':
        modelo.delete()
        messages.success(request, 'Modelo excluído.')
        return redirect('veiculos:modelo_list')
    return render(request, 'veiculos/modelo_confirm_delete.html', {'modelo': modelo})


# ---------- Venda / Nota de Compra ----------


@login_required
def api_pessoas(request):
    from apps.cadastros.models import Pessoa
    tipo = request.GET.get('tipo', 'cliente')
    qs = Pessoa.objects.all()
    if tipo == 'cliente':
        qs = qs.filter(cliente=True)
    elif tipo == 'fornecedor':
        qs = qs.filter(fornecedor=True)
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(nome__icontains=q) | qs.filter(cpf_cnpj__icontains=q)
    dados = [{'id': p.pk, 'nome': p.nome, 'cpf_cnpj': p.cpf_cnpj or ''} for p in qs[:20]]
    return JsonResponse(dados, safe=False)


@login_required
def api_tipos_pagamento(request):
    from apps.cadastros.models import TipoPagamento
    dados = [
        {'id': t.pk_tipo_pagamento, 'nome': t.tipo_pagamento,
         'forma_nfe': t.forma_pagamento_nfe}
        for t in TipoPagamento.objects.filter(ativo=True)
    ]
    return JsonResponse(dados, safe=False)


@login_required
def api_veiculos_entrada(request):
    """Lista veículos em estoque que podem ser dados como entrada (troca)."""
    dados = list(Veiculo.objects.filter(status__in=['EM_ESTOQUE', 'EM_AVALIACAO'])
                 .values('id', 'marca__nome', 'modelo__nome', 'placa', 'preco_venda'))
    resultado = [
        {'id': v['id'],
         'nome': f"{v['marca__nome']} {v['modelo__nome']} ({v['placa'] or 'sem placa'})",
         'valor': str(v['preco_venda'])}
        for v in dados
    ]
    return JsonResponse(resultado, safe=False)


@login_required
def veiculo_vender_api(request, pk):
    """Processa a venda do veículo via POST (JSON ou form)."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido.'}, status=405)
    from .services import vender_veiculo
    try:
        pagamentos = request.POST.getlist('pagamentos[]') or []
        veiculos_entrada = request.POST.getlist('veiculos_entrada[]') or []
        resultado = vender_veiculo(
            veiculo_id=pk,
            cliente_id=request.POST.get('cliente_id'),
            pagamentos=[
                {'tipo_pagamento_id': int(p.split(':')[0]),
                 'valor': p.split(':')[1]}
                for p in pagamentos if ':' in p
            ],
            veiculos_entrada=[int(v) for v in veiculos_entrada if v],
            vendedor_id=request.POST.get('vendedor_id') or None,
            local=request.POST.get('local') or None,
            usuario=request.user,
        )
        return JsonResponse({'sucesso': True, 'nfe': resultado['nfe']})
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)


@login_required
def veiculo_emitir_compra(request, pk):
    """Emite a NF-e de compra (entrada) do veículo."""
    if request.method != 'POST':
        return redirect('veiculos:veiculo_list')
    from .services import emitir_nota_compra
    try:
        resultado = emitir_nota_compra(
            veiculo_id=pk,
            fornecedor_id=request.POST.get('fornecedor_id') or None,
            usuario=request.user,
        )
        messages.success(request, f'Nota de compra emitida (NF-e #{resultado["nfe"]}).')
        return JsonResponse({'sucesso': True, 'nfe': resultado['nfe']})
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'erro': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('veiculos:veiculo_list')