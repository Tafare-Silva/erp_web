"""Views de Condicionais/Pré-Vendas."""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from apps.cadastros.models import (MovimentacaoEstoque, Pessoa, PreVenda, 
                                   ItemPreVenda, ItemMovimentacaoEstoque,
                                   LocalEstoque)
import json


@transaction.atomic
def criar_condicional(request):
    """Criar condicional/pré-venda."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    
    try:
        dados = json.loads(request.body)
        
        cliente_id = dados.get('cliente_id')
        vendedor_id = dados.get('vendedor_id')
        itens = dados.get('itens', [])
        local = LocalEstoque.objects.first()
        local_nome = dados.get('local', 'LOJA')
        
        if vendedor_id:
            try:
                vendedor_id = int(float(vendedor_id))
            except (ValueError, TypeError):
                vendedor_id = None
        
        if not itens:
            return JsonResponse({'erro': 'Nenhum item'}, status=400)
        
        if not cliente_id:
            consumidor = Pessoa.objects.filter(nome__iexact='CONSUMIDOR').first()
            if consumidor:
                cliente_id = consumidor.chave
        
        mov = MovimentacaoEstoque.objects.create(
            pessoa_id=cliente_id,
            tipo_movimento='PV',
            usuario=request.user.username if request.user.is_authenticated else 'SISTEMA'
        )
        
        PreVenda.objects.create(
            movimentacao=mov,
            vendedor_id=vendedor_id if vendedor_id else None,
            efetivada=False
        )
        
        for item in itens:
            desconto_valor = 0
            if item.get('tipoDesconto') == 'percent':
                subtotal = float(item['quantidade']) * float(item['preco'])
                desconto_valor = subtotal * (float(item.get('desconto', 0)) / 100)
            else:
                desconto_valor = float(item.get('desconto', 0))
            
            acrescimo_valor = 0
            if item.get('tipoAcrescimo') == 'percent':
                subtotal = float(item['quantidade']) * float(item['preco'])
                acrescimo_valor = subtotal * (float(item.get('acrescimo', 0)) / 100)
            else:
                acrescimo_valor = float(item.get('acrescimo', 0))
            
            item_mov = ItemMovimentacaoEstoque.objects.create(
                movimentacao=mov,
                produto_id=item['produto_id'],
                quantidade=-abs(float(item['quantidade'])),
                vr_unitario_bruto=float(item['preco']),
                vr_desconto_total=desconto_valor,
                vr_acrescimo_total=acrescimo_valor,
                local_id=local.pk_chave if local else None
            )
            
            ItemPreVenda.objects.create(
                item_movimentacao=item_mov,
                vendedor_id=vendedor_id if vendedor_id else None,
                quantidade_devolvida=0
            )
        
        condicional_id_limpo = str(mov.pk_chave).replace('.', '').replace(',', '')
        
        return JsonResponse({
            'sucesso': True,
            'condicional_id': condicional_id_limpo
        })
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)


def listar_condicionais(request):
    """Lista condicionais com filtros."""
    qs = MovimentacaoEstoque.objects.filter(
        tipo_movimento='PV'
    ).select_related('pessoa', 'pre_venda')
    
    data_ini = request.GET.get('data_ini')
    data_fim = request.GET.get('data_fim')
    numero = request.GET.get('numero')
    cliente = request.GET.get('cliente')
    situacao = request.GET.get('situacao', 'ABERTO')
    
    if data_ini:
        qs = qs.filter(data__gte=data_ini)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)
    if numero:
        qs = qs.filter(pk_chave=numero)
    if cliente:
        qs = qs.filter(pessoa__nome__icontains=cliente)
    
    if situacao == 'ABERTO':
        qs = qs.filter(pre_venda__efetivada=False)
    elif situacao == 'FECHADO':
        qs = qs.filter(pre_venda__efetivada=True)
    
    condicionais = qs.order_by('-pk_chave')[:100]
    
    return render(request, 'cadastros/condicionais/list.html', {
        'condicionais': condicionais,
        'filtros': {
            'data_ini': data_ini or '',
            'data_fim': data_fim or '',
            'numero': numero or '',
            'cliente': cliente or '',
            'situacao': situacao
        }
    })


def cupom_condicional(request, pk):
    """Cupom de condicional."""
    condicional = get_object_or_404(MovimentacaoEstoque, pk_chave=pk)
    itens = condicional.itens.select_related('produto').all()
    total = sum(abs(item.calcular_total()) for item in itens)
    
    return render(request, 'cadastros/condicionais/cupom.html', {
        'condicional': condicional,
        'itens': itens,
        'total': total
    })


def buscar_condicionais_api(request):
    """API: Buscar condicionais abertos."""
    termo = request.GET.get('q', '').strip()
    
    if not termo:
        return JsonResponse({'condicionais': []})
    
    qs = MovimentacaoEstoque.objects.filter(
        tipo_movimento='PV',
        pre_venda__efetivada=False
    ).select_related('pessoa')
    
    if termo.isdigit():
        qs = qs.filter(pk_chave=int(termo))
    else:
        qs = qs.filter(pessoa__nome__icontains=termo)
    
    condicionais = []
    for c in qs[:10]:
        condicionais.append({
            'id': c.pk_chave,
            'data': c.data.strftime('%d/%m/%Y'),
            'cliente': c.pessoa.nome if c.pessoa else 'Sem cliente',
            'total': f"{c.calcular_total():.2f}".replace('.', ',')
        })
    
    return JsonResponse({'condicionais': condicionais})


def tela_devolucao_multipla(request):
    """Tela de devolução combinando múltiplos condicionais."""
    ids_raw = request.GET.get('ids', '')
    id_list = []
    for x in ids_raw.split(','):
        try:
            id_list.append(int(float(x.strip())))
        except (ValueError, TypeError):
            pass

    if not id_list:
        from django.shortcuts import redirect
        return redirect('cadastros:condicional_list')

    condicionais = list(MovimentacaoEstoque.objects.filter(
        pk_chave__in=id_list
    ).select_related('pessoa', 'pre_venda'))

    itens_data = []
    total_original = 0
    vendedor_condicional = ''

    for cond in condicionais:
        itens = cond.itens.select_related('produto', 'item_pre_venda').all()
        for item in itens:
            try:
                dados_pv = item.item_pre_venda
                if dados_pv.quantidade_devolvida == -1:
                    continue
            except:
                pass

            vendedor_item = ''
            try:
                if item.item_pre_venda and item.item_pre_venda.vendedor_id:
                    vendedor_item = str(item.item_pre_venda.vendedor_id).replace('.', '').replace(',', '')
            except:
                pass

            itens_data.append({
                'item_id': item.id,
                'produto_id': item.produto.pk_chave,
                'nome': item.produto.nome,
                'qtd': abs(float(item.quantidade)),
                'preco': float(item.vr_unitario_bruto),
                'codigo_barras': '',
                'selecionado': False,
                'vendedor_id': vendedor_item,
                'condicional_id': cond.pk_chave
            })
            total_original += abs(item.calcular_total())

        if cond.pre_venda and cond.pre_venda.vendedor_id:
            vid = str(cond.pre_venda.vendedor_id).replace('.', '').replace(',', '')
            if vid:
                vendedor_condicional = vid

    from django.db.models import Q
    vendedores = Pessoa.objects.filter(
        Q(vendedor=True) | Q(funcionario=True, detalhes_funcionario__e_vendedor=True)
    ).distinct()[:50]

    combined_id = ','.join(str(c.pk_chave) for c in condicionais)
    cliente_nomes = ', '.join(c.pessoa.nome for c in condicionais if c.pessoa)

    return render(request, 'cadastros/condicionais/devolucao.html', {
        'condicional': condicionais[0],
        'condicional_id': combined_id,
        'vendedor_condicional': vendedor_condicional,
        'itens_json': json.dumps(itens_data),
        'vendedores': vendedores,
        'total_original': total_original,
        'is_multipla': True,
        'cliente_nomes': cliente_nomes
    })


def tela_devolucao(request, pk):
    """Tela de devolução - FILTRA devolvidos e vendidos."""
    condicional = get_object_or_404(MovimentacaoEstoque, pk_chave=pk)
    itens = condicional.itens.select_related('produto', 'item_pre_venda').all()
    
    itens_data = []
    for item in itens:
        try:
            dados_pv = item.item_pre_venda
            if dados_pv.quantidade_devolvida == -1:
                continue
        except:
            pass
        
        vendedor_item = ''
        try:
            if item.item_pre_venda and item.item_pre_venda.vendedor_id:
                vendedor_item = str(item.item_pre_venda.vendedor_id).replace('.', '').replace(',', '')
        except:
            pass
        
        itens_data.append({
            'item_id': item.id,
            'produto_id': item.produto.pk_chave,
            'nome': item.produto.nome,
            'qtd': abs(float(item.quantidade)),
            'preco': float(item.vr_unitario_bruto),
            'codigo_barras': '',
            'selecionado': False,
            'vendedor_id': vendedor_item
        })
    
    from django.db.models import Q
    vendedores = Pessoa.objects.filter(
        Q(vendedor=True) | Q(funcionario=True, detalhes_funcionario__e_vendedor=True)
    ).distinct()[:50]
    
    vendedor_condicional = ''
    if condicional.pre_venda and condicional.pre_venda.vendedor_id:
        vendedor_condicional = str(condicional.pre_venda.vendedor_id).replace('.', '').replace(',', '')
    
    total_original = sum(abs(item.calcular_total()) for item in itens)
    condicional_id_limpo = str(condicional.pk_chave).replace('.', '').replace(',', '')
    
    return render(request, 'cadastros/condicionais/devolucao.html', {
        'condicional': condicional,
        'condicional_id': condicional_id_limpo,
        'vendedor_condicional': vendedor_condicional,
        'itens_json': json.dumps(itens_data),
        'vendedores': vendedores,
        'total_original': total_original
    })


def _extrair_condicional_ids(selecionados, nao_selecionados, devolvidos):
    """Extrai IDs únicos de condicionais a partir dos itens."""
    ids = set()
    for item in selecionados + nao_selecionados + devolvidos:
        cid = item.get('condicional_id')
        if cid:
            try:
                ids.add(int(float(str(cid).replace(',', ''))))
            except (ValueError, TypeError):
                pass
    return list(ids)


def _processar_devolucao_items(cond_ids_list, selecionados, devolvidos):
    """Executa as queries de devolução usando Django ORM."""
    ItemPreVenda.objects.filter(
        item_movimentacao__movimentacao_id__in=cond_ids_list
    ).update(quantidade_devolvida=0)

    for item_dev in devolvidos:
        ItemPreVenda.objects.filter(
            item_movimentacao_id=item_dev['item_id']
        ).update(
            quantidade_devolvida=item_dev['qtd'],
            vendedor_id=item_dev.get('vendedor_id') or None
        )

    for item_sel in selecionados:
        ItemPreVenda.objects.filter(
            item_movimentacao_id=item_sel['item_id']
        ).update(
            quantidade_devolvida=-1,
            vendedor_id=item_sel.get('vendedor_id') or None
        )

    for cid in cond_ids_list:
        remaining = ItemMovimentacaoEstoque.objects.filter(movimentacao_id=cid).count()
        if remaining == 0:
            PreVenda.objects.filter(movimentacao_id=cid).update(efetivada=True)


@transaction.atomic
def processar_devolucao_multiplo(request):
    """Processar devolução de múltiplos condicionais (sem pk na URL)."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    try:
        dados = json.loads(request.body)
        selecionados = dados.get('selecionados', [])
        nao_selecionados = dados.get('nao_selecionados', [])
        devolvidos = dados.get('devolvidos', [])

        cond_ids_list = _extrair_condicional_ids(selecionados, nao_selecionados, devolvidos)
        if not cond_ids_list:
            return JsonResponse({'erro': 'Nenhum condicional identificado'}, status=400)

        _processar_devolucao_items(cond_ids_list, selecionados, devolvidos)

        cond_ids_limpos = ','.join(str(c) for c in cond_ids_list)
        return JsonResponse({'sucesso': True, 'condicional_id': cond_ids_limpos})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)


