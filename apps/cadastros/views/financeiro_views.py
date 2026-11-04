from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.contrib import messages
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from apps.cadastros.models import (
    TituloFinanceiro, Caixa, MovimentacaoCaixa, 
    Pessoa, TipoPagamento, PlanoContas, CentroCusto, ContaBancaria, Empresa
)
from apps.cadastros.forms import TituloFinanceiroForm


def caixa_status(request):
    """Verifica se há caixa aberto para o usuário e retorna dados consolidados."""
    if not request.user.is_authenticated:
        return JsonResponse({'aberto': False, 'caixa_aberto': False, 'erro': 'Não autenticado'})
    
    caixa = Caixa.objects.filter(usuario=request.user, aberto=True).first()
    if caixa:
        entradas = caixa.movimentacoes.filter(tipo_operacao='E').aggregate(Sum('valor'))['valor__sum'] or 0
        saidas = caixa.movimentacoes.filter(tipo_operacao='S').aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_atual = float(caixa.valor_abertura) + float(entradas) - float(saidas)

        movimentacoes = []
        for m in caixa.movimentacoes.select_related('tipo_pagamento').order_by('-data_movimento')[:100]:
            movimentacoes.append({
                'id': m.pk_chave,
                'hora': m.data_movimento.strftime('%H:%M'),
                'descricao': m.historico,
                'tipo_pgto_nome': m.tipo_pagamento.tipo_pagamento if m.tipo_pagamento else 'Dinheiro',
                'tipo_pgto_id': m.tipo_pagamento.pk_tipo_pagamento if m.tipo_pagamento else None,
                'valor': float(m.valor),
                'tipo': m.tipo_operacao
            })

        from collections import defaultdict
        resumo_pgto = defaultdict(lambda: {'entradas': 0, 'saidas': 0})
        for m in movimentacoes:
            chave = m['tipo_pgto_nome']
            if m['tipo'] == 'E':
                resumo_pgto[chave]['entradas'] += m['valor']
            else:
                resumo_pgto[chave]['saidas'] += m['valor']

        resumo_pagamentos = [
            {'tipo': k, 'entradas': round(v['entradas'], 2), 'saidas': round(v['saidas'], 2)}
            for k, v in sorted(resumo_pgto.items())
        ]

        return JsonResponse({
            'aberto': True,
            'caixa_aberto': True,
            'caixa_id': caixa.pk_chave,
            'data_abertura': caixa.data_abertura.strftime('%d/%m/%Y %H:%M'),
            'valor_abertura': float(caixa.valor_abertura),
            'saldo': float(saldo_atual),
            'entradas': float(entradas),
            'saidas': float(saidas),
            'saldo_atual': float(saldo_atual),
            'movimentacoes': movimentacoes,
            'resumo_pagamentos': resumo_pagamentos
        })
    return JsonResponse({'aberto': False, 'caixa_aberto': False})


@login_required
@transaction.atomic
def caixa_operacao(request):
    """Realiza Sangria ou Suprimento."""
    if request.method == 'POST':
        caixa = Caixa.objects.filter(usuario=request.user, aberto=True).first()
        if not caixa:
            return JsonResponse({'erro': 'Não há caixa aberto.'}, status=400)
            
        dados = json.loads(request.body)
        tipo = dados.get('tipo')  # 'E' para Suprimento, 'S' para Sangria
        valor = Decimal(str(dados.get('valor', 0)))
        historico = dados.get('historico')
        
        tipo_dinheiro = TipoPagamento.objects.filter(tipo_pagamento__icontains='DINHEIRO').first()
        
        MovimentacaoCaixa.objects.create(
            caixa=caixa,
            tipo_operacao=tipo,
            valor=valor,
            tipo_pagamento=tipo_dinheiro,
            historico=historico
        )
        
        return JsonResponse({'sucesso': True, 'mensagem': 'Operação realizada com sucesso!'})
    return JsonResponse({'erro': 'Método inválido'}, status=400)


@login_required
@transaction.atomic
def caixa_abrir(request):
    """Abre o caixa para o usuário."""
    if request.method == 'POST':
        dados = json.loads(request.body)
        valor_abertura = Decimal(str(dados.get('valor_abertura', 0)))
        
        if Caixa.objects.filter(usuario=request.user, aberto=True).exists():
            return JsonResponse({'erro': 'Você já possui um caixa aberto.'}, status=400)
            
        caixa = Caixa.objects.create(
            usuario=request.user,
            valor_abertura=valor_abertura,
            aberto=True
        )
        
        return JsonResponse({
            'sucesso': True,
            'caixa_id': caixa.pk_chave,
            'mensagem': 'Caixa aberto com sucesso!'
        })
    return JsonResponse({'erro': 'Método inválido'}, status=400)


