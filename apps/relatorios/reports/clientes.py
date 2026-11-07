from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Max, Q, Sum

from ..columns import Column, make_result, percent
from ..filters import FilterSpec, hoje, inicio_mes, vendedores_choices
from ..helpers import OPEN_SITUACOES, dec, norm, period_text, safe_div, today
from ..registry import Report, register
from apps.cadastros.models import Pessoa

VENDEDOR_FILTER = FilterSpec("vendedor", "Vendedor", "select", choices=vendedores_choices, col=3)


def _cliente_telefone(pessoa):
    return pessoa.celular_principal or pessoa.telefone_fixo or "-"


def clientes_inativos(filters, mode):
    dias = filters.get("dias") or 90
    cutoff = today() - timedelta(days=int(dias))
    qs = Pessoa.objects.filter(cliente=True)
    if filters.get("vendedor"):
        qs = qs.filter(vendedor_padrao_id=filters["vendedor"])
    qs = qs.annotate(
        ultima=Max("movimentacoes__data", filter=Q(movimentacoes__tipo_movimento="VE")),
        total=Sum(
            "movimentacoes__vr_total_liquido",
            filter=Q(movimentacoes__tipo_movimento="VE"),
        ),
        compras=Count("movimentacoes", filter=Q(movimentacoes__tipo_movimento="VE")),
    ).filter(Q(ultima__lt=cutoff) | Q(ultima__isnull=True))

    rows = []
    for pessoa in qs.select_related("vendedor_padrao").order_by("ultima", "nome"):
        ultima = pessoa.ultima
        rows.append(
            {
                "cliente": pessoa.nome,
                "vendedor": pessoa.vendedor_padrao.nome if pessoa.vendedor_padrao else "-",
                "ultima": ultima,
                "dias_sem_comprar": (today() - ultima).days if ultima else None,
                "compras": pessoa.compras,
                "total": norm(pessoa.total),
                "telefone": _cliente_telefone(pessoa),
            }
        )

    columns = [
        Column("cliente", "Cliente"),
        Column("vendedor", "Vendedor"),
        Column("telefone", "Telefone"),
        Column("ultima", "Última compra", "date"),
        Column("dias_sem_comprar", "Dias sem comprar", "number"),
        Column("compras", "Compras", "number", sum_key=True),
        Column("total", "Total histórico", "money", sum_key=True),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("compras", "total"),
        subtitle=f"Clientes sem compra há mais de {dias} dias · {period_text(filters) if filters.get('data_ini') else 'todos os períodos'}",
        notes=["Inclui clientes que nunca compraram (última compra em branco)."],
    )


