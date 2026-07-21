import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.db import transaction
from datetime import datetime
from django.utils import timezone

from .models import NFe, CertificadoDigital, NFeEvento, NFeItem, NFePagamento
from .services import NFeService
from apps.cadastros.models import MovimentacaoEstoque, Empresa, Pessoa, Produto, TipoPagamento


class NFeListView(LoginRequiredMixin, ListView):
    model = NFe
    template_name = 'fiscal/nfe_list.html'
    context_object_name = 'notas'
    paginate_by = 50

    def get_queryset(self):
        qs = NFe.objects.select_related('destinatario', 'empresa').order_by('-data_emissao')
        status = self.request.GET.get('status')
        modelo = self.request.GET.get('modelo')
        cliente = self.request.GET.get('cliente', '').strip()
        dt_ini = self.request.GET.get('dt_ini', '').strip()
        dt_fim = self.request.GET.get('dt_fim', '').strip()

        if status:
            qs = qs.filter(status=status)
        if modelo:
            qs = qs.filter(modelo=modelo)
        if cliente:
            qs = qs.filter(
                Q(destinatario__nome__icontains=cliente) |
                Q(destinatario__cpf_cnpj__icontains=cliente)
            )
        if dt_ini:
            qs = qs.filter(data_emissao__date__gte=dt_ini)
        if dt_fim:
            qs = qs.filter(data_emissao__date__lte=dt_fim)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['modelo_filter'] = self.request.GET.get('modelo', '')
        context['cliente_filter'] = self.request.GET.get('cliente', '')
        context['dt_ini_filter'] = self.request.GET.get('dt_ini', '')
        context['dt_fim_filter'] = self.request.GET.get('dt_fim', '')
        return context


class NFeDetailView(LoginRequiredMixin, DetailView):
    model = NFe
    template_name = 'fiscal/nfe_detail.html'
    context_object_name = 'nota'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itens'] = self.object.itens.select_related('produto').all()
        context['pagamentos'] = self.object.pagamentos.select_related('tipo_pagamento').all()
        context['eventos'] = self.object.eventos.all()
        from django.conf import settings
        context['debug'] = settings.DEBUG
        return context


@login_required
def nfe_create(request):
    """Tela de criação de NF-e a partir de uma venda."""
    vendas = MovimentacaoEstoque.objects.filter(
        tipo_movimento__in=['VE', 'PV']
    ).select_related('pessoa').order_by('-pk_chave')[:50]

    if request.method == 'POST':
        mov_id = request.POST.get('movimentacao_id')
        if mov_id:
            try:
                nfe = NFeService.criar_nfe_da_venda(int(mov_id), usuario=request.user)
                messages.success(request, f'NF-e #{nfe.numero} criada com sucesso!')
                return redirect('fiscal:nfe_detail', pk=nfe.pk)
            except Exception as e:
                messages.error(request, f'Erro ao criar NF-e: {str(e)}')

    return render(request, 'fiscal/nfe_create.html', {
        'vendas': vendas,
    })