@login_required
@transaction.atomic
def caixa_fechar(request):
    """Fecha o caixa do usuário."""
    if request.method == 'POST':
        caixa = Caixa.objects.filter(usuario=request.user, aberto=True).first()
        if not caixa:
            return JsonResponse({'erro': 'Não há caixa aberto para fechar.'}, status=400)
            
        dados = json.loads(request.body)
        valor_fechamento = Decimal(str(dados.get('valor_fechamento', 0)))
        
        caixa.data_fechamento = datetime.now()
        caixa.valor_fechamento = valor_fechamento
        caixa.aberto = False
        caixa.save()
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Caixa fechado com sucesso!'
        })
    return JsonResponse({'erro': 'Método inválido'}, status=400)


@login_required
def caixa_controle(request):
    """Tela de controle de caixa."""
    return render(request, 'cadastros/financeiro/caixa.html')


# =============================================================================
# CONTAS A PAGAR & CONTAS A RECEBER (MÓDULO FINANCEIRO REFORMULADO)
# =============================================================================

@login_required
def listar_titulos(request, tipo='P'):
    """Lista títulos a pagar (P) ou a receber (R) com métricas e filtros corporativos."""
    hoje = date.today()
    
    # Atualiza automaticamente status de títulos vencidos em aberto
    TituloFinanceiro.objects.filter(
        tipo=tipo,
        data_vencimento__lt=hoje,
        situacao='ABERTO'
    ).update(situacao='ATRASADO')

    # Queryset base
    qs = TituloFinanceiro.objects.filter(tipo=tipo).select_related(
        'pessoa', 'tipo_pagamento', 'plano_contas', 'centro_custo', 'conta_bancaria'
    )

    # Filtros da requisição
    q = request.GET.get('q', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    data_ini = request.GET.get('data_ini', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()
    plano_contas_id = request.GET.get('plano_contas', '').strip()
    centro_custo_id = request.GET.get('centro_custo', '').strip()
    conta_bancaria_id = request.GET.get('conta_bancaria', '').strip()

    if q:
        qs = qs.filter(
            Q(pessoa__nome__icontains=q) |
            Q(pessoa__cpf_cnpj__icontains=q) |
            Q(numero_documento__icontains=q) |
            Q(historico__icontains=q)
        )

    if situacao:
        if situacao == 'ABERTO':
            qs = qs.filter(situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL'])
        elif situacao == 'VENCIDO':
            qs = qs.filter(data_vencimento__lt=hoje, situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL'])
        else:
            qs = qs.filter(situacao=situacao)

    if data_ini:
        try:
            d_ini = datetime.strptime(data_ini, '%Y-%m-%d').date()
            qs = qs.filter(data_vencimento__gte=d_ini)
        except ValueError:
            pass

    if data_fim:
        try:
            d_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            qs = qs.filter(data_vencimento__lte=d_fim)
        except ValueError:
            pass

    if plano_contas_id:
        qs = qs.filter(plano_contas_id=plano_contas_id)

    if centro_custo_id:
        qs = qs.filter(centro_custo_id=centro_custo_id)

    if conta_bancaria_id:
        qs = qs.filter(conta_bancaria_id=conta_bancaria_id)

    # Ordenação padrão
    titulos = qs.order_by('data_vencimento', 'numero_documento', 'parcela')

    # Métricas consolidadas (base geral do tipo)
    base_geral = TituloFinanceiro.objects.filter(tipo=tipo)
    total_aberto = base_geral.filter(situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).aggregate(Sum('valor_saldo'))['valor_saldo__sum'] or Decimal('0.00')
    total_vencido = base_geral.filter(data_vencimento__lt=hoje, situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).aggregate(Sum('valor_saldo'))['valor_saldo__sum'] or Decimal('0.00')
    vence_hoje = base_geral.filter(data_vencimento=hoje, situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).aggregate(Sum('valor_saldo'))['valor_saldo__sum'] or Decimal('0.00')
    
    inicio_mes = hoje.replace(day=1)
    total_pago_mes = base_geral.filter(data_pagamento__gte=inicio_mes, situacao__in=['PAGO', 'PARCIAL']).aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal('0.00')

    count_aberto = base_geral.filter(situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).count()
    count_vencido = base_geral.filter(data_vencimento__lt=hoje, situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).count()

    # Opções para filtros e ações rápidas
    tipo_pc = 'D' if tipo == 'P' else 'R'
    planos_contas = PlanoContas.objects.filter(tipo_conta__in=[tipo_pc, 'A']).order_by('codigo')
    centros_custo = CentroCusto.objects.all().order_by('codigo')
    contas_bancarias = ContaBancaria.objects.filter(inativo=False).order_by('nome_conta')
    tipos_pagamento = TipoPagamento.objects.filter(ativo=True).order_by('tipo_pagamento')
    
    # Verifica caixa do usuário
    caixa_aberto = Caixa.objects.filter(usuario=request.user, aberto=True).exists()

    template = 'cadastros/financeiro/contas_pagar.html' if tipo == 'P' else 'cadastros/financeiro/contas_receber.html'
    
    context = {
        'titulos': titulos,
        'tipo': tipo,
        'hoje': hoje,
        'today': hoje,
        'total_aberto': total_aberto,
        'total_vencido': total_vencido,
        'vence_hoje': vence_hoje,
        'total_pago_mes': total_pago_mes,
        'count_aberto': count_aberto,
        'count_vencido': count_vencido,
        'planos_contas': planos_contas,
        'centros_custo': centros_custo,
        'contas_bancarias': contas_bancarias,
        'tipos_pagamento': tipos_pagamento,
        'caixa_aberto': caixa_aberto,
        'filtros': {
            'q': q,
            'situacao': situacao,
            'data_ini': data_ini,
            'data_fim': data_fim,
            'plano_contas': plano_contas_id,
            'centro_custo': centro_custo_id,
            'conta_bancaria': conta_bancaria_id,
        }
    }
    return render(request, template, context)


@login_required
@transaction.atomic
def titulo_novo_view(request, tipo='P'):
    """
    Tela dedicada e profissional para lançamento de novos títulos (Pagar ou Receber).
    Suporta gerador dinâmico de parcelas com ajuste individual no front-end.
    """
    if request.method == 'POST':
        # Suporta tanto requisição JSON (do gerador de parcelas) quanto Form convencional
        if request.content_type == 'application/json':
            dados = json.loads(request.body)
        else:
            dados = request.POST

        tipo_op = dados.get('tipo', tipo)
        pessoa_id = dados.get('pessoa_id') or dados.get('pessoa')
        if not pessoa_id:
            msg = 'Selecione a pessoa (fornecedor ou cliente).'
            if request.content_type == 'application/json':
                return JsonResponse({'sucesso': False, 'erro': msg}, status=400)
            messages.error(request, msg)
            return redirect(f"{request.path}?tipo={tipo_op}")

        numero_doc_base = dados.get('numero_documento', '').strip() or 'DOC'
        data_emissao = dados.get('data_emissao') or date.today().strftime('%Y-%m-%d')
        plano_contas_id = dados.get('plano_contas_id') or dados.get('plano_contas') or None
        centro_custo_id = dados.get('centro_custo_id') or dados.get('centro_custo') or None
        conta_bancaria_id = dados.get('conta_bancaria_id') or dados.get('conta_bancaria') or None
        tipo_pagamento_id = dados.get('tipo_pagamento_id') or dados.get('tipo_pagamento') or None
        historico = dados.get('historico', '').strip()

        # Verifica se foram enviadas parcelas customizadas
        parcelas_customizadas = dados.get('parcelas')
        if parcelas_customizadas and isinstance(parcelas_customizadas, list) and len(parcelas_customizadas) > 0:
            total_p = len(parcelas_customizadas)
            for idx, p in enumerate(parcelas_customizadas, start=1):
                num_p = p.get('parcela', idx)
                doc_p = p.get('numero_documento') or (f"{numero_doc_base}/{num_p}" if total_p > 1 else numero_doc_base)
                venc_p = datetime.strptime(str(p['data_vencimento']), '%Y-%m-%d').date()
                val_p = Decimal(str(p['valor']))

                TituloFinanceiro.objects.create(
                    tipo=tipo_op,
                    pessoa_id=pessoa_id,
                    numero_documento=doc_p,
                    parcela=num_p,
                    total_parcelas=total_p,
                    data_emissao=data_emissao,
                    data_vencimento=venc_p,
                    valor_documento=val_p,
                    valor_saldo=val_p,
                    situacao='ABERTO',
                    plano_contas_id=plano_contas_id,
                    centro_custo_id=centro_custo_id,
                    conta_bancaria_id=conta_bancaria_id,
                    tipo_pagamento_id=tipo_pagamento_id,
                    historico=historico,
                    usuario_criacao=request.user
                )
            
            sucesso_msg = f'{total_p} parcela(s) lançada(s) com sucesso!'
            if request.content_type == 'application/json':
                url_redirecionamento = '/cadastros/financeiro/contas-pagar/' if tipo_op == 'P' else '/cadastros/financeiro/contas-receber/'
                return JsonResponse({'sucesso': True, 'mensagem': sucesso_msg, 'redirect_url': url_redirecionamento})
            messages.success(request, sucesso_msg)
            return redirect('cadastros:contas_pagar' if tipo_op == 'P' else 'cadastros:contas_receber')

        else:
            # Lançamento simples de 1 parcela
            valor_total = Decimal(str(dados.get('valor_total') or dados.get('valor_documento', 0)))
            data_vencimento = datetime.strptime(str(dados.get('data_vencimento')), '%Y-%m-%d').date()
            
            TituloFinanceiro.objects.create(
                tipo=tipo_op,
                pessoa_id=pessoa_id,
                numero_documento=numero_doc_base,
                parcela=1,
                total_parcelas=1,
                data_emissao=data_emissao,
                data_vencimento=data_vencimento,
                valor_documento=valor_total,
                valor_saldo=valor_total,
                situacao='ABERTO',
                plano_contas_id=plano_contas_id,
                centro_custo_id=centro_custo_id,
                conta_bancaria_id=conta_bancaria_id,
                tipo_pagamento_id=tipo_pagamento_id,
                historico=historico,
                usuario_criacao=request.user
            )

            sucesso_msg = 'Título financeiro cadastrado com sucesso!'
            if request.content_type == 'application/json':
                url_redirecionamento = '/cadastros/financeiro/contas-pagar/' if tipo_op == 'P' else '/cadastros/financeiro/contas-receber/'
                return JsonResponse({'sucesso': True, 'mensagem': sucesso_msg, 'redirect_url': url_redirecionamento})
            messages.success(request, sucesso_msg)
            return redirect('cadastros:contas_pagar' if tipo_op == 'P' else 'cadastros:contas_receber')

    # GET
    tipo_op = request.GET.get('tipo', tipo).upper()
    if tipo_op not in ['P', 'R']:
        tipo_op = 'P'

    tipo_pc = 'D' if tipo_op == 'P' else 'R'
    if tipo_op == 'P':
        pessoas = Pessoa.objects.filter(fornecedor=True).order_by('nome')
    else:
        pessoas = Pessoa.objects.filter(cliente=True).order_by('nome')
    if not pessoas.exists():
        pessoas = Pessoa.objects.all().order_by('nome')

    context = {
        'tipo': tipo_op,
        'titulo_pagina': 'Novo Título a Pagar' if tipo_op == 'P' else 'Novo Título a Receber',
        'pessoas': pessoas,
        'tipos_pagamento': TipoPagamento.objects.filter(ativo=True).order_by('tipo_pagamento'),
        'planos_contas': PlanoContas.objects.filter(tipo_conta__in=[tipo_pc, 'A']).order_by('codigo'),
        'centros_custo': CentroCusto.objects.all().order_by('codigo'),
        'contas_bancarias': ContaBancaria.objects.filter(inativo=False).order_by('nome_conta'),
        'hoje': date.today().strftime('%Y-%m-%d'),
        'modo_edicao': False,
    }
    return render(request, 'cadastros/financeiro/titulo_form.html', context)


@login_required
@transaction.atomic
def titulo_editar_view(request, pk):
    """Edição completa de um título existente. Aceita JSON ou form POST."""
    titulo = get_object_or_404(TituloFinanceiro, pk_chave=pk)

    if request.method == 'POST':
        if request.content_type == 'application/json':
            dados = json.loads(request.body)
        else:
            dados = request.POST

        # Atualiza campos editáveis
        numero_doc = dados.get('numero_documento', '').strip() or titulo.numero_documento
        data_emissao = dados.get('data_emissao') or None
        data_vencimento_str = dados.get('data_vencimento')
        historico = dados.get('historico', '').strip()
        plano_contas_id = dados.get('plano_contas_id') or dados.get('plano_contas') or None
        centro_custo_id = dados.get('centro_custo_id') or dados.get('centro_custo') or None
        conta_bancaria_id = dados.get('conta_bancaria_id') or dados.get('conta_bancaria') or None
        tipo_pagamento_id = dados.get('tipo_pagamento_id') or dados.get('tipo_pagamento') or None
        valor_documento = dados.get('valor_total') or dados.get('valor_documento')

        try:
            if data_vencimento_str:
                titulo.data_vencimento = datetime.strptime(str(data_vencimento_str), '%Y-%m-%d').date()
            if data_emissao:
                titulo.data_emissao = datetime.strptime(str(data_emissao), '%Y-%m-%d').date()
            if valor_documento:
                titulo.valor_documento = Decimal(str(valor_documento))
            titulo.numero_documento = numero_doc
            titulo.historico = historico
            if plano_contas_id:
                titulo.plano_contas_id = plano_contas_id
            if centro_custo_id:
                titulo.centro_custo_id = centro_custo_id
            if conta_bancaria_id:
                titulo.conta_bancaria_id = conta_bancaria_id
            if tipo_pagamento_id:
                titulo.tipo_pagamento_id = tipo_pagamento_id

            # Recalcula saldo
            total_devido = titulo.valor_documento + (titulo.valor_juros or Decimal('0.00')) - (titulo.valor_desconto or Decimal('0.00'))
            titulo.valor_saldo = max(Decimal('0.00'), total_devido - (titulo.valor_pago or Decimal('0.00')))
            if titulo.valor_saldo <= 0 and titulo.valor_pago > 0:
                titulo.situacao = 'PAGO'
            titulo.save()

            url_retorno = '/cadastros/financeiro/contas-pagar/' if titulo.tipo == 'P' else '/cadastros/financeiro/contas-receber/'
            if request.content_type == 'application/json':
                return JsonResponse({'sucesso': True, 'mensagem': f'Título #{titulo.numero_documento} atualizado com sucesso!', 'redirect_url': url_retorno})
            messages.success(request, f'Título #{titulo.numero_documento} atualizado com sucesso!')
            return redirect('cadastros:contas_pagar' if titulo.tipo == 'P' else 'cadastros:contas_receber')

        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'sucesso': False, 'erro': str(e)}, status=400)
            messages.error(request, str(e))

    tipo_pc = 'D' if titulo.tipo == 'P' else 'R'
    context = {
        'titulo': titulo,
        'tipo': titulo.tipo,
        'titulo_pagina': f'Editar Título #{titulo.numero_documento}',
        'tipos_pagamento': TipoPagamento.objects.filter(ativo=True).order_by('tipo_pagamento'),
        'planos_contas': PlanoContas.objects.filter(tipo_conta__in=[tipo_pc, 'A']).order_by('codigo'),
        'centros_custo': CentroCusto.objects.all().order_by('codigo'),
        'contas_bancarias': ContaBancaria.objects.filter(inativo=False).order_by('nome_conta'),
        'hoje': date.today().strftime('%Y-%m-%d'),
        'modo_edicao': True,
    }
    return render(request, 'cadastros/financeiro/titulo_form.html', context)



@login_required
@transaction.atomic
def baixar_titulo(request, pk):
    """
    Realiza a baixa (total ou parcial) de um título a pagar ou receber.
    Suporta desconto, juros/multa, conta de destino e integração com o caixa aberto.
    """
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'}, status=405)

    titulo = get_object_or_404(TituloFinanceiro, pk_chave=pk)

    if titulo.situacao == 'PAGO':
        return JsonResponse({'sucesso': False, 'erro': 'Este título já está totalmente liquidado.'}, status=400)

    try:
        if request.content_type == 'application/json':
            dados = json.loads(request.body)
        else:
            dados = request.POST

        valor_pago_baixa = Decimal(str(dados.get('valor_pago', 0)))
        if valor_pago_baixa <= 0:
            return JsonResponse({'sucesso': False, 'erro': 'Informe um valor de pagamento maior que zero.'}, status=400)

        data_pagamento_str = dados.get('data_pagamento')
        data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date() if data_pagamento_str else date.today()

        valor_desconto = Decimal(str(dados.get('valor_desconto', 0) or 0))
        valor_juros = Decimal(str(dados.get('valor_juros', 0) or 0))

        tipo_pgto_id = dados.get('tipo_pagamento_id')
        conta_bancaria_id = dados.get('conta_bancaria_id')
        obs_baixa = dados.get('observacoes_baixa', '').strip()
        lancar_caixa = str(dados.get('lancar_caixa', 'false')).lower() in ['true', '1', 'on']

        # Atualiza acumuladores de pagamento no título
        titulo.valor_pago = (titulo.valor_pago or Decimal('0.00')) + valor_pago_baixa
        titulo.valor_desconto = (titulo.valor_desconto or Decimal('0.00')) + valor_desconto
        titulo.valor_juros = (titulo.valor_juros or Decimal('0.00')) + valor_juros
        titulo.data_pagamento = data_pagamento

        if tipo_pgto_id:
            titulo.tipo_pagamento_id = tipo_pgto_id
        if conta_bancaria_id:
            titulo.conta_bancaria_id = conta_bancaria_id
        if obs_baixa:
            titulo.observacoes_baixa = obs_baixa

        # Calcula saldo restante
        total_devido = titulo.valor_documento + titulo.valor_juros - titulo.valor_desconto
        saldo_restante = total_devido - titulo.valor_pago

        if saldo_restante <= Decimal('0.005'):
            titulo.valor_saldo = Decimal('0.00')
            titulo.situacao = 'PAGO'
        else:
            titulo.valor_saldo = saldo_restante
            titulo.situacao = 'PARCIAL'

        titulo.save()

        # Integração automática com o Caixa se solicitado e houver caixa aberto
        movimento_id = None
        if lancar_caixa:
            caixa = Caixa.objects.filter(usuario=request.user, aberto=True).first()
            if caixa:
                tp = titulo.tipo_pagamento or TipoPagamento.objects.filter(tipo_pagamento__icontains='DINHEIRO').first()
                if not tp:
                    tp = TipoPagamento.objects.first()

                tipo_op_caixa = 'E' if titulo.tipo == 'R' else 'S'
                mov = MovimentacaoCaixa.objects.create(
                    caixa=caixa,
                    tipo_operacao=tipo_op_caixa,
                    valor=valor_pago_baixa,
                    tipo_pagamento=tp,
                    titulo_financeiro=titulo,
                    historico=f"Baixa título #{titulo.numero_documento} ({titulo.parcela}/{titulo.total_parcelas}) - {titulo.pessoa.nome}"
                )
                movimento_id = mov.pk_chave

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Título #{titulo.numero_documento} ({titulo.parcela}/{titulo.total_parcelas}) baixado com sucesso!',
            'situacao': titulo.situacao,
            'situacao_display': titulo.get_situacao_display(),
            'valor_pago': float(titulo.valor_pago),
            'valor_saldo': float(titulo.valor_saldo),
            'caixa_movimento_id': movimento_id
        })

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=400)


