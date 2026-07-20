from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
import logging

from apps.cadastros.models import (
    LocalEstoque, SaldoEstoque, Produto,
    MovimentacaoEstoque, ItemMovimentacaoEstoque,
    TipoMovimentacao
)

logger = logging.getLogger(__name__)


class EstoqueService:

    TIPO_ENTRADA_COMPRA = "Compra de Mercadoria"
    TIPO_ENTRADA_ACERTO = "Acerto de Estoque (Entrada)"
    TIPO_SAIDA_VENDA = "Venda de Mercadoria"
    TIPO_SAIDA_ACERTO = "Acerto de Estoque (Saida)"
    TIPO_TRANSFERENCIA_SAIDA = "Transferencia (Saida)"
    TIPO_TRANSFERENCIA_ENTRADA = "Transferencia (Entrada)"

    @staticmethod
    def obter_saldo_produto(produto_id, local_id=None):
        qs = SaldoEstoque.objects.filter(produto_id=produto_id)
        if local_id:
            qs = qs.filter(local_id=local_id)
        resultado = qs.aggregate(total=Sum('quantidade'))
        return resultado['total'] or Decimal('0')

    @staticmethod
    def listar_estoque(filtros=None):
        filtros = filtros or {}
        qs = SaldoEstoque.objects.select_related(
            'produto', 'produto__marca',
            'produto__divisao', 'local'
        )
        if filtros.get('produto'):
            qs = qs.filter(
                Q(produto__nome__icontains=filtros['produto']) |
                Q(produto__referencia_fabrica__icontains=filtros['produto'])
            )
        if filtros.get('local'):
            qs = qs.filter(local__local=filtros['local'])
        if filtros.get('zerados') == 'sim':
            qs = qs.filter(quantidade=0)
        elif filtros.get('zerados') == 'nao':
            qs = qs.filter(quantidade__gt=0)
        return qs.order_by('produto__nome', 'local__local')

    @staticmethod
    def obter_locais():
        return LocalEstoque.objects.filter(ativo=True).order_by('local')

    @staticmethod
    def obter_historico(produto_id=None, local_id=None, limite=100):
        qs = ItemMovimentacaoEstoque.objects.select_related(
            'movimentacao', 'produto', 'local'
        )
        if produto_id:
            qs = qs.filter(produto_id=produto_id)
        if local_id:
            qs = qs.filter(local_id=local_id)
        return qs.order_by(
            '-movimentacao__data', '-movimentacao__data_criacao'
        )[:limite]

    @staticmethod
    def _get_tipo(nome):
        try:
            return TipoMovimentacao.objects.get(nome=nome)
        except TipoMovimentacao.DoesNotExist:
            raise ValueError(
                f"Tipo de movimentacao '{nome}' nao encontrado. "
                f"Crie-o em Cadastros > Tipos de Movimentacao."
            )

    @staticmethod
    @transaction.atomic
    def _movimentar(tipo_nome, produto, local, quantidade,
                    usuario=None, observacao=None, documento=None,
                    custo_unitario=0):
        tipo = EstoqueService._get_tipo(tipo_nome)

        saldo, _ = SaldoEstoque.objects.select_for_update().get_or_create(
            produto=produto,
            local=local,
            defaults={'quantidade': Decimal('0')}
        )

        if tipo.operacao == 'E':
            saldo.quantidade += Decimal(str(quantidade))
        else:
            saldo.quantidade -= Decimal(str(quantidade))
        saldo.save()

        movimentacao = MovimentacaoEstoque.objects.create(
            tipo_movimento='AJ' if tipo.operacao == 'E' else 'VE',
            data=timezone.localdate(),
            observacao=observacao,
            nro_documento=documento or '',
            usuario_criacao=usuario,
        )

        vr_unitario = Decimal(str(custo_unitario))
        vr_total = vr_unitario * Decimal(str(quantidade))

        ItemMovimentacaoEstoque.objects.create(
            movimentacao=movimentacao,
            produto=produto,
            local=local,
            quantidade=Decimal(str(quantidade)) if tipo.operacao == 'E' else -Decimal(str(quantidade)),
            vr_unitario_bruto=vr_unitario,
            vr_unitario_liquido=vr_unitario,
            vr_total_bruto=vr_total,
            vr_total_liquido=vr_total,
        )

        logger.info(
            f"[ESTOQUE] {tipo_nome} | "
            f"Produto: {produto.nome} | "
            f"Qtd: {quantidade}"
        )

        return movimentacao

    @staticmethod
    @transaction.atomic
    def entrada_manual(produto_id, quantidade, local_id,
                       motivo, usuario=None, custo_unitario=0):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser positiva")
        produto = Produto.objects.get(pk=produto_id)
        local = LocalEstoque.objects.get(pk=local_id)
        obs = f"Entrada manual. Motivo: {motivo}"
        mov = EstoqueService._movimentar(
            tipo_nome=EstoqueService.TIPO_ENTRADA_ACERTO,
            produto=produto, local=local,
            quantidade=quantidade,
            usuario=usuario, observacao=obs,
            custo_unitario=custo_unitario,
        )
        return mov.pk

    @staticmethod
    @transaction.atomic
    def saida_manual(produto_id, quantidade, local_id,
                     motivo, usuario=None):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser positiva")
        produto = Produto.objects.get(pk=produto_id)
        local = LocalEstoque.objects.get(pk=local_id)
        saldo_atual = EstoqueService.obter_saldo_produto(produto_id, local_id)
        if saldo_atual < Decimal(str(quantidade)):
            raise ValueError(
                f"Estoque insuficiente em '{local.local}'. "
                f"Disponivel: {saldo_atual} | Solicitado: {quantidade}"
            )
        obs = f"Saida manual. Motivo: {motivo}"
        mov = EstoqueService._movimentar(
            tipo_nome=EstoqueService.TIPO_SAIDA_ACERTO,
            produto=produto, local=local,
            quantidade=quantidade,
            usuario=usuario, observacao=obs,
        )
        return mov.pk

    @staticmethod
    @transaction.atomic
    def transferir(produto_id, quantidade, local_origem_id,
                   local_destino_id, motivo, usuario=None):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser positiva")
        if local_origem_id == local_destino_id:
            raise ValueError("Origem e destino devem ser diferentes")
        produto = Produto.objects.get(pk=produto_id)
        local_origem = LocalEstoque.objects.get(pk=local_origem_id)
        local_destino = LocalEstoque.objects.get(pk=local_destino_id)
        saldo_origem = EstoqueService.obter_saldo_produto(
            produto_id, local_origem_id
        )
        if saldo_origem < Decimal(str(quantidade)):
            raise ValueError(
                f"Estoque insuficiente em '{local_origem.local}'. "
                f"Disponivel: {saldo_origem} | Solicitado: {quantidade}"
            )
        obs = (
            f"Transferencia: {local_origem.local} -> "
            f"{local_destino.local}. Motivo: {motivo}"
        )
        mov_saida = EstoqueService._movimentar(
            tipo_nome=EstoqueService.TIPO_TRANSFERENCIA_SAIDA,
            produto=produto, local=local_origem,
            quantidade=quantidade,
            usuario=usuario, observacao=obs,
        )
        mov_entrada = EstoqueService._movimentar(
            tipo_nome=EstoqueService.TIPO_TRANSFERENCIA_ENTRADA,
            produto=produto, local=local_destino,
            quantidade=quantidade,
            usuario=usuario, observacao=obs,
        )
        return mov_saida.pk, mov_entrada.pk