@login_required
@transaction.atomic
def nfe_create_manual(request):
    from decimal import Decimal
    if request.method == 'POST':
        try:
            empresa = Empresa.objects.first()
            if not empresa:
                messages.error(request, 'Nenhuma empresa cadastrada')
                return redirect('fiscal:nfe_list')

            destinatario_id = request.POST.get('destinatario')
            if not destinatario_id:
                messages.error(request, 'Selecione o destinatário')
                return render(request, 'fiscal/nfe_create_manual.html', {
                    'tipos_pagamento': TipoPagamento.objects.filter(ativo=True),
                })

            modelo = request.POST.get('modelo', '55')
            serie = int(request.POST.get('serie', 1))
            natureza = request.POST.get('natureza_operacao', 'VENDA')

            ultima_nfe = NFe.objects.filter(empresa=empresa, modelo=modelo).order_by('-numero').first()
            novo_numero = (ultima_nfe.numero or 0) + 1 if ultima_nfe else 1

            chave = NFeService.gerar_chave_acesso(
                empresa, datetime.now().year, datetime.now().month,
                empresa.pessoa.cpf_cnpj, modelo, serie, novo_numero, 1, '4106902'
            )

            transp_id = request.POST.get('transportadora')
            nfe = NFe.objects.create(
                movimentacao=None,
                empresa=empresa,
                destinatario_id=destinatario_id,
                modelo=modelo,
                serie=serie,
                numero=novo_numero,
                chave_acesso=chave,
                natureza_operacao=natureza,
                finalidade=int(request.POST.get('finalidade', 1)),
                consumo_final=request.POST.get('consumo_final') == 'on',
                presenca_comprador=int(request.POST.get('presenca_comprador', 1)),
                status='DIGITACAO',
                valor_total=0,
                data_emissao=timezone.now(),
                modalidade_frete=int(request.POST.get('modalidade_frete', 9)),
                transportadora_id=int(transp_id) if transp_id and transp_id.isdigit() else None,
                volumes=int(request.POST.get('volumes', 0) or 0),
                especie=request.POST.get('especie', '')[:60],
                peso_bruto=Decimal(str(request.POST.get('peso_bruto', 0) or 0)),
                peso_liquido=Decimal(str(request.POST.get('peso_liquido', 0) or 0)),
            )

            produtos = request.POST.getlist('produto_id')
            quantidades = request.POST.getlist('quantidade')
            valores = request.POST.getlist('valor_unitario')
            cfops = request.POST.getlist('cfop')
            ncms = request.POST.getlist('ncm')
            csts = request.POST.getlist('cst_icms')
            csosns = request.POST.getlist('csosn')
            origens = request.POST.getlist('origem')
            aliq_icms_list = request.POST.getlist('aliquota_icms')

            for i in range(len(produtos)):
                prod = Produto.objects.get(pk=int(produtos[i]))
                qtd = Decimal(str(quantidades[i] if i < len(quantidades) else 1))
                v_unit = Decimal(str(valores[i] if i < len(valores) else 0))
                v_total = qtd * v_unit
                cfop_val = cfops[i] if i < len(cfops) else (prod.cfop_venda_estadual or '5102')
                ncm_val = ncms[i] if i < len(ncms) else (prod.ncm.ncm if prod.ncm else '00000000')
                cst_val = csts[i] if i < len(csts) else (prod.cst_icms or '')
                csosn_val = csosns[i] if i < len(csosns) else ''
                origem_val = origens[i] if i < len(origens) else (prod.origem or '0')
                aliq_val = Decimal(str(aliq_icms_list[i] if i < len(aliq_icms_list) else 0))

                cst_final = cst_val or csosn_val or ''
                base_calc = v_total if cst_final not in ('40', '41', '60', '103', '300', '400', '500') else 0
                valor_icms = v_total * aliq_val / 100 if cst_final not in ('40', '41', '60', '103', '300', '400', '500') else 0

                NFeItem.objects.create(
                    nfe=nfe,
                    produto=prod,
                    numero_item=i + 1,
                    codigo_produto=str(prod.pk_chave),
                    ean='SEM GTIN',
                    nome=prod.nome[:120],
                    ncm=ncm_val,
                    cfop=cfop_val,
                    unidade=prod.unidade_venda.simbolo if prod.unidade_venda else 'UN',
                    quantidade=qtd,
                    valor_unitario=v_unit,
                    valor_total=v_total,
                    cst_icms=cst_final,
                    aliquota_icms=aliq_val,
                    base_calculo_icms=base_calc,
                    valor_icms=valor_icms,
                    origem=origem_val,
                    csosn=csosn_val,
                )

            v_prod = sum(i.valor_total for i in nfe.itens.all())
            nfe.valor_total = v_prod
            nfe.valor_total_produtos = v_prod
            nfe.base_calculo_icms = sum(i.base_calculo_icms for i in nfe.itens.all())
            nfe.valor_icms = sum(i.valor_icms for i in nfe.itens.all())

            tipo_pgto_id = request.POST.get('tipo_pagamento')
            valor_pgto = request.POST.get('valor_pagamento')
            if tipo_pgto_id and valor_pgto:
                NFePagamento.objects.create(
                    nfe=nfe,
                    tipo_pagamento_id=int(tipo_pgto_id),
                    forma_pagamento=1,
                    valor=Decimal(str(valor_pgto)),
                )

            nfe.save(update_fields=[
                'valor_total', 'valor_total_produtos',
                'valor_base_calculo_icms', 'valor_icms',
                'modalidade_frete', 'transportadora_id',
                'volumes', 'especie', 'peso_bruto', 'peso_liquido',
            ])

            xml_bytes = NFeService.gerar_xml_nfe(nfe)
            nfe.xml_enviado = xml_bytes.decode('utf-8')
            nfe.status = 'VALIDADO'
            nfe.save(update_fields=['xml_enviado', 'status'])

            messages.success(request, f'NF-e #{nfe.numero} criada manualmente!')
            return redirect('fiscal:nfe_detail', pk=nfe.pk)

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'Erro: {str(e)}')

    return render(request, 'fiscal/nfe_create_manual.html', {
        'tipos_pagamento': TipoPagamento.objects.filter(ativo=True),
    })


