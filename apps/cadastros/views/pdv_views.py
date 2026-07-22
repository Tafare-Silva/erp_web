"""Views do PDV Rápido (Frente de Caixa)."""
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from apps.cadastros.models import (Produto, Pessoa, MovimentacaoEstoque, 
                                   LocalEstoque, TipoMovimentacao)
logger = logging.getLogger(__name__)


@login_required
def pdv_index(request):
    """Tela principal do PDV."""
    from apps.cadastros.models import TipoPagamento, Pessoa, FuncionarioDetalhes, Empresa
    from django.db.models import Q
    
    try:
        local_padrao = LocalEstoque.objects.first()
    except:
        local_padrao = None
    
    try:
        empresa = Empresa.objects.first()
        cliente_padrao = empresa.cliente_padrao
        vendedor_padrao = empresa.vendedor_padrao
    except:
        empresa = None
        cliente_padrao = None
        vendedor_padrao = None

    cliente_padrao_json = None
    vendedor_padrao_json = None
    if cliente_padrao:
        tel = cliente_padrao.celular_principal or cliente_padrao.telefone_fixo or ''
        try:
            end_princ = cliente_padrao.endereco_principal_rel
            cidade_nome = str(end_princ.endereco.cidade) if end_princ and end_princ.endereco and end_princ.endereco.cidade else ''
        except:
            cidade_nome = ''
        cliente_padrao_json = {
            'chave': cliente_padrao.chave,
            'nome': cliente_padrao.nome,
            'cpf_cnpj': cliente_padrao.cpf_cnpj or '',
            'telefone': tel,
            'cidade': cidade_nome
        }
    if vendedor_padrao:
        vendedor_padrao_json = {
            'chave': vendedor_padrao.chave,
            'nome': vendedor_padrao.nome
        }

    vendedores = list(Pessoa.objects.filter(
        Q(vendedor=True) | Q(funcionario=True, detalhes_funcionario__e_vendedor=True)
    ).distinct()[:50].values('chave', 'nome'))
    
    tipos_pagamento = TipoPagamento.objects.filter(ativo=True)
    
    tipos_pagamento_com_icone = []
    icon_map = {
        'DINHEIRO': 'fas fa-money-bill-wave text-green-600',
        'DÉBITO': 'fas fa-credit-card text-blue-600',
        'CRÉDITO': 'fas fa-credit-card text-purple-600',
        'PIX': 'fas fa-qrcode text-teal-600',
        'BOLETO': 'fas fa-barcode text-orange-600',
        'CREDIARIO': 'fas fa-handshake text-yellow-600',
        'CREDIÁRIO': 'fas fa-handshake text-yellow-600',
        'HAVER': 'fas fa-user-tag text-gray-600',
    }
    
    for tp in tipos_pagamento:
        nome_upper = tp.tipo_pagamento.upper()
        icone = 'fas fa-money-check-alt text-gray-500'
        for key in icon_map:
            if key in nome_upper:
                icone = icon_map[key]
                break
        
        tipos_pagamento_com_icone.append({
            'id': tp.pk_tipo_pagamento,
            'nome': tp.tipo_pagamento,
            'icone': icone,
            'prazo': tp.situacoes_permitidas == 'AP' or 'CREDI' in nome_upper
        })
    
    return render(request, 'cadastros/pdv/index.html', {
        'local_padrao': local_padrao,
        'local_padrao_json': json.dumps(local_padrao.local) if local_padrao else 'null',
        'vendedores_json': json.dumps(vendedores),
        'tipos_pagamento_json': json.dumps(tipos_pagamento_com_icone),
        'cliente_padrao_json': json.dumps(cliente_padrao_json) if cliente_padrao_json else 'null',
        'vendedor_padrao_json': json.dumps(vendedor_padrao_json) if vendedor_padrao_json else 'null',
    })