@login_required
@transaction.atomic
def cancelar_titulo(request, pk):
    """Cancela um título em aberto."""
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'}, status=405)
    titulo = get_object_or_404(TituloFinanceiro, pk_chave=pk)
    if titulo.situacao == 'PAGO':
        return JsonResponse({'sucesso': False, 'erro': 'Títulos já liquidados não podem ser cancelados diretamente. Estorne o pagamento primeiro.'}, status=400)
    
    titulo.situacao = 'CANCELADO'
    titulo.save()
    return JsonResponse({'sucesso': True, 'mensagem': f'Título #{titulo.numero_documento} cancelado com sucesso.'})


@login_required
@transaction.atomic
def estornar_titulo(request, pk):
    """Estorna um pagamento efetuado em um título."""
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'}, status=405)
    titulo = get_object_or_404(TituloFinanceiro, pk_chave=pk)
    
    # Se houver movimentações de caixa vinculadas, remove-as ou avisa
    MovimentacaoCaixa.objects.filter(titulo_financeiro=titulo).delete()

    titulo.valor_pago = Decimal('0.00')
    titulo.valor_desconto = Decimal('0.00')
    titulo.valor_juros = Decimal('0.00')
    titulo.valor_saldo = titulo.valor_documento
    titulo.data_pagamento = None
    titulo.situacao = 'ABERTO'
    titulo.save()

    return JsonResponse({'sucesso': True, 'mensagem': f'Pagamento do título #{titulo.numero_documento} estornado com sucesso!'})