@login_required
def api_buscar_clientes(request):
    term = request.GET.get('q', '').strip()
    pessoas = Pessoa.objects.filter(cliente=True)
    if term:
        pessoas = pessoas.filter(
            Q(nome__icontains=term) | Q(cpf_cnpj__icontains=term)
        )
    pessoas = pessoas.order_by('nome')[:30]
    results = [{'id': p.pk, 'text': f'{p.nome} — {p.cpf_cnpj or "---"}'} for p in pessoas]
    return JsonResponse({'results': results})


@login_required
def api_buscar_transportadoras(request):
    term = request.GET.get('q', '').strip()
    pessoas = Pessoa.objects.filter(transportador=True, inativo=False)
    if term:
        pessoas = pessoas.filter(
            Q(nome__icontains=term) | Q(cpf_cnpj__icontains=term)
        )
    pessoas = pessoas.order_by('nome')[:30]
    results = [{'id': p.pk, 'text': f'{p.nome} — {p.cpf_cnpj or "---"}'} for p in pessoas]
    return JsonResponse({'results': results})


@login_required
def api_buscar_produtos_fiscal(request):
    term = request.GET.get('q', '').strip()
    if not term or len(term) < 2:
        return JsonResponse({'results': []})
    
    from apps.cadastros.models import CodigoBarras
    
    produtos = Produto.objects.filter(inativo=False).select_related('ncm')
    
    if term.isdigit():
        produtos = produtos.filter(
            Q(pk_chave=int(term)) | Q(codigos_barras__codigo_barras=term)
        )
    else:
        produtos = produtos.filter(
            Q(nome__icontains=term) | Q(referencia_fabrica__icontains=term)
        )
    
    produtos = produtos.distinct().order_by('nome')[:20]
    
    results = []
    for p in produtos:
        cod_barras = ''
        cb = p.codigos_barras.first()
        if cb:
            cod_barras = cb.codigo_barras
        
        results.append({
            'id': p.pk_chave,
            'nome': p.nome,
            'ncm': p.ncm.ncm if p.ncm else '00000000',
            'cfop': p.cfop_venda_estadual or '5102',
            'cst': p.cst_icms or '',
            'aliq': float(p.aliquota_icms or 0),
            'preco': float(p.preco_venda or 0),
            'codigo_barras': cod_barras,
            'unidade': p.unidade_venda.simbolo if p.unidade_venda else 'UN',
            'origem': p.origem or '0',
        })
    
    return JsonResponse({'results': results})


@login_required
def nfe_cancelar(request, pk):
    nfe = get_object_or_404(NFe, pk=pk)
    if nfe.status not in ('AUTORIZADO',):
        messages.error(request, 'Apenas NF-e autorizadas podem ser canceladas.')
        return redirect('fiscal:nfe_detail', pk=pk)

    if request.method == 'POST':
        justificativa = request.POST.get('justificativa', '').strip()
        if len(justificativa) < 15:
            messages.error(request, 'Justificativa deve ter no mínimo 15 caracteres.')
        else:
            try:
                NFeService.cancelar_nfe(pk, justificativa)
                messages.success(request, 'NF-e cancelada com sucesso!')
                return redirect('fiscal:nfe_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Erro ao cancelar: {str(e)}')

    return render(request, 'fiscal/nfe_cancelar.html', {'nota': nfe})


