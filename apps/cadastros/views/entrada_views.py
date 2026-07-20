"""Views de Entrada de Nota Fiscal."""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db import transaction, connection
from django.db.models import Q
from decimal import Decimal
import json
from datetime import datetime
from django.contrib import messages
from django.db.models import Value, Func
# Importações de Cadastros
from apps.cadastros.models import Pessoa, Produto, Marca, Divisao, Unidade, Empresa, TituloFinanceiro, TipoPagamento
from apps.cadastros.models.produto import LocalEstoque, CodigoBarras, SaldoEstoque
from apps.cadastros.models.reservados import CFOP, NCM

# Importações de Estoque (Ajuste os caminhos se os seus models de estoque estiverem em outro lugar)
from apps.estoque.models import MovimentacaoEstoque, ItemMovimentacaoEstoque

# Parser do XML
from .nfe_parser import NFEParser


def entrada_nf(request):
    """Tela de entrada manual de NF."""
    fornecedores = Pessoa.objects.filter(fornecedor=True, inativo=False).order_by('nome')[:100]
    locais = list(LocalEstoque.objects.values_list('local', flat=True).order_by('local'))
    marcas = list(Marca.objects.values_list('nome', flat=True).order_by('nome'))
    divisoes = list(Divisao.objects.values_list('nome', flat=True).order_by('nome'))
    unidades = list(Unidade.objects.values_list('nome', flat=True).order_by('nome'))
    
    cfops_query = CFOP.objects.filter(Q(cfop__startswith='1') | Q(cfop__startswith='2')).order_by('cfop')
    cfops = [{'cfop': c.cfop, 'descricao': c.descricao} for c in cfops_query]
    
    # Para o TipoDocumento, como não tenho o local exato do seu model, estou simulando. 
    # Se você tiver um Model TipoDocumento, use TipoDocumento.objects.values_list(...)
    tipos_doc = ['NFE', 'NFCE', 'RECIBO'] 

    return render(request, 'cadastros/entradas/entrada_nf.html', {
        'fornecedores': fornecedores,
        'locais': locais,
        'tipos_doc': tipos_doc,
        'cfops': cfops,
        'marcas': marcas,
        'divisoes': divisoes,
        'unidades': unidades
    })