@login_required
@transaction.atomic
def excluir_titulo(request, pk):
    """Exclui um título avulso."""
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'}, status=405)
    titulo = get_object_or_404(TituloFinanceiro, pk_chave=pk)
    if titulo.movimentacao_estoque:
        return JsonResponse({'sucesso': False, 'erro': 'Este título foi gerado automaticamente por uma Venda/Movimentação comercial e não pode ser excluído individualmente.'}, status=400)

    MovimentacaoCaixa.objects.filter(titulo_financeiro=titulo).delete()
    titulo.delete()
    return JsonResponse({'sucesso': True, 'mensagem': 'Título excluído com sucesso.'})


# =============================================================================
# RECEBIMENTO DE CREDIÁRIO / CARNÊ DE CLIENTES
# =============================================================================

@login_required
def recebimento_crediario(request):
    """
    Tela dedicada, rápida e corporativa para Recebimento de Crediário (Carnê).
    Permite selecionar o cliente, marcar uma ou mais parcelas em aberto,
    calcular troco/juros/desconto e liquidar emitindo o recibo instantâneo.
    """
    hoje = date.today()
    caixa_aberto = Caixa.objects.filter(usuario=request.user, aberto=True).exists()
    tipos_pagamento = TipoPagamento.objects.filter(ativo=True).order_by('tipo_pagamento')
    contas_bancarias = ContaBancaria.objects.filter(inativo=False).order_by('nome_conta')

    icon_map = {
        'DINHEIRO': 'fas fa-money-bill-wave text-green-600',
        'DÉBITO': 'fas fa-credit-card text-blue-600',
        'DEBITO': 'fas fa-credit-card text-blue-600',
        'CRÉDITO': 'fas fa-credit-card text-purple-600',
        'CREDITO': 'fas fa-credit-card text-purple-600',
        'PIX': 'fas fa-qrcode text-teal-600',
        'BOLETO': 'fas fa-barcode text-orange-600',
        'CREDIARIO': 'fas fa-handshake text-yellow-600',
        'CREDIÁRIO': 'fas fa-handshake text-yellow-600',
        'HAVER': 'fas fa-user-tag text-gray-600',
        'CHEQUE': 'fas fa-money-check text-amber-600',
    }
    
    tipos_pagamento_com_icone = []
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
            'dinheiro': 'DINHEIRO' in nome_upper,
        })

    context = {
        'hoje': hoje,
        'caixa_aberto': caixa_aberto,
        'tipos_pagamento': tipos_pagamento,
        'tipos_pagamento_json': json.dumps(tipos_pagamento_com_icone),
        'contas_bancarias': contas_bancarias,
    }
    return render(request, 'cadastros/financeiro/crediario.html', context)