def clientes_positivados(filters, mode):
    if mode == "analitico":
        from ..helpers import sale_headers

        vendas = (
            sale_headers(filters)
            .select_related("pessoa", "vendedor")
            .order_by("-data", "pk_chave")
        )
        columns = [
            Column("data", "Data", "date"),
            Column("documento", "Documento"),
            Column("cliente", "Cliente"),
            Column("vendedor", "Vendedor"),
            Column("total", "Faturamento", "money", sum_key=True),
        ]
        rows = [
            {
                "data": venda.data,
                "documento": venda.nro_documento or f"#{venda.pk_chave}",
                "cliente": venda.pessoa.nome if venda.pessoa else "-",
                "vendedor": venda.vendedor.nome if venda.vendedor else "-",
                "total": norm(venda.vr_total_liquido),
            }
            for venda in vendas
        ]
        return make_result(columns, rows, sum_keys=("total",), subtitle=period_text(filters))

    filters_periodo = Q(
        movimentacoes__tipo_movimento="VE",
        movimentacoes__data__gte=filters.get("data_ini"),
        movimentacoes__data__lte=filters.get("data_fim"),
    )
    if not filters.get("data_ini"):
        filters_periodo = Q(movimentacoes__tipo_movimento="VE", movimentacoes__data__lte=filters.get("data_fim"))
    if not filters.get("data_fim"):
        filters_periodo = Q(movimentacoes__tipo_movimento="VE", movimentacoes__data__gte=filters.get("data_ini"))

    carteira = Pessoa.objects.filter(cliente=True)
    if filters.get("vendedor"):
        carteira = carteira.filter(vendedor_padrao_id=filters["vendedor"])
    total_carteira = carteira.count()

    qs = carteira.annotate(
        n=Count("movimentacoes", filter=filters_periodo),
        total=Sum("movimentacoes__vr_total_liquido", filter=filters_periodo),
        ultima=Max("movimentacoes__data", filter=Q(movimentacoes__tipo_movimento="VE")),
    ).filter(n__gt=0)

    rows = []
    for pessoa in qs.select_related("vendedor_padrao").order_by("-total", "nome"):
        total = norm(pessoa.total)
        rows.append(
            {
                "cliente": pessoa.nome,
                "vendedor": pessoa.vendedor_padrao.nome if pessoa.vendedor_padrao else "-",
                "n": pessoa.n,
                "total": total,
                "ticket": safe_div(total, pessoa.n),
                "ultima": pessoa.ultima,
            }
        )
    total = sum((row["total"] for row in rows), Decimal("0"))
    for row in rows:
        row["part"] = percent(row["total"], total)

    columns = [
        Column("cliente", "Cliente"),
        Column("vendedor", "Vendedor"),
        Column("n", "Compras", "number", sum_key=True),
        Column("total", "Faturamento", "money", sum_key=True),
        Column("ticket", "Ticket médio", "money"),
        Column("ultima", "Última compra", "date"),
        Column("part", "Part. %", "percent"),
    ]
    positivados = len(rows)
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "total"),
        subtitle=f"Clientes positivados · {period_text(filters)}",
        notes=[
            f"Positivados: {positivados} de {total_carteira} clientes da carteira "
            f"({percent(positivados, total_carteira):.2f}%).".replace(".", ","),
        ],
    )
    result.totals["ticket"] = safe_div(result.totals.get("total"), result.totals.get("n"))
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def carteira_por_vendedor(filters, mode):
    qs = Pessoa.objects.filter(cliente=True)
    if filters.get("vendedor"):
        qs = qs.filter(vendedor_padrao_id=filters["vendedor"])
    qs = qs.annotate(
        ultima=Max("movimentacoes__data", filter=Q(movimentacoes__tipo_movimento="VE")),
        total=Sum("movimentacoes__vr_total_liquido", filter=Q(movimentacoes__tipo_movimento="VE")),
    ).select_related("vendedor_padrao").order_by("vendedor_padrao__nome", "nome")

    if mode == "analitico":
        columns = [
            Column("vendedor", "Vendedor"),
            Column("cliente", "Cliente"),
            Column("telefone", "Telefone"),
            Column("situacao", "Situação"),
            Column("ultima", "Última compra", "date"),
            Column("total", "Total histórico", "money", sum_key=True),
        ]
        rows = []
        for pessoa in qs:
            rows.append(
                {
                    "vendedor": pessoa.vendedor_padrao.nome if pessoa.vendedor_padrao else "Sem vendedor",
                    "cliente": pessoa.nome,
                    "telefone": _cliente_telefone(pessoa),
                    "situacao": "Inativo" if pessoa.inativo else "Ativo",
                    "ultima": pessoa.ultima,
                    "total": norm(pessoa.total),
                }
            )
        return make_result(columns, rows, sum_keys=("total",), subtitle="Carteira detalhada por vendedor")

    grouped = defaultdict(
        lambda: {
            "vendedor": "",
            "clientes": 0,
            "ativos": 0,
            "inativos": 0,
            "total": Decimal("0"),
            "ultima": None,
        }
    )
    for pessoa in qs:
        key = pessoa.vendedor_padrao.nome if pessoa.vendedor_padrao else "Sem vendedor"
        row = grouped[key]
        row["vendedor"] = key
        row["clientes"] += 1
        if pessoa.inativo:
            row["inativos"] += 1
        else:
            row["ativos"] += 1
        row["total"] += norm(pessoa.total)
        if pessoa.ultima and (row["ultima"] is None or pessoa.ultima > row["ultima"]):
            row["ultima"] = pessoa.ultima

    rows = sorted(grouped.values(), key=lambda r: r["clientes"], reverse=True)
    columns = [
        Column("vendedor", "Vendedor"),
        Column("clientes", "Clientes", "number", sum_key=True),
        Column("ativos", "Ativos", "number", sum_key=True),
        Column("inativos", "Inativos", "number", sum_key=True),
        Column("total", "Total histórico", "money", sum_key=True),
        Column("ultima", "Última venda", "date"),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("clientes", "ativos", "inativos", "total"),
        subtitle="Carteira de clientes por vendedor",
        notes=["Ativo/Inativo considera o campo inativo do cadastro do cliente."],
    )


