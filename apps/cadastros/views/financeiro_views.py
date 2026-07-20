from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from apps.cadastros.models import (
    TituloFinanceiro, Caixa, MovimentacaoCaixa, 
    Pessoa, TipoPagamento, PlanoContas, CentroCusto, Empresa
)

def caixa_status(request):
    """Verifica se há caixa aberto para o usuário e retorna dados consolidados."""
    if not request.user.is_authenticated:
        return JsonResponse({'aberto': False, 'caixa_aberto': False, 'erro': 'Não autenticado'})
    from django.db.models import Sum
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
                'tipo_pgto_nome': m.tipo_pagamento.tipo_pagamento,
                'tipo_pgto_id': m.tipo_pagamento.pk_tipo_pagamento,
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
        tipo = dados.get('tipo') # 'E' para Suprimento, 'S' para Sangria
        valor = Decimal(str(dados.get('valor', 0)))
        historico = dados.get('historico')
        
        # Tipo de pagamento padrão DINHEIRO para sangria/suprimento
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
        
        # Verificar se já tem um aberto
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
def listar_titulos(request, tipo='P'):
    """Lista títulos a pagar (P) ou a receber (R)."""
    titulos = TituloFinanceiro.objects.filter(tipo=tipo).select_related('pessoa', 'tipo_pagamento').order_by('data_vencimento')
    
    # Listas para o modal de inclusão manual
    tipos_pagamento = TipoPagamento.objects.filter(ativo=True)
    tipo_pc = 'D' if tipo == 'P' else 'R'
    planos_contas = PlanoContas.objects.filter(tipo_conta__in=[tipo_pc, 'A'])
    centros_custo = CentroCusto.objects.all()
    
    # Totais para o dashboard da tela
    from django.db.models import Sum
    total_aberto = titulos.filter(situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).aggregate(Sum('valor_saldo'))['valor_saldo__sum'] or 0
    vence_hoje = titulos.filter(data_vencimento=date.today(), situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL']).aggregate(Sum('valor_saldo'))['valor_saldo__sum'] or 0

    template = 'cadastros/financeiro/contas_pagar.html' if tipo == 'P' else 'cadastros/financeiro/contas_receber.html'
    
    return render(request, template, {
        'titulos': titulos,
        'tipo': tipo,
        'tipos_pagamento': tipos_pagamento,
        'planos_contas': planos_contas,
        'centros_custo': centros_custo,
        'total_aberto': f"{total_aberto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'vence_hoje': f"{vence_hoje:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'today': date.today()
    })

@login_required
@transaction.atomic
def salvar_titulo_manual(request):
    """Salva título financeiro manual (com suporte a parcelas/carnê)."""
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            
            tipo = dados.get('tipo', 'P')
            pessoa_id = dados.get('pessoa_id')
            data_vencimento_base = datetime.strptime(dados.get('data_vencimento'), '%Y-%m-%d').date()
            valor_total = Decimal(str(dados.get('valor_total', 0)))
            num_parcelas = int(dados.get('parcelas', 1))
            
            valor_parcela = round(valor_total / num_parcelas, 2)
            
            empresa = Empresa.objects.first()
            
            for i in range(1, num_parcelas + 1):
                if i == num_parcelas:
                    valor_parcela = round(valor_total - (valor_parcela * (num_parcelas - 1)), 2)
                
                # Calcular vencimento (mensal)
                venc = data_vencimento_base
                if i > 1:
                    # Adiciona meses de forma simples
                    ano = data_vencimento_base.year + (data_vencimento_base.month + i - 2) // 12
                    mes = (data_vencimento_base.month + i - 2) % 12 + 1
                    dia = min(data_vencimento_base.day, 28) # Simplificação para evitar erro de dia inexistente
                    venc = date(ano, mes, dia)
                
                TituloFinanceiro.objects.create(
                    tipo=tipo,
                    pessoa_id=pessoa_id,
                    data_vencimento=venc,
                    numero_documento=dados.get('numero_documento'),
                    parcela=i,
                    total_parcelas=num_parcelas,
                    valor_documento=valor_parcela,
                    valor_saldo=valor_parcela,
                    situacao='ABERTO',
                    tipo_pagamento_id=dados.get('tipo_pagamento_id'),
                    plano_contas_id=dados.get('plano_contas_id'),
                    centro_custo_id=dados.get('centro_custo_id'),
                    usuario_criacao=request.user
                )
            
            return JsonResponse({'sucesso': True, 'mensagem': f'{num_parcelas} parcelas geradas com sucesso!'})
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=400)
    return JsonResponse({'erro': 'Método inválido'}, status=400)

@login_required
def caixa_controle(request):
    """Tela de controle de caixa."""
    return render(request, 'cadastros/financeiro/caixa.html')