def pdv_buscar_produto(request):
    """API: Buscar produto por código, código de barras ou nome."""
    termo = request.GET.get('q', '').strip()
    
    if not termo:
        return JsonResponse({'produto': None, 'erro': 'Termo vazio'})
    
    # Tentar por código (exato)
    try:
        if termo.isdigit():
            produto = Produto.objects.get(pk_chave=int(termo))
            return JsonResponse({
                'produto': {
                    'id': produto.pk_chave,
                    'nome': produto.nome,
                    'preco': float(produto.preco_venda or 0)
                }
            })
    except:
        pass
    
    # Tentar por código de barras (exato)
    from apps.cadastros.models import CodigoBarras
    codigo = CodigoBarras.objects.filter(codigo_barras=termo).select_related('produto').first()
    if codigo:
        produto = codigo.produto
        return JsonResponse({
            'produto': {
                'id': produto.pk_chave,
                'nome': produto.nome,
                'preco': float(produto.preco_venda or 0)
            }
        })
    
    # Buscar por nome (pode retornar múltiplos)
    produtos = Produto.objects.filter(nome__icontains=termo)[:10]
    
    if produtos.count() == 1:
        # Apenas 1 encontrado, retorna direto
        p = produtos.first()
        return JsonResponse({
            'produto': {
                'id': p.pk_chave,
                'nome': p.nome,
                'preco': float(p.preco_venda or 0)
            }
        })
    elif produtos.count() > 1:
        # Múltiplos encontrados, retorna lista
        lista = [{
            'id': p.pk_chave,
            'nome': p.nome,
            'preco': float(p.preco_venda or 0)
        } for p in produtos]
        return JsonResponse({'produtos': lista})
    
    return JsonResponse({'produto': None, 'erro': 'Produto não encontrado'})