def upload_xml_nfe(request):
    """API: Upload e parse de XML da NFe."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    
    try:
        if 'xml_file' not in request.FILES:
            return JsonResponse({'erro': 'Nenhum arquivo enviado'}, status=400)
        
        xml_file = request.FILES['xml_file']
        
        # Ler conteúdo do XML
        try:
            xml_content = xml_file.read()
            if isinstance(xml_content, bytes):
                try:
                    xml_content = xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    xml_content = xml_content.decode('latin1')
        except Exception as e:
            return JsonResponse({'erro': f'Erro ao ler arquivo: {str(e)}'}, status=400)
        
        # Importar seu parser
        from .nfe_parser import NFEParser
        import re
        
        # Fazer parse usando o método correto que você criou!
        parser = NFEParser(xml_content)
        dados = parser.extrair_dados_nfe()
        
        chave_nfe = dados.get('chave_nfe')
        
        # ===== VALIDAR SE NOTA JÁ FOI LANÇADA =====
        if chave_nfe:
            nota_existente = MovimentacaoEstoque.objects.filter(chave_nfe=chave_nfe).first()
            if nota_existente:
                return JsonResponse({
                    'erro': f'Esta nota já foi lançada no sistema! (Movimentação #{nota_existente.pk})'
                }, status=400)
        
        # ===== PROCESSAR FORNECEDOR =====
        cnpj_bruto = dados['fornecedor']['cnpj']
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj_bruto) if cnpj_bruto else ''
        
        fornecedor = None
        fornecedor_criado = False
        
        if cnpj_limpo:
            fornecedor = (
                Pessoa.objects.annotate(
                    cpf_cnpj_digits=Func(
                        'cpf_cnpj', Value('[^0-9]'), Value(''), Value('g'),
                        function='regexp_replace'
                    )
                ).filter(
                    cpf_cnpj_digits=Value(cnpj_limpo),
                    fornecedor=True
                ).first()
            )
            
            if not fornecedor:
                fornecedor = Pessoa.objects.create(
                    nome=dados['fornecedor']['nome'][:100],
                    cpf_cnpj=cnpj_limpo,
                    fornecedor=True,
                    inativo=False
                )
                fornecedor_criado = True
        
        if not fornecedor:
            return JsonResponse({'erro': 'Erro ao processar fornecedor do XML'}, status=400)
        
        v_total_nf = float(dados['totais']['total_nf'])
        # Preparar a estrutura de resposta que o seu frontend (Alpine.js) espera
        response = {
            'sucesso': True,
            'dados_nf': {
                'fornecedor_id': fornecedor.pk,
                'chave_nfe': chave_nfe,
                'numero_nf': dados['numero_nf'],
                'serie_nf': dados['serie_nf'],
                'data_emissao': str(dados['data_emissao']),
                'tipo_documento': dados['tipo_documento'],
                'valor_total_nf': v_total_nf,
                'vr_nf': v_total_nf,
                'vr_total_nf': v_total_nf
            },
            'fornecedor': {
                'chave': fornecedor.pk,
                'nome': fornecedor.nome,
                'cnpj': cnpj_bruto,
                'criado_automaticamente': fornecedor_criado
            },
            'totais': {
                'total_produtos': float(dados['totais']['total_produtos']),
                'total_desconto': float(dados['totais']['total_desconto']),
                'total_frete': float(dados['totais']['total_frete']),
                'total_ipi': float(dados['totais']['total_ipi']),
                'total_icms_st': float(dados['totais']['total_icms_st']),
                'total_nf': float(dados['totais']['total_nf']),
            },
            'pagamentos': [
                {
                    'numero': p.get('numero', ''),
                    'vencimento': str(p.get('vencimento', '')),
                    'valor': float(p.get('valor', 0))
                } for p in dados.get('pagamentos', [])
            ],
            'produtos_encontrados': [],
            'produtos_nao_encontrados': []
        }
        
        # ===== PROCESSAR ITENS (100% ORM do Django) =====
        for item_nfe in dados['itens']:
            produto_obj = None
            codigo_fornecedor = item_nfe.get('codigo_produto', '')
            cean = item_nfe.get('ean', '')
            nome_xml = item_nfe.get('nome_produto', '')
            
            # 1. Tenta buscar pelo Código de Barras (EAN/GTIN)
            if cean and cean != 'SEM GTIN':
                codigo_barras = CodigoBarras.objects.filter(codigo_barras=cean).select_related('produto').first()
                if codigo_barras:
                    p = codigo_barras.produto
                    produto_obj = {
                        'id': p.pk_chave, 
                        'nome': p.nome, 
                        'preco_venda': float(p.preco_venda), 
                        'custo_referencia': float(p.custo_referencia)
                    }
            
            # 2. Tenta buscar pela Referência de Fábrica (se não achou por EAN)
            if not produto_obj and codigo_fornecedor:
                p = Produto.objects.filter(referencia_fabrica=codigo_fornecedor).first()
                if p:
                    produto_obj = {
                        'id': p.pk_chave, 
                        'nome': p.nome, 
                        'preco_venda': float(p.preco_venda), 
                        'custo_referencia': float(p.custo_referencia)
                    }

            # 3. Tenta buscar pelo Nome Exato (última tentativa)
            if not produto_obj and nome_xml:
                p = Produto.objects.filter(nome__iexact=nome_xml).first()
                if p:
                    produto_obj = {
                        'id': p.pk_chave, 
                        'nome': p.nome, 
                        'preco_venda': float(p.preco_venda), 
                        'custo_referencia': float(p.custo_referencia)
                    }
            
            
            # Pega o valor independentemente de como o Parser do XML o chamou
            v_unitario = float(item_nfe.get('valor_unitario', 0) or item_nfe.get('vr_unitario', 0) or 0)
            v_total = float(item_nfe.get('valor_total', 0) or item_nfe.get('vr_total', 0) or 0)
            v_desc = float(item_nfe.get('valor_desconto', 0) or item_nfe.get('vr_desconto', 0) or 0)
            v_frete = float(item_nfe.get('valor_frete', 0) or item_nfe.get('vr_frete', 0) or 0)

            # Montar a linha do item para enviar ao frontend
            item_dados = {
                'numero_item': item_nfe.get('numero_item', ''),
                'codigo_fornecedor': codigo_fornecedor,
                'produto_id': produto_obj['id'] if produto_obj else None,
                'produto_nome_xml': nome_xml,
                'produto_nome_sistema': produto_obj['nome'] if produto_obj else None,
                'ean': cean,
                'ncm': item_nfe.get('ncm', ''),
                'cfop': item_nfe.get('cfop', ''),
                'unidade': item_nfe.get('unidade', ''),
                'quantidade': float(item_nfe.get('quantidade', 0)),
                
                # =======================================================
                # TRUQUE DE MESTRE: Mandamos os dois nomes para blindar o JS!
                # =======================================================
                'valor_unitario': v_unitario,
                'vr_unitario': v_unitario,
                
                'valor_total': v_total,
                'vr_total': v_total,
                
                'valor_desconto': v_desc,
                'vr_desconto': v_desc,
                
                'valor_frete': v_frete,
                'vr_frete': v_frete,
                # =======================================================
                
                'valor_seguro': float(item_nfe.get('valor_seguro', 0)),
                'valor_outras': float(item_nfe.get('valor_outras', 0)),
                
                'cest': item_nfe.get('cest', ''),
                'cst_icms': item_nfe.get('cst_icms', ''),
                'orig_icms': item_nfe.get('orig_icms', '0'),
                'bc_icms': float(item_nfe.get('bc_icms', 0)),
                'aliq_icms': float(item_nfe.get('aliq_icms', 0)),
                'valor_icms': float(item_nfe.get('valor_icms', 0)),
                'reducao_bc_icms': float(item_nfe.get('reducao_bc_icms', 0)),
                'bc_icms_st': float(item_nfe.get('bc_icms_st', 0)),
                'aliq_icms_st': float(item_nfe.get('aliq_icms_st', 0)),
                'valor_icms_st': float(item_nfe.get('valor_icms_st', 0)),
                'aliq_mva': float(item_nfe.get('aliq_mva', 0)),
                'reducao_bc_icms_st': float(item_nfe.get('reducao_bc_icms_st', 0)),
                'cst_ipi': item_nfe.get('cst_ipi', ''),
                'bc_ipi': float(item_nfe.get('bc_ipi', 0)),
                'aliq_ipi': float(item_nfe.get('aliq_ipi', 0)),
                'valor_ipi': float(item_nfe.get('valor_ipi', 0)),
                'cst_pis': item_nfe.get('cst_pis', ''),
                'bc_pis': float(item_nfe.get('bc_pis', 0)),
                'aliq_pis': float(item_nfe.get('aliq_pis', 0)),
                'valor_pis': float(item_nfe.get('valor_pis', 0)),
                'cst_cofins': item_nfe.get('cst_cofins', ''),
                'bc_cofins': float(item_nfe.get('bc_cofins', 0)),
                'aliq_cofins': float(item_nfe.get('aliq_cofins', 0)),
                'valor_cofins': float(item_nfe.get('valor_cofins', 0)),
            }
            
            if produto_obj:
                response['produtos_encontrados'].append(item_dados)
            else:
                response['produtos_nao_encontrados'].append(item_dados)
                
        return JsonResponse(response)
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)


@transaction.atomic
def cadastrar_produtos_xml(request):
    """API: Cadastrar produtos que não foram encontrados no XML."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
        
    try:
        dados = json.loads(request.body)
        produtos_novos = dados.get('produtos', [])
        
        if not produtos_novos:
            return JsonResponse({'erro': 'Nenhum produto enviado'}, status=400)
            
        resultados = []
        
        for prod_data in produtos_novos:
            # 1. Tratar Unidade (Se vier vazio, assume 'UN')
            unidade_str = prod_data.get('unidade') or 'UN'
            unidade_obj, _ = Unidade.objects.get_or_create(nome=unidade_str[:50])
            
            # 2. Tratar NCM (Se vier vazio, assume um NCM genérico)
            ncm_str = prod_data.get('ncm') or '00000000'
            ncm_str = ncm_str.replace('.', '') # Limpa pontos do NCM caso venham no XML
            ncm_obj, _ = NCM.objects.get_or_create(ncm=ncm_str)
            
            # 3. Tratar Marca (Se vier vazio, assume 'DIVERSOS')
            marca_str = prod_data.get('marca') or 'DIVERSOS'
            marca_obj, _ = Marca.objects.get_or_create(nome=marca_str[:100])
            
            # 4. Tratar Divisão (Se vier vazio, assume 'GERAL')
            divisao_str = prod_data.get('divisao') or 'GERAL'
            divisao_obj, _ = Divisao.objects.get_or_create(nome=divisao_str[:100])
            
            # Pega o valor independentemente de como o JS enviou!
            valor_unit = prod_data.get('valor_unitario') or prod_data.get('vr_unitario') or 0
            valor_venda = prod_data.get('preco_venda') or prod_data.get('vr_venda') or 0
            
            novo_produto = Produto.objects.create(
                nome=prod_data.get('nome')[:255],
                ncm=ncm_obj,
                cest=prod_data.get('cest', '')[:7],
                unidade_venda=unidade_obj,
                marca=marca_obj,
                divisao=divisao_obj,
                custo_referencia=Decimal(str(valor_unit)), 
                preco_venda=Decimal(str(valor_venda)),     
                tipo_produto='PRODUTO ACABADO',
                inativo=False
            )
            
            # Cadastra o Código de Barras se existir
            cean = prod_data.get('cean')
            if cean and cean != 'SEM GTIN':
                CodigoBarras.objects.get_or_create(produto=novo_produto, codigo_barras=cean[:13])
                
            resultados.append({
                'numero_item': prod_data.get('numero_item'),
                'produto_id': novo_produto.pk_chave,
                'nome': novo_produto.nome
            })
            
        return JsonResponse({
            'sucesso': True,
            'mensagem': f'{len(resultados)} produtos cadastrados com sucesso!',
            'produtos': resultados
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)

@transaction.atomic
def finalizar_entrada_nf(request):
    """API: Finaliza a entrada gravando na base de dados e atualizando estoques/custos."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
        
    try:
        dados = json.loads(request.body)
        itens = dados.get('itens', [])
        
        if not itens:
            return JsonResponse({'erro': 'Nenhum item para guardar'}, status=400)
            
        # =============================================================
        # 1. BUSCA EXTREMAMENTE INTELIGENTE (Cobre todos os cenários do JS)
        # =============================================================
        raiz = dados.get('dados_nf') or dados.get('cabecalho') or dados
        
        fornecedor_id = raiz.get('fornecedor_id') or dados.get('fornecedor_id') or dados.get('fornecedor')
        if not fornecedor_id:
            return JsonResponse({'erro': 'O ID do fornecedor não foi recebido.'}, status=400)
            
        pessoa = get_object_or_404(Pessoa, pk=fornecedor_id)
        
        nome_local = raiz.get('local_id') or raiz.get('local') or dados.get('local_id')
        local = LocalEstoque.objects.filter(local=nome_local).first() if nome_local else None
        if not local:
            local = LocalEstoque.objects.first()
        if not local:
            return JsonResponse({'erro': 'Nenhum Local de Estoque cadastrado.'}, status=400)
        
        # Puxando os dados reais com os nomes exatos do seu JS antigo:
        vr_nf_total = raiz.get('valor_total_nf') or raiz.get('vr_total_nf') or dados.get('valor_total_nf') or 0
        nro_doc = raiz.get('numero_nf') or raiz.get('nro_nf') or dados.get('numero_nf') or ''
        serie_doc = raiz.get('serie_nf') or dados.get('serie_nf') or ''
        chave = raiz.get('chave_nfe') or raiz.get('chave_nf') or dados.get('chave_nfe') or ''
        data_doc = raiz.get('data_emissao') or dados.get('data_emissao') or datetime.now().date()
        
        # O CFOP geralmente vem nos itens, então pegamos do primeiro item se o cabeçalho não tiver
        cfop_doc = raiz.get('cfop') or dados.get('cfop') or (itens[0].get('cfop') if itens else '')
        
        # =============================================================
        # 2. GRAVANDO O CABEÇALHO DA MOVIMENTAÇÃO
        # =============================================================
        movimentacao = MovimentacaoEstoque.objects.create(
            tipo_movimento='E',
            data=data_doc,
            nro_documento=nro_doc,
            serie=serie_doc,
            pessoa=pessoa,
            local=local,
            vr_total_bruto=Decimal(str(vr_nf_total)),
            vr_total_liquido=Decimal(str(vr_nf_total)),
            observacao=f"Entrada via XML chave {chave}",
            cfop=cfop_doc,
            chave_nfe=chave
        )
        
        # =============================================================
        # 3. GRAVANDO OS ITENS
        # =============================================================
        for item in itens:
            produto_id = item.get('produto_id')
            if not produto_id:
                continue
                
            produto = Produto.objects.get(pk_chave=produto_id)
            qtd = Decimal(str(item.get('quantidade', 0)))
            
            vr_unitario = Decimal(str(item.get('valor_unitario') or item.get('vr_unitario') or 0))
            vr_total = Decimal(str(item.get('valor_total') or item.get('vr_total') or 0))
            preco_venda = Decimal(str(item.get('preco_venda') or item.get('vr_venda') or 0))
            
            ItemMovimentacaoEstoque.objects.create(
                movimentacao=movimentacao,
                produto=produto,
                local=local,
                quantidade=qtd,
                vr_unitario_bruto=vr_unitario,
                vr_unitario_liquido=vr_unitario,
                vr_total_bruto=vr_total,
                vr_total_liquido=vr_total
            )
            
            # Atualiza os custos no Produto
            if vr_unitario > 0 or preco_venda > 0:
                produto.custo_referencia = vr_unitario
                if preco_venda > 0:
                    produto.preco_venda = preco_venda
                produto.save(update_fields=['custo_referencia', 'preco_venda'])
            
            saldo, created = SaldoEstoque.objects.get_or_create(
                produto=produto,
                local=local,
                defaults={'quantidade': 0}
            )
            # Soma a quantidade que acabou de entrar na nota fiscal
            saldo.quantidade += qtd
            saldo.save()
            
        # =============================================================
        # 4. GERANDO O FINANCEIRO (CONTAS A PAGAR)
        # =============================================================
        pagamentos = dados.get('pagamentos', [])
        empresa = Empresa.objects.first()
        
        if pagamentos:
            tipo_boleto = TipoPagamento.objects.filter(tipo_pagamento__icontains='BOLETO').first() or \
                          TipoPagamento.objects.filter(tipo_pagamento__icontains='DUPLICATA').first()
            
            for i, pag in enumerate(pagamentos, 1):
                venc = pag.get('vencimento')
                if isinstance(venc, str) and venc:
                    try:
                        venc = datetime.strptime(venc, '%Y-%m-%d').date()
                    except:
                        venc = datetime.now().date()
                
                TituloFinanceiro.objects.create(
                    tipo='P', # A Pagar
                    pessoa=pessoa,
                    data_vencimento=venc,
                    numero_documento=pag.get('numero') or f"{nro_doc}/{i}",
                    parcela=i,
                    total_parcelas=len(pagamentos),
                    valor_documento=Decimal(str(pag.get('valor', 0))),
                    valor_saldo=Decimal(str(pag.get('valor', 0))),
                    situacao='ABERTO',
                    tipo_pagamento=tipo_boleto,
                    plano_contas=empresa.plano_contas_receita_compra if empresa else None,
                    centro_custo=empresa.centro_custo_compra if empresa else None,
                    movimentacao_estoque=movimentacao,
                    usuario_criacao=request.user if request.user.is_authenticated else None
                )
                
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Entrada gravada com sucesso!',
            'id_movimentacao': movimentacao.pk
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)

def listar_entradas(request):
    """Lista as entradas lançadas."""
   
    entradas = MovimentacaoEstoque.objects.filter(
        tipo_movimento='E'
    ).select_related('pessoa').order_by('-data', '-pk_chave')
    
    return render(request, 'cadastros/entradas/list_entrada.html', {'entradas': entradas})


def detalhe_entrada(request, pk):
    """Exibe detalhes de uma entrada."""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo_movimento='E')
    # O related_name no ForeignKey do ItemMovimentacaoEstoque precisa ser 'itens' (ou ajuste abaixo)
    itens = movimentacao.itens.all().select_related('produto')
    
    return render(request, 'cadastros/entradas/detalhe.html', {
        'entrada': movimentacao,
        'itens': itens
    })

def buscar_produto_entrada(request):
    """Busca produtos para a tabela manual (caso use)."""
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse({'produtos': []})
        
    produtos = Produto.objects.filter(Q(nome__icontains=q) | Q(pk_chave__icontains=q))[:20]
    dados = [{'id': p.pk_chave, 'nome': p.nome, 'preco': str(p.custo_referencia)} for p in produtos]
    return JsonResponse({'produtos': dados})

@transaction.atomic
def editar_entrada(request, pk):
    """Tela de edição de uma entrada existente."""
    # 1. Busca a Movimentação (Cabeçalho)
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo_movimento='E')
    
    # 2. Busca os itens relacionados a esta entrada
    # Nota: Assumo que o ForeignKey no ItemMovimentacaoEstoque usa related_name='itens'
    itens_obj = movimentacao.itens.all().select_related('produto')
    
    # Prepara os itens no formato JSON que o Alpine.js e o frontend esperam (como se tivessem vindo do XML)
    itens_json = []
    for item in itens_obj:
        v_unit = float(item.vr_unitario_bruto)
        v_tot = float(item.vr_total_bruto)
        
        itens_json.append({
            'produto_id': item.produto.pk_chave if item.produto else None,
            
            
            'produto_nome_sistema': item.produto.nome if item.produto else '',
            'produto_nome_xml': item.produto.nome if item.produto else '',
            'quantidade': float(item.quantidade),
            
            # TRUQUE DO ESPELHO NOS ITENS PARA A EDIÇÃO
            'vr_unitario': v_unit,
            'valor_unitario': v_unit,
            'vr_total': v_tot,
            'valor_total': v_tot,
            
            'cfop': movimentacao.cfop if movimentacao.cfop else '',
            'status_vinculo': 'vinculado' if item.produto else 'nao_encontrado'
        })

    # 3. Carrega os mesmos auxiliares que a tela de Nova Entrada usa para os selects
    fornecedores = Pessoa.objects.filter(fornecedor=True, inativo=False).order_by('nome')[:100]
    locais = list(LocalEstoque.objects.values_list('local', flat=True).order_by('local'))
    marcas = list(Marca.objects.values_list('nome', flat=True).order_by('nome'))
    divisoes = list(Divisao.objects.values_list('nome', flat=True).order_by('nome'))
    unidades = list(Unidade.objects.values_list('nome', flat=True).order_by('nome'))
    
    cfops_query = CFOP.objects.filter(Q(cfop__startswith='1') | Q(cfop__startswith='2')).order_by('cfop')
    cfops = [{'cfop': c.cfop, 'descricao': c.descricao} for c in cfops_query]
    
    tipos_doc = ['NFE', 'NFCE', 'RECIBO']

    return render(request, 'cadastros/entradas/entrada_nf.html', {
        'entrada': movimentacao, # Passa os dados do cabeçalho
        'itens_json': json.dumps(itens_json), # Passa os itens para o JavaScript
        'fornecedores': fornecedores,
        'locais': locais,
        'tipos_doc': tipos_doc,
        'cfops': cfops,
        'marcas': marcas,
        'divisoes': divisoes,
        'unidades': unidades,
        'modo_edicao': True # Flag para o template saber que é edição e mudar o botão/URL de salvar
    })


@transaction.atomic
def atualizar_entrada(request, pk):
    """API: Recebe os dados alterados, apaga os itens antigos e salva os novos, recalculando estoques."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
        
    try:
        dados = json.loads(request.body)
        
        # BUSCA INTELIGENTE: Pega os dados do JS independentemente do nível onde estejam agrupados
        cabecalho = dados.get('cabecalho') or dados.get('dados_nf') or dados
        itens = dados.get('itens', [])
        
        if not itens:
            return JsonResponse({'erro': 'Uma entrada precisa ter pelo menos 1 item'}, status=400)
            
        # 1. Recupera a movimentação existente
        movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo_movimento='E')
        
        # Trata o Fornecedor
        fornecedor_id = cabecalho.get('fornecedor_id') or dados.get('fornecedor_id')
        pessoa = get_object_or_404(Pessoa, pk=fornecedor_id)
        
        # Trata o Local de Estoque
        nome_local = cabecalho.get('local_id') or cabecalho.get('local') or dados.get('local_id')
        local = LocalEstoque.objects.filter(local=nome_local).first() if nome_local else None
        if not local:
            local = LocalEstoque.objects.first()

        # 2. Atualiza os dados do Cabeçalho com os nomes corretos do Model
        movimentacao.data = cabecalho.get('data_emissao') or cabecalho.get('data') or movimentacao.data
        movimentacao.nro_documento = cabecalho.get('nro_nf') or cabecalho.get('numero_nf') or movimentacao.nro_documento
        movimentacao.serie = cabecalho.get('serie_nf', movimentacao.serie)
        movimentacao.pessoa = pessoa
        movimentacao.local = local
        
        vr_nf = cabecalho.get('vr_nf') or cabecalho.get('valor_total_nf') or movimentacao.vr_total_bruto
        movimentacao.vr_total_bruto = Decimal(str(vr_nf))
        movimentacao.vr_total_liquido = Decimal(str(vr_nf))
        
        movimentacao.cfop = cabecalho.get('cfop', movimentacao.cfop)
        movimentacao.chave_nfe = cabecalho.get('chave_nf') or cabecalho.get('chave_nfe') or movimentacao.chave_nfe
        movimentacao.observacao = cabecalho.get('observacao', movimentacao.observacao)
        movimentacao.save()
        
        # =================================================================
        # 3. ESTORNA O ESTOQUE DOS ITENS ANTIGOS ANTES DE DELETAR
        # =================================================================
        for item_antigo in movimentacao.itens.all():
            if item_antigo.produto and item_antigo.local:
                saldo = SaldoEstoque.objects.filter(produto=item_antigo.produto, local=item_antigo.local).first()
                if saldo:
                    saldo.quantidade -= item_antigo.quantidade
                    saldo.save()
                    
        # 4. Limpa os itens antigos
        movimentacao.itens.all().delete()
        
        # =================================================================
        # 5. RECRIAR ITENS E SOMAR NOVO ESTOQUE
        # =================================================================
        for item in itens:
            produto_id = item.get('produto_id')
            if not produto_id:
                continue
                
            produto = Produto.objects.get(pk_chave=produto_id)
            qtd = Decimal(str(item.get('quantidade', 0)))
            
            # Pega o valor independentemente do nome enviado pelo JS
            vr_unitario = Decimal(str(item.get('valor_unitario') or item.get('vr_unitario') or 0))
            vr_total = Decimal(str(item.get('valor_total') or item.get('vr_total') or 0))
            preco_venda = Decimal(str(item.get('preco_venda') or item.get('vr_venda') or 0))
            
            # Criando o item com as colunas EXATAS da sua tabela
            ItemMovimentacaoEstoque.objects.create(
                movimentacao=movimentacao,
                produto=produto,
                local=local, # Obrigatorio no seu item
                quantidade=qtd,
                vr_unitario_bruto=vr_unitario,
                vr_unitario_liquido=vr_unitario,
                vr_total_bruto=vr_total,
                vr_total_liquido=vr_total
                # O CFOP foi removido do item no model, fica so no cabecalho
            )
            
            # Re-atualiza os custos
            if vr_unitario > 0 or preco_venda > 0:
                produto.custo_referencia = vr_unitario
                if preco_venda > 0:
                    produto.preco_venda = preco_venda
                produto.save(update_fields=['custo_referencia', 'preco_venda'])
                
            # SOMAR ESTOQUE DA EDIÇÃO
            saldo, created = SaldoEstoque.objects.get_or_create(
                produto=produto,
                local=local,
                defaults={'quantidade': 0}
            )
            saldo.quantidade += qtd
            saldo.save()
                
        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Entrada #{movimentacao.nro_documento} atualizada com sucesso!'
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=500)

@transaction.atomic
def excluir_entrada(request, pk):
    """Exclui a nota fiscal de entrada e estorna o saldo do estoque."""
    if request.method == 'POST':
        try:
            movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo_movimento='E')
            numero_doc = movimentacao.nro_documento
            
            # 1. Estornar (subtrair) o saldo do estoque para cada item
            for item in movimentacao.itens.all():
                if item.produto and item.local:
                    saldo = SaldoEstoque.objects.filter(produto=item.produto, local=item.local).first()
                    if saldo:
                        saldo.quantidade -= item.quantidade
                        saldo.save()
            
            # 2. Excluir a nota (Isso apaga os itens automaticamente via CASCADE)
            movimentacao.delete()
            
            # 3. Avisar o usuário
            messages.success(request, f'Entrada NF {numero_doc} excluída e estoque estornado com sucesso!')
            
        except Exception as e:
            messages.error(request, f'Erro ao excluir a entrada: {str(e)}')
            
    # Redireciona de volta para a lista de entradas
    return redirect('cadastros:listar_entradas')