@login_required
def api_titulos_cliente(request, pessoa_id):
    """API que retorna todas as parcelas de crediário em aberto/vencidas de um cliente específico."""
    cliente = get_object_or_404(Pessoa, chave=pessoa_id)
    hoje = date.today()

    # Atualiza títulos vencidos
    TituloFinanceiro.objects.filter(
        tipo='R',
        pessoa=cliente,
        data_vencimento__lt=hoje,
        situacao='ABERTO'
    ).update(situacao='ATRASADO')

    titulos_qs = TituloFinanceiro.objects.filter(
        tipo='R',
        pessoa=cliente,
        situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']
    ).select_related('tipo_pagamento').order_by('data_vencimento', 'parcela')

    parcelas = []
    total_devedor = Decimal('0.00')
    total_vencido = Decimal('0.00')

    for t in titulos_qs:
        total_devedor += t.valor_saldo
        is_venc = t.data_vencimento < hoje
        dias_atr = (hoje - t.data_vencimento).days if is_venc else 0
        if is_venc:
            total_vencido += t.valor_saldo

        parcelas.append({
            'id': t.pk_chave,
            'numero_documento': t.numero_documento,
            'parcela': t.parcela,
            'total_parcelas': t.total_parcelas,
            'data_vencimento': t.data_vencimento.strftime('%d/%m/%Y'),
            'vencimento_iso': t.data_vencimento.strftime('%Y-%m-%d'),
            'is_vencido': is_venc,
            'dias_atraso': dias_atr,
            'valor_documento': float(t.valor_documento),
            'valor_pago': float(t.valor_pago),
            'valor_saldo': float(t.valor_saldo),
            'forma_pagamento': t.tipo_pagamento.tipo_pagamento if t.tipo_pagamento else 'Crediário',
            'situacao': t.situacao,
            'situacao_display': t.get_situacao_display()
        })

    return JsonResponse({
        'sucesso': True,
        'cliente': {
            'id': cliente.chave,
            'nome': cliente.nome,
            'nome_fantasia': cliente.nome_fantasia or '',
            'cpf_cnpj': cliente.cpf_cnpj or '',
            'celular': cliente.celular_principal or cliente.telefone_fixo or '',
            'limite_credito': float(cliente.limite_credito) if cliente.limite_credito else 0.0,
            'total_devedor': float(total_devedor),
            'total_vencido': float(total_vencido),
            'qtd_parcelas': len(parcelas),
        },
        'parcelas': parcelas
    })