@transaction.atomic
def pdv_finalizar(request):
    """Finalizar venda."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    
    try:
        import json
        dados = json.loads(request.body)
        
        cliente_id = dados.get('cliente_id')
        vendedor_id = dados.get('vendedor_id')
        itens = dados.get('itens', [])
        local = dados.get('local', None)
        # Validar/fallback do LocalEstoque
        if local:
            from apps.cadastros.models import LocalEstoque
            if not LocalEstoque.objects.filter(local=local).exists():
                primeiro = LocalEstoque.objects.first()
                local = primeiro.local if primeiro else None
        else:
            primeiro = LocalEstoque.objects.first()
            local = primeiro.local if primeiro else None
        
        # Mapear tipo_movimento para o código de 2 letras do model
        tipo_mov_raw = dados.get('tipo_movimento', 'VENDA').upper()
        tipo_movimento = 'VE' # Default Venda
        if 'CONDICIONAL' in tipo_mov_raw:
            tipo_movimento = 'PV'
        elif 'COMPRA' in tipo_mov_raw: tipo_movimento = 'CO'
        elif 'DEVOLUCAO' in tipo_mov_raw: tipo_movimento = 'DV'
        
        if not itens:
            return JsonResponse({'erro': 'Nenhum item na venda'}, status=400)
        
        # CPF Consumidor para NFC-e (CPF na nota sem cadastro completo)
        cpf_consumidor = dados.get('cpf_consumidor', '').strip()

        # Se não informou cliente, buscar na Empresa ou usar CONSUMIDOR
        if not cliente_id:
            if cpf_consumidor and cpf_consumidor != 'ISENTO':
                cpf_clean = ''.join(filter(str.isdigit, cpf_consumidor))
                consumidor, created = Pessoa.objects.get_or_create(
                    cpf_cnpj=cpf_clean,
                    defaults={'nome': 'CONSUMIDOR', 'cliente': True}
                )
                cliente_id = consumidor.chave
            else:
                from apps.cadastros.models import Empresa
                empresa = Empresa.objects.first()
                if empresa and empresa.cliente_padrao:
                    cliente_id = empresa.cliente_padrao.chave
                else:
                    consumidor, created = Pessoa.objects.get_or_create(
                        nome='CONSUMIDOR',
                        defaults={'cpf_cnpj': '000.000.000-00', 'cliente': True}
                    )
                    cliente_id = consumidor.chave
        
        # Criar movimentação
        # Note: usuario -> usuario_criacao (FK)
        mov = MovimentacaoEstoque.objects.create(
            pessoa_id=cliente_id,
            vendedor_id=vendedor_id if vendedor_id else None,
            tipo_movimento=tipo_movimento,
            usuario_criacao=request.user if request.user.is_authenticated else None
        )
        
        # Criar itens usando ORM
        from apps.cadastros.models import ItemMovimentacaoEstoque
        for item in itens:
            # Calcular desconto em valor
            desconto_valor = 0
            if item.get('tipoDesconto') == 'percent':
                subtotal_item = float(item['quantidade']) * float(item['preco'])
                desconto_valor = subtotal_item * (float(item.get('desconto', 0)) / 100)
            else:
                desconto_valor = float(item.get('desconto', 0))
            
            # Calcular acréscimo em valor
            acrescimo_valor = 0
            if item.get('tipoAcrescimo') == 'percent':
                subtotal_item = float(item['quantidade']) * float(item['preco'])
                acrescimo_valor = subtotal_item * (float(item.get('acrescimo', 0)) / 100)
            else:
                acrescimo_valor = float(item.get('acrescimo', 0))
            
            ItemMovimentacaoEstoque.objects.create(
                movimentacao=mov,
                produto_id=item['produto_id'],
                quantidade=-abs(float(item['quantidade'])),  # Negativo para saída
                vr_unitario_bruto=float(item['preco']),
                vr_unitario_liquido=float(item['preco']), # Inicialmente igual
                vr_desconto_total=desconto_valor,
                vr_acrescimo_total=acrescimo_valor,
                local_id=local
            )
        
        # Recalcular totais da movimentação
        mov.recalcular_totais()
        
        # Se for condicional, criar PreVenda + ItemPreVenda
        if tipo_movimento == 'PV':
            from apps.cadastros.models import PreVenda, Empresa
            # Buscar vendedor padrão se não informado
            if not vendedor_id:
                try:
                    empresa = Empresa.objects.first()
                    if empresa and empresa.vendedor_padrao:
                        vendedor_id = empresa.vendedor_padrao.chave
                except:
                    pass
            # Se ainda não tem vendedor, buscar qualquer vendedor
            if not vendedor_id:
                from apps.cadastros.models import Pessoa
                vend = Pessoa.objects.filter(vendedor=True).first()
                if vend:
                    vendedor_id = vend.chave
            pv = PreVenda.objects.create(
                movimentacao=mov,
                vendedor_id=vendedor_id,
                efetivada=False
            )
            from apps.cadastros.models import ItemPreVenda
            for item_mov in mov.itens.all():
                ItemPreVenda.objects.create(
                    pre_venda=pv,
                    item_movimentacao=item_mov,
                    vendedor_id=vendedor_id,
                    quantidade_devolvida=0
                )
        
        # Emitir NF-e/NFC-e se solicitado
        erros_nfe = []
        nfe_result = None
        emitir_nfe = dados.get('emitir_nfe', False)
        tipo_doc = dados.get('tipo_documento_fiscal', '')
        if emitir_nfe and tipo_doc in ('55', '65'):
            try:
                from apps.fiscal.services import NFeService
                nfe = NFeService.criar_nfe_da_venda(
                    mov.pk_chave, usuario=request.user, modelo=tipo_doc,
                    modalidade_frete=dados.get('modalidade_frete', 9),
                    volumes=int(dados.get('volumes', 0) or 0),
                    especie=dados.get('especie', '')[:60],
                    peso_bruto=float(dados.get('peso_bruto', 0) or 0),
                    peso_liquido=float(dados.get('peso_liquido', 0) or 0),
                )
                from apps.cadastros.models import TipoPagamento
                from apps.fiscal.models import NFePagamento
                for pag in dados.get('pagamentos', []):
                    tp = TipoPagamento.objects.filter(pk_tipo_pagamento=pag.get('tipo_id')).first()
                    if not tp:
                        tp = TipoPagamento.objects.first()
                    cod_nfe = tp.forma_pagamento_nfe if (tp and tp.forma_pagamento_nfe) else 99
                    NFePagamento.objects.create(
                        nfe=nfe, tipo_pagamento=tp, forma_pagamento=cod_nfe,
                        valor=float(pag.get('valor', 0)),
                        integracao_pagamento='O',
                    )
                mov.emitir_nfe = True
                mov.tipo_documento_fiscal = tipo_doc
                mov.chave_nfe = nfe.chave_acesso
                mov.save(update_fields=['emitir_nfe', 'tipo_documento_fiscal', 'chave_nfe'])
                nfe_result = {'id': nfe.pk, 'numero': nfe.numero, 'chave': nfe.chave_acesso, 'status': nfe.status}
            except Exception as e:
                import traceback
                traceback.print_exc()
                mov.emitir_nfe = True
                mov.tipo_documento_fiscal = tipo_doc
                mov.save(update_fields=['emitir_nfe', 'tipo_documento_fiscal'])
                erros_nfe.append(f'Erro ao emitir NF-e: {str(e)}')
        
        # Gerar Financeiro (Contas a Receber / Caixa) - apenas para VENDA
        if tipo_movimento == 'VE':
            pagamentos = dados.get('pagamentos', [])
            from apps.cadastros.models import Empresa, TituloFinanceiro, TipoPagamento, Caixa, MovimentacaoCaixa
            from datetime import date, timedelta
            
            empresa = Empresa.objects.first()
            caixa_aberto = Caixa.objects.filter(usuario=request.user, aberto=True).first() if request.user.is_authenticated else None
            
            # Calcular troco (total pago - total venda)
            total_pago = sum(float(p.get('valor', 0)) for p in pagamentos)
            total_venda = abs(float(mov.vr_total_liquido))
            troco = max(0, total_pago - total_venda)
            
            for pag in pagamentos:
                tipo_id = pag.get('tipo_id')
                valor_pag = float(pag.get('valor', 0))
                if valor_pag <= 0: continue

                tipo_pgto = TipoPagamento.objects.filter(pk_tipo_pagamento=tipo_id).first()
                if not tipo_pgto: continue
                
                # Ajustar valor proporcionalmente descontando o troco
                if troco > 0 and total_pago > 0:
                    proporcao = valor_pag / total_pago
                    valor_liquido = round(valor_pag - (troco * proporcao), 2)
                else:
                    valor_liquido = valor_pag

                if tipo_pgto.situacoes_permitidas == 'AP' or tipo_pgto.tipo_pagamento == 'CREDIARIO':
                    num_parcelas = int(pag.get('parcelas', 1))
                    valores_parcela = pag.get('valores_parcela', [])
                    vencimentos = pag.get('vencimentos', [])

                    for i in range(1, num_parcelas + 1):
                        if valores_parcela and i <= len(valores_parcela):
                            valor_parcela = float(valores_parcela[i-1])
                        else:
                            valor_parcela_base = round(valor_liquido / num_parcelas, 2)
                            if i == num_parcelas:
                                valor_parcela = round(valor_liquido - (valor_parcela_base * (num_parcelas - 1)), 2)
                            else:
                                valor_parcela = valor_parcela_base

                        data_venc = date.today() + timedelta(days=30 * i)
                        if vencimentos and i <= len(vencimentos):
                            from datetime import datetime as dt
                            try:
                                data_venc = dt.strptime(vencimentos[i-1], '%Y-%m-%d').date()
                            except:
                                pass

                        TituloFinanceiro.objects.create(
                            tipo='R',
                            pessoa_id=cliente_id,
                            data_vencimento=data_venc,
                            numero_documento=f"VE{mov.pk_chave}",
                            parcela=i,
                            total_parcelas=num_parcelas,
                            valor_documento=valor_parcela,
                            valor_saldo=valor_parcela,
                            situacao='ABERTO',
                            tipo_pagamento=tipo_pgto,
                            plano_contas=empresa.plano_contas_receita_venda if empresa else None,
                            centro_custo=empresa.centro_custo_venda if empresa else None,
                            movimentacao_estoque=mov,
                            usuario_criacao=request.user if request.user.is_authenticated else None
                        )
                else:
                    if caixa_aberto:
                        MovimentacaoCaixa.objects.create(
                            caixa=caixa_aberto,
                            tipo_operacao='E',
                            valor=valor_liquido,
                            tipo_pagamento=tipo_pgto,
                            historico=f"Recebimento Venda #{mov.pk_chave}"
                        )
                    TituloFinanceiro.objects.create(
                        tipo='R',
                        pessoa_id=cliente_id,
                        data_vencimento=date.today(),
                        data_pagamento=date.today(),
                        numero_documento=f"VE{mov.pk_chave}",
                        valor_documento=valor_liquido,
                        valor_pago=valor_liquido,
                        valor_saldo=0,
                        situacao='PAGO',
                        tipo_pagamento=tipo_pgto,
                        plano_contas=empresa.plano_contas_receita_venda if empresa else None,
                        centro_custo=empresa.centro_custo_venda if empresa else None,
                        movimentacao_estoque=mov,
                        usuario_criacao=request.user if request.user.is_authenticated else None
                    )
        
        resp = {
            'sucesso': True,
            'movimentacao_id': mov.pk_chave,
            'mensagem': f"{'Condicional' if tipo_movimento == 'PV' else 'Venda'} #{mov.pk_chave} {'salvo' if tipo_movimento == 'PV' else 'finalizada'} com sucesso!",
        }
        if nfe_result:
            resp['nfe'] = nfe_result
        if erros_nfe:
            resp['erros_nfe'] = erros_nfe
        return JsonResponse(resp)
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': f'Erro ao finalizar: {str(e)}'}, status=500)


def api_buscar_pessoas(request):
    """API: Buscar pessoas para autocomplete com dados completos."""
    termo = request.GET.get('q', '').strip()
    
    if len(termo) < 3:
        return JsonResponse({'results': []})
    
    from apps.cadastros.models import Pessoa
    from django.db.models import Q
    
    # Busca por nome ou CPF/CNPJ
    pessoas = Pessoa.objects.filter(
        Q(nome__icontains=termo) | 
        Q(cpf_cnpj__icontains=termo)
    )[:10]
    
    results = []
    for p in pessoas:
        # Telefone está na própria Pessoa
        telefone = p.telefone_fixo or p.celular_principal or ''
        
        # Cidade do endereço principal (se existir)
        cidade = ''
        try:
            end_principal = p.endereco_principal_rel
            if end_principal and end_principal.cidade:
                cidade = f"{end_principal.cidade.nome}/{end_principal.cidade.uf}"
        except:
            pass
        
        results.append({
            'chave': p.chave,
            'nome': p.nome,
            'cpf_cnpj': p.cpf_cnpj or '',
            'telefone': telefone,
            'cidade': cidade
        })
    
    return JsonResponse({'results': results})


@transaction.atomic
def api_criar_cliente_rapido(request):
    """API: Cadastro rápido de cliente no PDV."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    
    import json
    dados = json.loads(request.body)
    
    nome = dados.get('nome', '').strip()
    if not nome:
        return JsonResponse({'erro': 'Nome obrigatório'}, status=400)
    
    from apps.cadastros.models import Pessoa, Cliente
    
    # Criar pessoa
    cpf_cnpj = dados.get('cpf_cnpj', '').strip()
    pessoa = Pessoa.objects.create(
        nome=nome,
        cpf_cnpj=cpf_cnpj or None
    )
    
    # Marcar como cliente
    Cliente.objects.create(pessoa=pessoa)
    
    return JsonResponse({
        'sucesso': True,
        'cliente': {
            'chave': pessoa.chave,
            'nome': pessoa.nome,
            'cpf_cnpj': cpf_cnpj,
            'telefone': '',
            'cidade': ''
        }
    })
