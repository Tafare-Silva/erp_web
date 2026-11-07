from decimal import Decimal

from django.db.models import Count, Sum

from ..columns import Column, make_result, percent
from ..filters import FilterSpec, fornecedores_choices, hoje, inicio_mes
from ..helpers import dec, norm, period_text, purchase_headers, purchase_items, safe_div
from ..registry import Report, register

PERIOD_FILTERS = [
    FilterSpec("data_ini", "Data inicial", "date", default=inicio_mes, col=2),
    FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
]

FORNECEDOR_FILTER = FilterSpec("fornecedor", "Fornecedor", "select", choices=fornecedores_choices, col=3)


def compras_por_fornecedor(filters, mode):
    qs = purchase_items(filters)

    if mode == "analitico":
        compras = (
            qs.select_related("movimentacao", "movimentacao__pessoa")
            .order_by("movimentacao__data", "movimentacao__pk_chave", "id")
        )
        columns = [
            Column("data", "Data", "date"),
            Column("documento", "Documento"),
            Column("fornecedor", "Fornecedor"),
            Column("total", "Total", "money", sum_key=True),
        ]
        rows = [
            {
                "data": compra.movimentacao.data,
                "documento": compra.movimentacao.nro_documento or f"#{compra.movimentacao.pk_chave}",
                "fornecedor": compra.movimentacao.pessoa.nome if compra.movimentacao.pessoa else "-",
                "total": norm(compra.movimentacao.vr_total_liquido),
            }
            for compra in compras
        ]
        return make_result(columns, rows, sum_keys=("total",), subtitle=period_text(filters))

    grouped = (
        qs.values("movimentacao__pessoa__nome")
        .annotate(n=Count("movimentacao_id", distinct=True), total=Sum("vr_total_liquido"))
        .order_by("-total")
    )
    rows = []
    total = Decimal("0")
    for item in grouped:
        valor = norm(item["total"])
        total += valor
        rows.append(
            {
                "fornecedor": item["movimentacao__pessoa__nome"] or "Sem fornecedor",
                "n": item["n"],
                "total": valor,
                "ticket": safe_div(valor, item["n"]),
            }
        )
    for row in rows:
        row["part"] = percent(row["total"], total)

    columns = [
        Column("fornecedor", "Fornecedor"),
        Column("n", "Compras", "number", sum_key=True),
        Column("total", "Total comprado", "money", sum_key=True),
        Column("ticket", "Ticket médio", "money"),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "total"),
        subtitle=f"Compras por fornecedor · {period_text(filters)}",
    )
    result.totals["ticket"] = safe_div(result.totals.get("total"), result.totals.get("n"))
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def compras_por_produto(filters, mode):
    if mode == "analitico":
        items = (
            purchase_items(filters)
            .select_related("produto", "movimentacao", "movimentacao__pessoa")
            .order_by("movimentacao__data", "id")
        )
        columns = [
            Column("data", "Data", "date"),
            Column("documento", "Documento"),
            Column("fornecedor", "Fornecedor"),
            Column("codigo", "Código"),
            Column("produto", "Produto"),
            Column("qtd", "Qtde", "number", sum_key=True),
            Column("unitario", "Unitário", "money"),
            Column("total", "Total", "money", sum_key=True),
        ]
        rows = [
            {
                "data": item.movimentacao.data,
                "documento": item.movimentacao.nro_documento or f"#{item.movimentacao.pk_chave}",
                "fornecedor": item.movimentacao.pessoa.nome if item.movimentacao.pessoa else "-",
                "codigo": item.produto.codigo or "",
                "produto": item.produto.nome,
                "qtd": norm(item.quantidade),
                "unitario": norm(item.vr_unitario_liquido),
                "total": norm(item.vr_total_liquido),
            }
            for item in items
        ]
        return make_result(columns, rows, sum_keys=("qtd", "total"), subtitle=period_text(filters))

    grouped = (
        purchase_items(filters)
        .values("produto__pk_chave", "produto__nome", "produto__codigo")
        .annotate(qtd=Sum("quantidade"), total=Sum("vr_total_liquido"))
        .order_by("-total")
    )
    rows = []
    total = Decimal("0")
    for item in grouped:
        qtd = norm(item["qtd"])
        valor = norm(item["total"])
        total += valor
        rows.append(
            {
                "codigo": item["produto__codigo"] or "",
                "produto": item["produto__nome"] or "Produto removido",
                "qtd": qtd,
                "total": valor,
                "medio": safe_div(valor, qtd),
            }
        )
    for row in rows:
        row["part"] = percent(row["total"], total)

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("total", "Total comprado", "money", sum_key=True),
        Column("medio", "Custo médio", "money"),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("qtd", "total"),
        subtitle=f"Compras por produto · {period_text(filters)}",
    )
    result.totals["medio"] = safe_div(result.totals["total"], result.totals["qtd"])
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


register(
    Report(
        slug="compras-por-fornecedor",
        title="Compras por Fornecedor",
        category="compras",
        description="Total comprado de cada fornecedor no período.",
        filters=PERIOD_FILTERS + [FORNECEDOR_FILTER],
        run=compras_por_fornecedor,
        supports_analitico=True,
        icon="fa-truck",
        order=1,
    )
)

register(
    Report(
        slug="compras-por-produto",
        title="Compras por Produto",
        category="compras",
        description="Total comprado por produto, com custo médio.",
        filters=PERIOD_FILTERS + [FORNECEDOR_FILTER],
        run=compras_por_produto,
        supports_analitico=True,
        icon="fa-boxes-packing",
        order=2,
    )
)