@login_required
@transaction.atomic
def processar_recebimento_crediario(request):
    """
    Processa a quitação atômica de múltiplas parcelas de crediário selecionadas.
    Gera lançamento no caixa e retorna chave para emissão de recibo.
    """
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'}, status=405)

    try:
        dados = json.loads(request.body)
        pessoa_id = dados.get('pessoa_id')
        titulos_ids = dados.get('titulos_ids', [])
        
        if not pessoa_id or not titulos_ids:
            return JsonResponse({'sucesso': False, 'erro': 'Selecione ao menos uma parcela para recebimento.'}, status=400)

        cliente = get_object_or_404(Pessoa, chave=pessoa_id)
        titulos = TituloFinanceiro.objects.filter(pk_chave__in=titulos_ids, tipo='R', pessoa=cliente).select_related('tipo_pagamento')

        if not titulos.exists():
            return JsonResponse({'sucesso': False, 'erro': 'Nenhuma parcela válida encontrada.'}, status=400)

        tipo_pagamento_id = dados.get('forma_pagamento_id')
        tipo_pagamento = TipoPagamento.objects.filter(pk_tipo_pagamento=tipo_pagamento_id).first() if tipo_pagamento_id else None
        
        lancar_caixa = bool(dados.get('lancar_caixa', True))
        data_pagamento = date.today()
        
        total_pago_acumulado = Decimal('0.00')
        titulos_baixados_ids = []

        # Suporte a Baixa Parcial e Quitação Integral
        valor_receber_param = dados.get('valor_receber')
        if valor_receber_param is not None and str(valor_receber_param).strip() != '':
            valor_disponivel = Decimal(str(valor_receber_param))
        else:
            valor_disponivel = sum(t.valor_saldo for t in titulos)

        if valor_disponivel <= Decimal('0.00'):
            return JsonResponse({'sucesso': False, 'erro': 'Informe um valor maior que zero para recebimento.'}, status=400)

        # Ordena títulos por vencimento e parcela para abater prioritariamente os mais antigos
        titulos_ordenados = titulos.order_by('data_vencimento', 'parcela', 'pk_chave')

        for tit in titulos_ordenados:
            if valor_disponivel <= Decimal('0.00'):
                break

            saldo_atual = tit.valor_saldo
            abatimento = min(saldo_atual, valor_disponivel)

            tit.valor_pago = (tit.valor_pago or Decimal('0.00')) + abatimento
            novo_saldo = max(Decimal('0.00'), saldo_atual - abatimento)
            tit.valor_saldo = novo_saldo

            if novo_saldo <= Decimal('0.005'):
                tit.valor_saldo = Decimal('0.00')
                tit.situacao = 'PAGO'
            else:
                tit.situacao = 'PARCIAL'

            tit.data_pagamento = data_pagamento
            if tipo_pagamento:
                tit.tipo_pagamento = tipo_pagamento
            tit.save()

            total_pago_acumulado += abatimento
            valor_disponivel -= abatimento
            titulos_baixados_ids.append(tit.pk_chave)

        # Lança no Caixa aberto do operador se configurado
        caixa = Caixa.objects.filter(usuario=request.user, aberto=True).first() if lancar_caixa else None
        if caixa and total_pago_acumulado > 0:
            tp_caixa = tipo_pagamento or TipoPagamento.objects.filter(tipo_pagamento__icontains='DINHEIRO').first()
            if not tp_caixa:
                tp_caixa = TipoPagamento.objects.first()

            docs_str = ", ".join([f"{t.numero_documento} ({t.parcela}/{t.total_parcelas})" for t in titulos[:4]])
            MovimentacaoCaixa.objects.create(
                caixa=caixa,
                tipo_operacao='E',
                valor=total_pago_acumulado,
                tipo_pagamento=tp_caixa,
                titulo_financeiro=titulos[0] if len(titulos) == 1 else None,
                historico=f"Recebimento Crediário - {cliente.nome} ({docs_str})"[:250]
            )

        ids_param = ",".join(str(i) for i in titulos_baixados_ids)
        recibo_url = f"/cadastros/financeiro/recibo-crediario/?ids={ids_param}&total={total_pago_acumulado}"

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'{len(titulos)} parcela(s) quitada(s) com sucesso! Total: R$ {total_pago_acumulado:,.2f}',
            'total_pago': float(total_pago_acumulado),
            'recibo_url': recibo_url,
            'titulos_ids': titulos_baixados_ids
        })

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=400)


