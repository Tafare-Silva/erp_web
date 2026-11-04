"""
Serviços do módulo de veículos.

Integrações externas são plugáveis e configuradas via variáveis de ambiente
(padrão decouple do projeto). Nenhuma depende de chave/contrato para o
funcionamento básico do cadastro.
"""
import requests
from decouple import config


class FipeClient:
    """
    Cliente de consulta à Tabela FIPE.

    Por padrão usa a API gratuita fipe.api.br (sem chave). A URL base pode
    ser sobrescrita por FIPE_API_URL nas variáveis de ambiente para trocar
    de provedor sem alterar o código.
    """
    BASE_URL = config('FIPE_API_URL', default='https://parallelum.com.br/fipe/api/v1')

    def _get(self, path, params=None):
        resp = requests.get(f'{self.BASE_URL}/{path}', params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def listar_marcas(self, tipo='carros'):
        return self._get(f'{tipo}/marcas')

    def listar_modelos(self, codigo_marca, tipo='carros'):
        return self._get(f'{tipo}/marcas/{codigo_marca}/modelos')

    def listar_anos(self, codigo_marca, codigo_modelo, tipo='carros'):
        return self._get(f'{tipo}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos')

    def consultar_preco(self, codigo_marca, codigo_modelo, codigo_ano, tipo='carros'):
        return self._get(f'{tipo}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos/{codigo_ano}')


class ConsultaPlacaClient:
    """
    Consulta de dados do veículo pela placa usando a APIBrasil.

    A APIBrasil oferece duas rotas:
      1. /consulta/veiculos/credits  -> só BearerToken (debita saldo/consulta)
      2. /vehicles/dados             -> Bearer + DeviceToken (plano pago)

    Como o DeviceToken exige contratar um plano, usamos a rota de crédito,
    que só precisa do BearerToken. Em homologação (APIBRASIL_HOMOLOG=1) os
    dados são fictícios e NÃO debitam saldo — ideal para testar.

    Configuração (variáveis de ambiente):
      APIBRASIL_BEARER_TOKEN  -> BearerToken (app.apibrasil.io > Minhas APIs)
      APIBRASIL_HOMOLOG       -> '1' para dados fictícios (default), '0' produção
      APIBRASIL_DEVICE_TOKEN  -> opcional; se preenchido, usa a rota device
    """
    BASE_URL = config('APIBRASIL_URL', default='https://gateway.apibrasil.io/api/v2')

    def is_configured(self):
        return bool(config('APIBRASIL_BEARER_TOKEN', default=''))

    def _headers(self):
        headers = {
            'Authorization': f'Bearer {config("APIBRASIL_BEARER_TOKEN")}',
            'Content-Type': 'application/json',
        }
        return headers

    def consultar_por_placa(self, placa):
        """
        Retorna um dict com dados do veículo ou None se não configurado.
        """
        if not self.is_configured():
            return None
        placa = normalizar_placa(placa)
        if not placa:
            raise RuntimeError('Placa inválida.')

        headers = self._headers()
        homolog = config('APIBRASIL_HOMOLOG', default='1') != '0'

        # Prefere a rota device se houver DeviceToken; senão usa crédito.
        device_token = config('APIBRASIL_DEVICE_TOKEN', default='')
        if device_token:
            path = '/vehicles/dados'
            headers['DeviceToken'] = device_token
        else:
            path = '/consulta/veiculos/credits'

        corpo = {'placa': placa}
        if homolog:
            corpo['homolog'] = True

        resp = requests.post(
            f'{self.BASE_URL}{path}',
            headers=headers,
            json=corpo,
            timeout=30,
        )
        try:
            data = resp.json()
        except ValueError:
            data = {'message': resp.text}
        if resp.status_code >= 400:
            msg = data.get('message') or data
            if 'Plano ativo' in str(msg) or 'não está disponível' in str(msg) or 'nao esta disponivel' in str(msg).lower():
                raise RuntimeError(
                    'Sua conta APIBrasil não possui o serviço de consulta de veículos ativo. '
                    'Ative um plano/device de veículos em app.apibrasil.io (Minhas APIs > Placa Dados) '
                    'para usar a consulta por placa.'
                )
            raise RuntimeError(f'APIBrasil {resp.status_code}: {msg}')

        veiculo = data.get('dados') or data.get('return') or data
        return {
            'renavam': str(veiculo.get('renavam', '')),
            'chassi': str(veiculo.get('chassi', '')),
            'placa': str(veiculo.get('placa', placa)),
            'marca': str(veiculo.get('marca', '')),
            'modelo': str(veiculo.get('modelo', '')),
            'cor': str(veiculo.get('cor', '')),
            'ano_fabricacao': veiculo.get('anoFabricacao') or veiculo.get('ano_fabricacao'),
            'ano_modelo': veiculo.get('anoModelo') or veiculo.get('ano_modelo'),
            'combustivel': str(veiculo.get('combustivel', '')),
            'motor': str(veiculo.get('motor', '')),
        }


def normalizar_placa(placa):
    """Remove máscaras e normaliza a placa para o padrão alfanumérico."""
    if not placa:
        return ''
    placa = placa.upper().replace('-', '').replace(' ', '').strip()
    return placa


def _obter_empresa():
    from apps.cadastros.models import Empresa
    empresa = Empresa.objects.first()
    if not empresa:
        raise ValueError('Nenhuma empresa cadastrada.')
    return empresa


def _garantir_produto_veiculo(veiculo):
    """Garante que o veículo tenha um Produto vinculado para a movimentação."""
    if veiculo.produto_id:
        return veiculo.produto
    from apps.cadastros.models import Produto, Marca, Divisao, Unidade, NCM
    marca = Marca.objects.filter(nome=veiculo.marca.nome).first()
    if not marca:
        marca = Marca.objects.create(nome=veiculo.marca.nome)
    divisao = Divisao.objects.first()
    if not divisao:
        raise ValueError('Cadastre uma Divisão em Cadastros antes de vender veículos.')
    unidade = Unidade.objects.first()
    ncm = NCM.objects.filter(ncm=veiculo.ncm or '').first() or NCM.objects.first()
    produto = Produto.objects.create(
        nome=f'{veiculo.marca} {veiculo.modelo.nome} {veiculo.placa}'.strip()[:255],
        marca=marca,
        divisao=divisao,
        unidade_venda=unidade,
        ncm=ncm,
        preco_venda=veiculo.preco_venda,
        custo_referencia=veiculo.valor_custo,
        cfop_venda_estadual=veiculo.cfop or '5101',
    )
    veiculo.produto = produto
    veiculo.save(update_fields=['produto'])
    return produto


def vender_veiculo(veiculo_id, cliente_id, pagamentos=None, veiculos_entrada=None,
                   vendedor_id=None, local=None, usuario=None, modalidade_frete=9):
    """
    Registra a venda de um veículo, gerando movimentação, NF-e e financeiro.

    - pagamentos: lista de dicts {'tipo_pagamento_id': X, 'valor': Y}
    - veiculos_entrada: lista de ids de veículos dados como entrada (troca)
    """
    from decimal import Decimal
    from datetime import date
    from apps.cadastros.models import (Pessoa, TipoPagamento, MovimentacaoEstoque,
                                       ItemMovimentacaoEstoque, TituloFinanceiro, LocalEstoque)
    from apps.fiscal.models import NFe, NFeItem, NFePagamento
    from apps.fiscal.services import NFeService
    from .models import Veiculo

    veiculo = Veiculo.objects.select_related('marca', 'modelo').get(pk=veiculo_id)
    if veiculo.status != 'EM_ESTOQUE':
        raise ValueError('Veículo não está em estoque para venda.')
    cliente = Pessoa.objects.get(pk=cliente_id)
    empresa = _obter_empresa()

    produto = _garantir_produto_veiculo(veiculo)

    # Valida pagamentos batem com valor
    valor_total = veiculo.preco_venda
    total_entrada = Decimal('0')
    for v_id in veiculos_entrada or []:
        v_entrada = Veiculo.objects.filter(pk=v_id).first()
        if v_entrada and v_entrada.status in ('EM_ESTOQUE', 'EM_AVALIACAO'):
            total_entrada += v_entrada.preco_venda

    total_pag = sum(Decimal(str(p['valor'] or 0)) for p in (pagamentos or []))
    if total_pag + total_entrada < valor_total:
        raise ValueError('Soma dos pagamentos não cobre o valor do veículo.')

    # Movimentação de saída (venda)
    mov = MovimentacaoEstoque.objects.create(
        pessoa=cliente,
        tipo_movimento='VE',
        emitir_nfe=True,
        tipo_documento_fiscal='55',
        cfop=veiculo.cfop or '5101',
        vr_total_bruto=valor_total,
        vr_total_liquido=valor_total,
        local=local,
        vendedor_id=vendedor_id,
        usuario_criacao=usuario,
        observacao=f'Venda de veículo {veiculo}',
    )
    ItemMovimentacaoEstoque.objects.create(
        movimentacao=mov,
        produto=produto,
        local=local,
        quantidade=-1,
        vr_unitario_bruto=valor_total,
        vr_total_bruto=valor_total,
        vr_total_liquido=valor_total,
    )
    mov.recalcular_totais()

    # NF-e de saída
    nfe = NFeService.criar_nfe_da_venda(
        mov.pk_chave, usuario=usuario, modelo='55',
        modalidade_frete=modalidade_frete,
    )
    # vincula o veículo ao item da NF-e
    item_nfe = nfe.itens.first()
    if item_nfe:
        item_nfe.veiculo = veiculo
        item_nfe.ncm = veiculo.ncm or item_nfe.ncm
        item_nfe.cfop = veiculo.cfop or item_nfe.cfop
        item_nfe.origem = veiculo.origem or item_nfe.origem
        item_nfe.cst_icms = veiculo.cst_icms or item_nfe.cst_icms
        item_nfe.csosn = veiculo.csosn or item_nfe.csosn
        item_nfe.aliquota_icms = veiculo.aliquota_icms or item_nfe.aliquota_icms
        item_nfe.cst_pis = veiculo.cst_pis or item_nfe.cst_pis
        item_nfe.cst_cofins = veiculo.cst_cofins or item_nfe.cst_cofins
        item_nfe.save()
        nfe.tipo_operacao = 1
        nfe.natureza_operacao = 'VENDA'
        nfe.valor_total = valor_total
        nfe.valor_total_produtos = valor_total
        nfe.save()

    # Pagamentos na NF-e (dinheiro, cartão etc.)
    for pag in (pagamentos or []):
        tp = TipoPagamento.objects.filter(pk=pag.get('tipo_pagamento_id')).first()
        NFePagamento.objects.create(
            nfe=nfe,
            tipo_pagamento=tp,
            forma_pagamento=tp.forma_pagamento_nfe if tp else 99,
            valor=Decimal(str(pag['valor'] or 0)),
            integracao_pagamento='O',
        )

    # Veículos dados como entrada: registra como forma de pagamento 12/99
    for v_id in veiculos_entrada or []:
        v_entrada = Veiculo.objects.filter(pk=v_id).first()
        if v_entrada:
            NFePagamento.objects.create(
                nfe=nfe,
                tipo_pagamento=TipoPagamento.objects.filter(
                    tipos_titulos_permitidos='OU'
                ).first() or TipoPagamento.objects.first(),
                forma_pagamento=99,
                valor=v_entrada.preco_venda,
                integracao_pagamento='O',
            )
            # registra a entrada do usado (compra) e marca como vendido
            _entrada_veiculo_usado(v_entrada, veiculo, local, usuario)

    # Gera título financeiro (a receber)
    TituloFinanceiro.objects.create(
        tipo='R',
        pessoa=cliente,
        data_vencimento=date.today(),
        numero_documento=str(nfe.numero),
        valor_documento=valor_total,
        valor_saldo=valor_total,
        situacao='ABERTO',
        movimentacao_estoque=mov,
        historico=f'Venda de veículo {veiculo}',
        usuario_criacao=usuario,
    )

    # Atualiza status
    veiculo.status = 'VENDIDO'
    veiculo.save(update_fields=['status'])
    mov.emitir_nfe = True
    mov.tipo_documento_fiscal = '55'
    mov.chave_nfe = nfe.chave_acesso
    mov.save(update_fields=['emitir_nfe', 'tipo_documento_fiscal', 'chave_nfe'])

    return {'movimentacao': mov.pk_chave, 'nfe': nfe.pk, 'veiculo': veiculo.pk}


def _entrada_veiculo_usado(veiculo_entrada, veiculo_vendido, local, usuario):
    """Registra a entrada do veículo usado dado como parte de pagamento."""
    from decimal import Decimal
    from datetime import date
    from apps.cadastros.models import (MovimentacaoEstoque, ItemMovimentacaoEstoque,
                                       TituloFinanceiro)
    from .models import Veiculo

    v = veiculo_entrada
    produto = _garantir_produto_veiculo(v)
    from apps.cadastros.models import Pessoa
    fornecedor = v.dono_recibo
    if not fornecedor:
        fornecedor = Pessoa.objects.filter(fornecedor=True).first() or Pessoa.objects.first()
    if not fornecedor:
        raise ValueError('Cadastre um fornecedor para registrar a entrada do veículo usado.')
    mov = MovimentacaoEstoque.objects.create(
        pessoa=fornecedor,
        tipo_movimento='CO',
        vr_total_bruto=v.preco_venda,
        vr_total_liquido=v.preco_venda,
        local=local,
        usuario_criacao=usuario,
        observacao=f'Entrada de veículo {v} (troca na venda de {veiculo_vendido})',
    )
    ItemMovimentacaoEstoque.objects.create(
        movimentacao=mov,
        produto=produto,
        local=local,
        quantidade=1,
        vr_unitario_bruto=v.preco_venda,
        vr_total_bruto=v.preco_venda,
        vr_total_liquido=v.preco_venda,
    )
    mov.recalcular_totais()
    v.status = 'EM_ESTOQUE'
    v.save(update_fields=['status'])
    return mov


def emitir_nota_compra(veiculo_id, fornecedor_id=None, usuario=None, modalidade_frete=9):
    """
    Emite a NF-e de ENTRADA (compra) do veículo.

    - fornecedor_id: a Pessoa que vendeu o carro à loja (dono do recibo).
      Se não informado, usa veiculo.dono_recibo.
    """
    from decimal import Decimal
    from datetime import date
    from apps.cadastros.models import (Pessoa, MovimentacaoEstoque,
                                       ItemMovimentacaoEstoque, TituloFinanceiro)
    from apps.fiscal.models import NFe, NFeItem
    from apps.fiscal.services import NFeService
    from .models import Veiculo

    veiculo = Veiculo.objects.select_related('marca', 'modelo').get(pk=veiculo_id)

    fornecedor = None
    if fornecedor_id:
        fornecedor = Pessoa.objects.filter(pk=fornecedor_id).first()
    if not fornecedor:
        fornecedor = veiculo.dono_recibo
    if not fornecedor:
        raise ValueError(
            'Informe o fornecedor (dono do veículo) para emitir a nota de compra. '
            'Preencha "Dono do Veículo (Recibo)" no cadastro.'
        )

    empresa = _obter_empresa()
    produto = _garantir_produto_veiculo(veiculo)
    valor = veiculo.valor_custo or veiculo.preco_venda

    # Movimentação de entrada (compra)
    mov = MovimentacaoEstoque.objects.create(
        pessoa=fornecedor,
        tipo_movimento='CO',
        emitir_nfe=True,
        tipo_documento_fiscal='55',
        cfop=veiculo.cfop or '1101',
        vr_total_bruto=valor,
        vr_total_liquido=valor,
        vendedor_id=None,
        usuario_criacao=usuario,
        observacao=f'Compra de veículo {veiculo}',
    )
    ItemMovimentacaoEstoque.objects.create(
        movimentacao=mov,
        produto=produto,
        local=None,
        quantidade=1,
        vr_unitario_bruto=valor,
        vr_total_bruto=valor,
        vr_total_liquido=valor,
    )
    mov.recalcular_totais()

    nfe = NFeService.criar_nfe_da_venda(
        mov.pk_chave, usuario=usuario, modelo='55',
        modalidade_frete=modalidade_frete,
    )
    item_nfe = nfe.itens.first()
    if item_nfe:
        item_nfe.veiculo = veiculo
        item_nfe.ncm = veiculo.ncm or item_nfe.ncm
        item_nfe.cfop = veiculo.cfop or item_nfe.cfop
        item_nfe.origem = veiculo.origem or item_nfe.origem
        item_nfe.cst_icms = veiculo.cst_icms or item_nfe.cst_icms
        item_nfe.csosn = veiculo.csosn or item_nfe.csosn
        item_nfe.aliquota_icms = veiculo.aliquota_icms or item_nfe.aliquota_icms
        item_nfe.cst_pis = veiculo.cst_pis or item_nfe.cst_pis
        item_nfe.cst_cofins = veiculo.cst_cofins or item_nfe.cst_cofins
        item_nfe.save()
    nfe.tipo_operacao = 2
    nfe.natureza_operacao = 'COMPRA'
    nfe.valor_total = valor
    nfe.valor_total_produtos = valor
    nfe.save()

    TituloFinanceiro.objects.create(
        tipo='P',
        pessoa=fornecedor,
        data_vencimento=date.today(),
        numero_documento=str(nfe.numero),
        valor_documento=valor,
        valor_saldo=valor,
        situacao='ABERTO',
        movimentacao_estoque=mov,
        historico=f'Compra de veículo {veiculo}',
        usuario_criacao=usuario,
    )

    mov.chave_nfe = nfe.chave_acesso
    mov.save(update_fields=['chave_nfe'])

    return {'movimentacao': mov.pk_chave, 'nfe': nfe.pk, 'veiculo': veiculo.pk}