@login_required
def nfe_cce(request, pk):
    nfe = get_object_or_404(NFe, pk=pk)
    if request.method == 'POST':
        correcao = request.POST.get('correcao', '').strip()
        if len(correcao) < 15:
            messages.error(request, 'Correção deve ter no mínimo 15 caracteres.')
        else:
            with transaction.atomic():
                NFeEvento.objects.create(
                    nfe=nfe,
                    tipo='CCE',
                    justificativa=correcao,
                    sequencia=nfe.eventos.filter(tipo='CCE').count() + 1,
                    correcao_cce=correcao,
                )
                if nfe.status == 'AUTORIZADO':
                    nfe.status = 'CCE'
                    nfe.save(update_fields=['status'])
            messages.success(request, 'Carta de Correção registrada!')
            return redirect('fiscal:nfe_detail', pk=pk)

    return render(request, 'fiscal/nfe_cce.html', {'nota': nfe})


@login_required
def nfe_download_xml(request, pk):
    nfe = get_object_or_404(NFe, pk=pk)
    xml_content = nfe.xml_enviado or nfe.xml_retorno or ''
    response = HttpResponse(xml_content, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="{nfe.chave_acesso}-nfe.xml"'
    return response


@login_required
def nfe_autorizar(request, pk):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    try:
        nfe = NFeService.autorizar_nfe(pk)
        if nfe.status == 'AUTORIZADO':
            return JsonResponse({
                'sucesso': True,
                'status': nfe.status,
                'protocolo': nfe.protocolo,
                'mensagem': 'NF-e autorizada com sucesso!'
            })
        elif nfe.status == 'DENEGADO':
            return JsonResponse({
                'sucesso': False,
                'status': nfe.status,
                'erro': nfe.mensagem_retorno or 'NF-e denegada pela SEFAZ'
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'status': nfe.status,
                'erro': nfe.mensagem_retorno or 'NF-e rejeitada pela SEFAZ'
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'sucesso': False,
            'status': 'ERRO',
            'erro': str(e)
        }, status=500)


@login_required
def nfe_simular_autorizar(request, pk):
    from django.conf import settings
    if not settings.DEBUG:
        raise Http404
    nfe = get_object_or_404(NFe, pk=pk)
    if nfe.status == 'VALIDADO':
        nfe.status = 'AUTORIZADO'
        nfe.protocolo = '999999999999999'
        nfe.data_autorizacao = datetime.now()
        nfe.save(update_fields=['status', 'protocolo', 'data_autorizacao'])
        messages.success(request, 'NF-e simulada como autorizada.')
    else:
        messages.warning(request, 'NF-e precisa estar VALIDADO para simular autorização.')
    return redirect('fiscal:nfe_detail', pk=pk)


@login_required
def nfe_danfe(request, pk):
    nfe = get_object_or_404(
        NFe.objects.select_related(
            'empresa__pessoa', 'destinatario', 'empresa__certificado_digital',
            'empresa__cidade_sede__estado',
        ).prefetch_related('itens', 'pagamentos'),
        pk=pk
    )
    from django.conf import settings
    if nfe.status == 'AUTORIZADO':
        pass
    elif nfe.status == 'VALIDADO' and settings.DEBUG:
        pass
    else:
        messages.error(request, 'NF-e precisa estar autorizada para gerar DANFE.')
        return redirect('fiscal:nfe_detail', pk=pk)

    from .danfe import gerar_danfe
    pdf_bytes = gerar_danfe(nfe)
    filename = f'DANFE-{nfe.numero}-{nfe.chave_acesso}.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def nfe_enviar_lote(request):
    if request.method == 'POST':
        nfe_ids = request.POST.getlist('nfe_ids')
        for nfe_id in nfe_ids:
            try:
                nfe = NFe.objects.get(pk=nfe_id, status='VALIDADO')
                nfe = NFeService.autorizar_nfe(nfe.pk)
                nfe.refresh_from_db()
                if nfe.status == 'AUTORIZADO':
                    messages.success(request, f'NF-e #{nfe.numero} autorizada!')
                elif nfe.status == 'DENEGADO':
                    messages.error(request, f'NF-e #{nfe.numero} DENEGADA: {nfe.mensagem_retorno}')
                else:
                    messages.error(request, f'NF-e #{nfe.numero} REJEITADA: {nfe.mensagem_retorno}')
            except NFe.DoesNotExist:
                messages.warning(request, f'NF-e #{nfe_id} não está pronta para envio.')
            except Exception as e:
                messages.error(request, f'Erro na NF-e #{nfe_id}: {str(e)}')
        return redirect('fiscal:nfe_list')
    return redirect('fiscal:nfe_list')


@login_required
def nfe_testar_sefaz(request):
    from .services import NFeService
    empresa = Empresa.objects.first()
    if not empresa:
        messages.error(request, 'Nenhuma empresa cadastrada.')
        return redirect('fiscal:nfe_list')
    if not empresa.certificado_digital:
        messages.error(request, 'Configure um certificado digital na empresa.')
        return redirect('fiscal:empresa_config')
    try:
        resultado = NFeService.testar_conexao_sefaz(empresa)
        if resultado.get('cStat') == '107':
            messages.success(request, f"SEFAZ online! Status: {resultado.get('xMotivo')} | Tempo médio: {resultado.get('tMed', 'N/A')}")
        elif resultado.get('cStat') == 'ERRO':
            messages.error(request, f'Falha na conexão: {resultado.get("xMotivo")}')
        else:
            messages.info(request, f"Resposta SEFAZ: [{resultado.get('cStat')}] {resultado.get('xMotivo')}")
    except Exception as e:
        messages.error(request, f'Erro ao testar conexão: {str(e)[:200]}')
    return redirect('fiscal:nfe_list')


@login_required
def nfe_consultar_status(request, pk):
    nfe = get_object_or_404(NFe, pk=pk)
    if nfe.status in ('ENVIADO', 'AUTORIZADO', 'REJEITADO', 'CANCELADO'):
        try:
            dados = NFeService.consultar_status_sefaz(pk)
            if dados.get('cStat') != '999':
                return JsonResponse({
                    'id': nfe.pk,
                    'status': nfe.status,
                    'protocolo': nfe.protocolo,
                    'sefaz_cstat': dados['cStat'],
                    'sefaz_motivo': dados['xMotivo'],
                    'sefaz_nprot': dados['nProt'],
                })
        except Exception:
            pass
    return JsonResponse({
        'id': nfe.pk,
        'status': nfe.status,
        'protocolo': nfe.protocolo,
        'mensagem': nfe.mensagem_retorno,
    })


class CertificadoListView(LoginRequiredMixin, ListView):
    model = CertificadoDigital
    template_name = 'fiscal/certificado_list.html'
    context_object_name = 'certificados'

    def get_queryset(self):
        return CertificadoDigital.objects.filter(ativo=True).select_related('empresa')


@login_required
def certificado_create(request):
    dados = {}
    if request.method == 'POST':
        empresa = Empresa.objects.first()
        if not empresa:
            messages.error(request, 'Cadastre uma empresa primeiro.')
            return redirect('fiscal:certificado_list')

        arquivo = request.FILES.get('arquivo')
        senha = request.POST.get('senha')

        if arquivo and senha:
            try:
                parsed = NFeService.parse_certificado_pfx(
                    arquivo.read(), senha
                )
                dados = {
                    'cnpj': parsed['cnpj'],
                    'validade_inicio': parsed['validade_inicio'],
                    'validade_fim': parsed['validade_fim'],
                    'emissor': parsed['emissor'],
                }
                request.POST._mutable = True
                for k, v in dados.items():
                    if k != 'emissor':
                        request.POST[k] = v
            except Exception as e:
                messages.warning(request, f'Não foi possível ler o certificado: {str(e)}')

        try:
            CertificadoDigital.objects.create(
                empresa=empresa,
                tipo=request.POST.get('tipo', 'A1'),
                arquivo=request.FILES.get('arquivo'),
                senha=request.POST.get('senha'),
                validade_inicio=request.POST.get('validade_inicio'),
                validade_fim=request.POST.get('validade_fim'),
                cnpj=request.POST.get('cnpj'),
                emissor=dados.get('emissor', ''),
            )
            messages.success(request, 'Certificado cadastrado!')
            return redirect('fiscal:certificado_list')
        except Exception as e:
            messages.error(request, f'Erro: {str(e)}')

    return render(request, 'fiscal/certificado_form.html')


@login_required
def certificado_detail(request, pk):
    certificado = get_object_or_404(CertificadoDigital, pk=pk)
    return render(request, 'fiscal/certificado_detail.html', {
        'certificado': certificado,
    })


@login_required
def api_parse_certificado(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)

    arquivo = request.FILES.get('arquivo')
    senha = request.POST.get('senha')

    if not arquivo or not senha:
        return JsonResponse({'erro': 'Arquivo e senha são obrigatórios'}, status=400)

    try:
        dados = NFeService.parse_certificado_pfx(arquivo.read(), senha)
        return JsonResponse({'sucesso': True, 'dados': dados})
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)