@transaction.atomic
def processar_devolucao(request, pk):
    """Processar devolução de UM condicional."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)

    try:
        cond = get_object_or_404(MovimentacaoEstoque, pk_chave=pk)

        dados = json.loads(request.body)
        selecionados = dados.get('selecionados', [])
        nao_selecionados = dados.get('nao_selecionados', [])
        devolvidos = dados.get('devolvidos', [])

        cond_ids_list = _extrair_condicional_ids(selecionados, nao_selecionados, devolvidos)
        if not cond_ids_list:
            cond_ids_list = [cond.pk_chave]

        _processar_devolucao_items(cond_ids_list, selecionados, devolvidos)

        cond_ids_limpos = ','.join(str(c) for c in cond_ids_list)
        return JsonResponse({'sucesso': True, 'condicional_id': cond_ids_limpos})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)


def dados_pdv(request, pk):
    """API: Retorna dados do condicional para PDV e REMOVE itens selecionados."""
    try:
        condicional = get_object_or_404(MovimentacaoEstoque, pk_chave=pk)
        
        itens_query = condicional.itens.select_related('produto', 'item_pre_venda').all()
        itens_data = []
        itens_para_remover = []
        
        for item in itens_query:
            try:
                dados_pv = item.item_pre_venda
                if dados_pv.quantidade_devolvida == -1:
                    itens_data.append({
                        'produto_id': item.produto.pk_chave,
                        'nome': item.produto.nome,
                        'qtd': abs(float(item.quantidade)),
                        'preco': float(item.vr_unitario_bruto)
                    })
                    itens_para_remover.append(item.id)
            except Exception as e:
                print(f"Erro no item {item.id}: {e}")
        
        if itens_para_remover:
            ItemMovimentacaoEstoque.objects.filter(id__in=itens_para_remover).delete()
        
        itens_restantes = condicional.itens.count()
        if itens_restantes == 0:
            condicional.pre_venda.efetivada = True
            condicional.pre_venda.save()
        
        cliente_data = None
        if condicional.pessoa:
            cliente_data = {
                'chave': condicional.pessoa.chave,
                'nome': condicional.pessoa.nome,
                'cpf_cnpj': condicional.pessoa.cpf_cnpj or '',
                'telefone': condicional.pessoa.telefone_fixo or condicional.pessoa.celular_principal or ''
            }
        
        vendedor_id = None
        if condicional.pre_venda and condicional.pre_venda.vendedor_id:
            vendedor_id = str(condicional.pre_venda.vendedor_id).replace('.', '').replace(',', '')
        
        return JsonResponse({
            'sucesso': True,
            'cliente': cliente_data,
            'vendedor_id': vendedor_id,
            'itens': itens_data
        })
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)


def dados_pdv_multiplo(request):
    """API: Retorna dados de múltiplos condicionais para PDV."""
    try:
        ids_raw = request.GET.get('ids', '')
        id_list = []
        for x in ids_raw.split(','):
            try:
                id_list.append(int(float(x.strip())))
            except (ValueError, TypeError):
                pass

        if not id_list:
            return JsonResponse({'erro': 'Nenhum ID fornecido'}, status=400)

        condicionais = MovimentacaoEstoque.objects.filter(pk_chave__in=id_list)

        all_itens = []
        all_itens_para_remover = []
        cliente_data = None
        vendedor_id = None

        for cond in condicionais:
            itens_query = cond.itens.select_related('produto', 'item_pre_venda').all()

            for item in itens_query:
                try:
                    dados_pv = item.item_pre_venda
                    if dados_pv.quantidade_devolvida == -1:
                        all_itens.append({
                            'produto_id': item.produto.pk_chave,
                            'nome': item.produto.nome,
                            'qtd': abs(float(item.quantidade)),
                            'preco': float(item.vr_unitario_bruto)
                        })
                        all_itens_para_remover.append(item.id)
                except Exception as e:
                    print(f"Erro no item {item.id}: {e}")

            if cond.pessoa and not cliente_data:
                cliente_data = {
                    'chave': cond.pessoa.chave,
                    'nome': cond.pessoa.nome,
                    'cpf_cnpj': cond.pessoa.cpf_cnpj or '',
                    'telefone': cond.pessoa.telefone_fixo or cond.pessoa.celular_principal or ''
                }

            if cond.pre_venda and cond.pre_venda.vendedor_id and not vendedor_id:
                vendedor_id = str(cond.pre_venda.vendedor_id).replace('.', '').replace(',', '')

        if all_itens_para_remover:
            ItemMovimentacaoEstoque.objects.filter(id__in=all_itens_para_remover).delete()

        for cond in condicionais:
            itens_restantes = cond.itens.count()
            if itens_restantes == 0 and cond.pre_venda:
                cond.pre_venda.efetivada = True
                cond.pre_venda.save()

        return JsonResponse({
            'sucesso': True,
            'cliente': cliente_data,
            'vendedor_id': vendedor_id,
            'itens': all_itens
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)