@login_required
def imprimir_recibo_crediario(request):
    """
    Renderiza o comprovante / recibo de quitação de crediário pronto para impressão
    (compatível com impressora térmica de 80mm e impressora padrão A4).
    """
    ids_str = request.GET.get('ids', '')
    if not ids_str:
        messages.error(request, 'Nenhum título informado para emissão de recibo.')
        return redirect('cadastros:recebimento_crediario')

    ids = [int(i.strip()) for i in ids_str.split(',') if i.strip().isdigit()]
    titulos = TituloFinanceiro.objects.filter(pk_chave__in=ids).select_related('pessoa', 'tipo_pagamento')
    if not titulos.exists():
        messages.error(request, 'Títulos não encontrados.')
        return redirect('cadastros:recebimento_crediario')

    cliente = titulos.first().pessoa
    empresa = Empresa.objects.first()

    total_param = request.GET.get('total')
    if total_param:
        try:
            total_pago = Decimal(str(total_param))
        except Exception:
            total_pago = sum(t.valor_pago for t in titulos)
    else:
        total_pago = sum(t.valor_pago for t in titulos)
    
    # Saldo devedor restante do cliente (quantas parcelas ainda faltam pagar no crediário)
    parcelas_restantes = TituloFinanceiro.objects.filter(
        tipo='R',
        pessoa=cliente,
        situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']
    ).count()

    saldo_devedor_restante = TituloFinanceiro.objects.filter(
        tipo='R',
        pessoa=cliente,
        situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']
    ).aggregate(Sum('valor_saldo'))['valor_saldo__sum'] or Decimal('0.00')

    context = {
        'titulos': titulos,
        'cliente': cliente,
        'empresa': empresa,
        'total_pago': total_pago,
        'parcelas_restantes': parcelas_restantes,
        'saldo_devedor_restante': saldo_devedor_restante,
        'forma_pagamento': titulos.first().tipo_pagamento,
        'data_hora': datetime.now(),
        'operador': request.user,
    }
    return render(request, 'cadastros/financeiro/recibo_crediario.html', context)