@login_required
def api_buscar_venda(request):
    termo = request.GET.get('q', '').strip()
    vendas = MovimentacaoEstoque.objects.filter(
        tipo_movimento__in=['VE', 'PV']
    ).select_related('pessoa').order_by('-pk_chave')

    if termo.isdigit():
        vendas = vendas.filter(pk_chave=int(termo))
    elif termo:
        vendas = vendas.filter(pessoa__nome__icontains=termo)

    data = []
    for v in vendas[:20]:
        data.append({
            'id': v.pk_chave,
            'cliente': v.pessoa.nome,
            'data': v.data.strftime('%d/%m/%Y') if v.data else '',
            'valor': float(v.vr_total_liquido or 0),
        })
    return JsonResponse({'vendas': data})


@login_required
def nfe_reabrir(request, pk):
    try:
        nfe = NFe.objects.get(pk=pk)
        if nfe.status not in ('REJEITADO', 'DENEGADO'):
            messages.error(request, f'NF-e #{nfe.numero} não está rejeitada ou denegada.')
            return redirect('fiscal:nfe_list')

        nfe.status = 'VALIDADO'
        nfe.mensagem_retorno = ''
        nfe.protocolo = ''
        nfe.xml_retorno = ''
        nfe.lote = None
        nfe.save(update_fields=['status', 'mensagem_retorno', 'protocolo', 'xml_retorno', 'lote'])

        try:
            xml = NFeService.gerar_xml_nfe(nfe)
            nfe.xml_enviado = xml.decode('utf-8')
            nfe.save(update_fields=['xml_enviado'])
        except Exception as e:
            pass

        messages.success(request, f'NF-e #{nfe.numero} reaberta. Reenvie quando estiver pronta.')
    except NFe.DoesNotExist:
        messages.error(request, 'NF-e não encontrada.')
    return redirect('fiscal:nfe_list')


@login_required
@transaction.atomic
def api_emitir_nfe(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    try:
        dados = json.loads(request.body)
        mov_id = dados.get('movimentacao_id')
        if not mov_id:
            return JsonResponse({'erro': 'ID da movimentação é obrigatório'}, status=400)

        nfe = NFeService.criar_nfe_da_venda(int(mov_id), usuario=request.user)

        autorizar = dados.get('autorizar', True)
        if autorizar and nfe.status == 'VALIDADO':
            nfe = NFeService.autorizar_nfe(nfe.pk)

        return JsonResponse({
            'sucesso': True,
            'nfe_id': nfe.pk,
            'numero': nfe.numero,
            'chave': nfe.chave_acesso,
            'status': nfe.status,
        })
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)