def limite_credito(filters, mode):
    qs = Pessoa.objects.filter(cliente=True)
    if filters.get("vendedor"):
        qs = qs.filter(vendedor_padrao_id=filters["vendedor"])
    qs = qs.annotate(
        aberto=Sum(
            "titulos_financeiros__valor_saldo",
            filter=Q(titulos_financeiros__tipo="R", titulos_financeiros__situacao__in=OPEN_SITUACOES),
        ),
        vencido=Sum(
            "titulos_financeiros__valor_saldo",
            filter=Q(
                titulos_financeiros__tipo="R",
                titulos_financeiros__situacao__in=OPEN_SITUACOES,
                titulos_financeiros__data_vencimento__lt=today(),
            ),
        ),
        titulos_abertos=Count(
            "titulos_financeiros",
            filter=Q(titulos_financeiros__tipo="R", titulos_financeiros__situacao__in=OPEN_SITUACOES),
        ),
    ).filter(Q(limite_credito__gt=0) | Q(aberto__gt=0))

    rows = []
    for pessoa in qs.order_by("-aberto", "nome"):
        limite = dec(pessoa.limite_credito)
        aberto = norm(pessoa.aberto)
        vencido = norm(pessoa.vencido)
        disponivel = max(limite - aberto, Decimal("0")) if limite else Decimal("0")
        uso = percent(aberto, limite) if limite else Decimal("0")
        rows.append(
            {
                "cliente": pessoa.nome,
                "limite": limite,
                "aberto": aberto,
                "vencido": vencido,
                "disponivel": disponivel,
                "uso": uso,
                "estourou": "Sim" if limite and aberto > limite else "Não",
                "titulos": pessoa.titulos_abertos,
            }
        )

    columns = [
        Column("cliente", "Cliente"),
        Column("limite", "Limite", "money", sum_key=True),
        Column("aberto", "Em aberto", "money", sum_key=True),
        Column("vencido", "Vencido", "money", sum_key=True),
        Column("disponivel", "Disponível", "money", sum_key=True),
        Column("uso", "Uso %", "percent"),
        Column("titulos", "Títulos", "number", sum_key=True),
        Column("estourou", "Estourou?"),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("limite", "aberto", "vencido", "disponivel", "titulos"),
        subtitle="Limite de crédito versus utilização",
        notes=["Utilização = saldo em aberto de títulos a receber. Disponível limitado a zero quando não há limite cadastrado."],
    )


register(
    Report(
        slug="clientes-inativos",
        title="Clientes Inativos",
        category="clientes",
        description="Quem parou de comprar (ou nunca comprou), com telefone e última compra.",
        filters=[
            FilterSpec("dias", "Sem comprar há (dias)", "number", default=90, col=2),
            VENDEDOR_FILTER,
        ],
        run=clientes_inativos,
        icon="fa-user-clock",
        order=1,
    )
)

register(
    Report(
        slug="clientes-positivados",
        title="Clientes Positivados no Período",
        category="clientes",
        description="Quem comprou no período e quanto, comparado ao total da carteira.",
        filters=[
            FilterSpec("data_ini", "Data inicial", "date", default=inicio_mes, col=2),
            FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
            VENDEDOR_FILTER,
        ],
        run=clientes_positivados,
        supports_analitico=True,
        icon="fa-user-check",
        order=2,
    )
)

register(
    Report(
        slug="carteira-por-vendedor",
        title="Carteira por Vendedor",
        category="clientes",
        description="Clientes atribuídos a cada vendedor, com ativos, inativos e total histórico.",
        filters=[VENDEDOR_FILTER],
        run=carteira_por_vendedor,
        supports_analitico=True,
        icon="fa-address-book",
        order=3,
    )
)

register(
    Report(
        slug="limite-credito",
        title="Limite de Crédito vs Utilização",
        category="clientes",
        description="Limite concedido contra o saldo em aberto e vencido, por cliente.",
        filters=[VENDEDOR_FILTER],
        run=limite_credito,
        icon="fa-credit-card",
        order=4,
    )
)
