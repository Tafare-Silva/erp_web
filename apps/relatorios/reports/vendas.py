from decimal import Decimal

from django.db.models import Count, Max, Sum
from django.db.models.functions import Abs, TruncMonth

from ..columns import Column, make_result, percent
from ..filters import (
    FilterSpec,
    divisoes_choices,
    hoje,
    inicio_mes,
    locais_choices,
    marcas_choices,
    vendedores_choices,
)
from ..helpers import dec, norm, period_text, safe_div, sale_headers, sale_items
from ..registry import Report, register

PERIOD_FILTERS = [
    FilterSpec("data_ini", "Data inicial", "date", default=inicio_mes, col=2),
    FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
]

VENDEDOR_FILTER = FilterSpec("vendedor", "Vendedor", "select", choices=vendedores_choices, col=2)
MARCA_FILTER = FilterSpec("marca", "Marca", "select", choices=marcas_choices, col=2)
DIVISAO_FILTER = FilterSpec("divisao", "Divisão", "select", choices=divisoes_choices, col=2)
LOCAL_FILTER = FilterSpec("local", "Local de estoque", "select", choices=locais_choices, col=2)
CLIENTE_FILTER = FilterSpec("cliente", "Cliente", "text", placeholder="Nome ou CPF/CNPJ", col=3)


def _doc(mov) -> str:
    return mov.nro_documento or f"#{mov.pk_chave}"


def _sales_by_headers(filters, dimension):
    group = {
        "vendedor": ("vendedor__nome", "Vendedor", "Vendas"),
        "cliente": ("pessoa__nome", "Cliente", "Compras"),
    }[dimension]
    field, label, count_label = group
    qs = (
        sale_headers(filters)
        .values(field)
        .annotate(n=Count("pk_chave"), total=Abs(Sum("vr_total_liquido")))
        .order_by("-total")
    )
    rows = []
    for item in qs:
        key = item[field] or "Sem vendedor" if dimension == "vendedor" else item[field] or "Sem cliente"
        total = norm(item["total"])
        rows.append({"grupo": key, "n": item["n"], "total": total, "ticket": safe_div(total, item["n"])})
    return rows, label, count_label


def _sales_by_items(filters, dimension):
    group = {
        "produto": (("produto__pk_chave", "produto__nome", "produto__codigo"), "Produto", "Qtde"),
        "marca": (("produto__marca__nome",), "Marca", "Qtde"),
        "divisao": (("produto__divisao__nome",), "Divisão", "Qtde"),
    }[dimension]
    fields, label, count_label = group
    qs = (
        sale_items(filters)
        .values(*fields)
        .annotate(qtd=Abs(Sum("quantidade")), total=Abs(Sum("vr_total_liquido")))
        .order_by("-total")
    )
    rows = []
    for item in qs:
        if dimension == "produto":
            key = item["produto__nome"] or "Produto removido"
            code = item.get("produto__codigo") or ""
        else:
            key = item[fields[0]] or "Não informado"
            code = ""
        qtd = norm(item["qtd"])
        total = norm(item["total"])
        rows.append(
            {
                "grupo": key,
                "codigo": code,
                "qtd": qtd,
                "n": qtd,
                "total": total,
                "ticket": safe_div(total, qtd),
            }
        )
    return rows, label, count_label


def faturamento_consolidado(filters, mode):
    grouping = filters.get("agrupar") or "vendedor"
    if mode == "analitico":
        items = (
            sale_items(filters)
            .select_related("produto", "movimentacao", "movimentacao__pessoa", "movimentacao__vendedor")
            .order_by("movimentacao__data", "movimentacao__pk_chave", "id")
        )
        columns = [
            Column("data", "Data", "date"),
            Column("documento", "Documento"),
            Column("cliente", "Cliente"),
            Column("vendedor", "Vendedor"),
            Column("produto", "Produto"),
            Column("qtd", "Qtde", "number", sum_key=True),
            Column("unitario", "Unitário", "money"),
            Column("total", "Total", "money", sum_key=True),
        ]
        rows = []
        for item in items:
            rows.append(
                {
                    "data": item.movimentacao.data,
                    "documento": _doc(item.movimentacao),
                    "cliente": item.movimentacao.pessoa.nome if item.movimentacao.pessoa else "-",
                    "vendedor": item.movimentacao.vendedor.nome if item.movimentacao.vendedor else "-",
                    "produto": item.produto.nome,
                    "qtd": norm(item.quantidade),
                    "unitario": norm(item.vr_unitario_liquido),
                    "total": norm(item.vr_total_liquido),
                }
            )
        return make_result(
            columns,
            rows,
            sum_keys=("qtd", "total"),
            subtitle="Detalhamento item a item por venda",
            notes=[f"Período: {period_text(filters)}"],
        )

    if grouping in ("vendedor", "cliente"):
        rows, label, count_label = _sales_by_headers(filters, grouping)
        columns = [
            Column("grupo", label),
            Column("n", count_label, "number", sum_key=True),
            Column("total", "Faturamento", "money", sum_key=True),
            Column("ticket", "Ticket médio", "money"),
            Column("part", "Part. %", "percent"),
        ]
    else:
        rows, label, count_label = _sales_by_items(filters, grouping)
        columns = [Column("grupo", label)]
        if grouping == "produto":
            columns.insert(1, Column("codigo", "Código"))
        columns += [
            Column("qtd", count_label, "number", sum_key=True),
            Column("total", "Faturamento", "money", sum_key=True),
            Column("ticket", "Preço médio", "money"),
            Column("part", "Part. %", "percent"),
        ]

    total = sum((dec(r["total"]) for r in rows), Decimal("0"))
    for row in rows:
        row["part"] = percent(row["total"], total)

    result = make_result(
        columns,
        rows,
        sum_keys=("n", "qtd", "total"),
        subtitle=f"Agrupado por {label.lower()} · {period_text(filters)}",
    )
    result.totals["ticket"] = safe_div(result.totals.get("total"), result.totals.get("qtd") or result.totals.get("n"))
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def evolucao_vendas(filters, mode):
    if mode == "analitico":
        vendas = (
            sale_headers(filters)
            .select_related("pessoa", "vendedor")
            .order_by("data", "pk_chave")
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
                "documento": _doc(venda),
                "cliente": venda.pessoa.nome if venda.pessoa else "-",
                "vendedor": venda.vendedor.nome if venda.vendedor else "-",
                "total": norm(venda.vr_total_liquido),
            }
            for venda in vendas
        ]
        return make_result(
            columns,
            rows,
            sum_keys=("total",),
            subtitle=f"Vendas realizadas · {period_text(filters)}",
        )

    items = sale_items(filters)
    grouped = (
        items.annotate(periodo=TruncMonth("movimentacao__data"))
        .values("periodo")
        .annotate(
            n=Count("movimentacao", distinct=True),
            qtd=Abs(Sum("quantidade")),
            total=Abs(Sum("vr_total_liquido")),
        )
        .order_by("periodo")
    )
    rows = []
    previous = None
    for item in grouped:
        periodo = item["periodo"]
        total = norm(item["total"])
        variacao = Decimal("0")
        if previous is not None and previous > 0:
            variacao = ((total - previous) / previous * Decimal("100")).quantize(Decimal("0.01"))
        rows.append(
            {
                "periodo": periodo,
                "n": item["n"],
                "qtd": norm(item["qtd"]),
                "total": total,
                "ticket": safe_div(total, item["n"]),
                "variacao": variacao,
            }
        )
        previous = total

    columns = [
        Column("periodo", "Mês", "date"),
        Column("n", "Vendas", "number", sum_key=True),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("total", "Faturamento", "money", sum_key=True),
        Column("ticket", "Ticket médio", "money"),
        Column("variacao", "Variação %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "qtd", "total"),
        subtitle=f"Evolução mensal · {period_text(filters)}",
    )
    result.totals["ticket"] = safe_div(result.totals.get("total"), result.totals.get("n"))
    result.totals["variacao"] = Decimal("0")
    return result


def ranking_clientes(filters, mode):
    if mode == "analitico":
        vendas = (
            sale_headers(filters)
            .select_related("pessoa", "vendedor")
            .order_by("-vr_total_liquido", "data")
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
                "documento": _doc(venda),
                "cliente": venda.pessoa.nome if venda.pessoa else "-",
                "vendedor": venda.vendedor.nome if venda.vendedor else "-",
                "total": norm(venda.vr_total_liquido),
            }
            for venda in vendas
        ]
        return make_result(columns, rows, sum_keys=("total",), subtitle=period_text(filters))

    grouped = (
        sale_headers(filters)
        .values("pessoa__chave", "pessoa__nome", "pessoa__vendedor_padrao__nome")
        .annotate(n=Count("pk_chave"), total=Abs(Sum("vr_total_liquido")), ultima=Max("data"))
        .order_by("-total")
    )
    rows = []
    for index, item in enumerate(grouped, start=1):
        total = norm(item["total"])
        rows.append(
            {
                "posicao": index,
                "cliente": item["pessoa__nome"] or "Sem cliente",
                "vendedor": item["pessoa__vendedor_padrao__nome"] or "-",
                "n": item["n"],
                "total": total,
                "ticket": safe_div(total, item["n"]),
                "ultima": item["ultima"],
            }
        )
    total = sum((row["total"] for row in rows), Decimal("0"))
    for row in rows:
        row["part"] = percent(row["total"], total)

    columns = [
        Column("posicao", "#", "number"),
        Column("cliente", "Cliente"),
        Column("vendedor", "Vendedor"),
        Column("n", "Compras", "number", sum_key=True),
        Column("total", "Faturamento", "money", sum_key=True),
        Column("ticket", "Ticket médio", "money"),
        Column("ultima", "Última compra", "date"),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "total"),
        subtitle=f"Clientes que mais compraram · {period_text(filters)}",
    )
    result.totals["ticket"] = safe_div(result.totals.get("total"), result.totals.get("n"))
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def curva_abc_produtos(filters, mode):
    if mode == "analitico":
        items = (
            sale_items(filters)
            .select_related("produto", "movimentacao", "movimentacao__pessoa")
            .order_by("movimentacao__data", "id")
        )
        columns = [
            Column("data", "Data", "date"),
            Column("cliente", "Cliente"),
            Column("produto", "Produto"),
            Column("qtd", "Qtde", "number", sum_key=True),
            Column("total", "Faturamento", "money", sum_key=True),
        ]
        rows = [
            {
                "data": item.movimentacao.data,
                "cliente": item.movimentacao.pessoa.nome if item.movimentacao.pessoa else "-",
                "produto": item.produto.nome,
                "qtd": norm(item.quantidade),
                "total": norm(item.vr_total_liquido),
            }
            for item in items
        ]
        return make_result(columns, rows, sum_keys=("qtd", "total"), subtitle=period_text(filters))

    grouped = list(
        sale_items(filters)
        .values("produto__pk_chave", "produto__nome", "produto__codigo")
        .annotate(qtd=Abs(Sum("quantidade")), total=Abs(Sum("vr_total_liquido")))
        .order_by("-total")
    )
    total = sum((norm(item["total"]) for item in grouped), Decimal("0"))
    accumulated = Decimal("0")
    rows = []
    for index, item in enumerate(grouped, start=1):
        value = norm(item["total"])
        accumulated += value
        part = percent(value, total)
        accumulated_part = percent(accumulated, total)
        if accumulated_part <= 80:
            classe = "A"
        elif accumulated_part <= 95:
            classe = "B"
        else:
            classe = "C"
        rows.append(
            {
                "posicao": index,
                "codigo": item["produto__codigo"] or "",
                "produto": item["produto__nome"] or "Produto removido",
                "qtd": norm(item["qtd"]),
                "total": value,
                "part": part,
                "acumulado": accumulated_part,
                "classe": classe,
            }
        )

    columns = [
        Column("posicao", "#", "number"),
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("total", "Faturamento", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
        Column("acumulado", "Acum. %", "percent"),
        Column("classe", "Classe"),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("qtd", "total"),
        subtitle=f"Classificação ABC por faturamento · {period_text(filters)}",
        notes=["Classe A: até 80% acumulado · B: até 95% · C: demais."],
    )


def produtos_vendidos(filters, mode):
    if mode == "analitico":
        items = (
            sale_items(filters)
            .select_related("produto", "movimentacao", "movimentacao__pessoa", "movimentacao__vendedor")
            .order_by("movimentacao__data", "movimentacao__pk_chave", "id")
        )
        columns = [
            Column("data", "Data", "date"),
            Column("documento", "Documento"),
            Column("cliente", "Cliente"),
            Column("vendedor", "Vendedor"),
            Column("codigo", "Código"),
            Column("produto", "Produto"),
            Column("qtd", "Qtde", "number", sum_key=True),
            Column("unitario", "Unitário", "money"),
            Column("total", "Total", "money", sum_key=True),
        ]
        rows = [
            {
                "data": item.movimentacao.data,
                "documento": _doc(item.movimentacao),
                "cliente": item.movimentacao.pessoa.nome if item.movimentacao.pessoa else "-",
                "vendedor": item.movimentacao.vendedor.nome if item.movimentacao.vendedor else "-",
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
        sale_items(filters)
        .values(
            "produto__pk_chave",
            "produto__nome",
            "produto__codigo",
            "produto__marca__nome",
            "produto__divisao__nome",
        )
        .annotate(qtd=Abs(Sum("quantidade")), total=Abs(Sum("vr_total_liquido")))
        .order_by("-total")
    )
    rows = []
    total = Decimal("0")
    for item in grouped:
        value = norm(item["total"])
        qtd = norm(item["qtd"])
        total += value
        rows.append(
            {
                "codigo": item["produto__codigo"] or "",
                "produto": item["produto__nome"] or "Produto removido",
                "marca": item["produto__marca__nome"] or "-",
                "divisao": item["produto__divisao__nome"] or "-",
                "qtd": qtd,
                "total": value,
                "medio": safe_div(value, qtd),
                "part": percent(value, total) if total else Decimal("0"),
            }
        )
    for row in rows:
        row["part"] = percent(row["total"], total)

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("marca", "Marca"),
        Column("divisao", "Divisão"),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("total", "Faturamento", "money", sum_key=True),
        Column("medio", "Preço médio", "money"),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("qtd", "total"),
        subtitle=f"Produtos vendidos · {period_text(filters)}",
    )
    result.totals["medio"] = safe_div(result.totals.get("total"), result.totals.get("qtd"))
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


register(
    Report(
        slug="faturamento-consolidado",
        title="Faturamento Consolidado",
        category="vendas",
        description="Quanto a empresa vendeu no período, por vendedor, cliente, produto, marca ou divisão.",
        filters=PERIOD_FILTERS
        + [
            FilterSpec(
                "agrupar",
                "Agrupar por",
                "select",
                choices=[
                    ("vendedor", "Vendedor"),
                    ("cliente", "Cliente"),
                    ("produto", "Produto"),
                    ("marca", "Marca"),
                    ("divisao", "Divisão"),
                ],
                default="vendedor",
                col=2,
            ),
            VENDEDOR_FILTER,
            CLIENTE_FILTER,
            MARCA_FILTER,
            DIVISAO_FILTER,
            LOCAL_FILTER,
        ],
        run=faturamento_consolidado,
        supports_analitico=True,
        icon="fa-chart-pie",
        order=1,
    )
)

register(
    Report(
        slug="evolucao-vendas",
        title="Evolução de Vendas",
        category="vendas",
        description="Faturamento mês a mês, ticket médio e variação percentual.",
        filters=[
            FilterSpec("data_ini", "Data inicial", "date", default=lambda: hoje().replace(month=1, day=1), col=2),
            FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
            VENDEDOR_FILTER,
            CLIENTE_FILTER,
        ],
        run=evolucao_vendas,
        supports_analitico=True,
        icon="fa-chart-line",
        order=2,
    )
)

register(
    Report(
        slug="ranking-clientes",
        title="Ranking de Clientes",
        category="vendas",
        description="Clientes que mais compraram no período, com ticket médio e participação.",
        filters=PERIOD_FILTERS + [VENDEDOR_FILTER, CLIENTE_FILTER],
        run=ranking_clientes,
        supports_analitico=True,
        icon="fa-trophy",
        order=3,
    )
)

register(
    Report(
        slug="curva-abc-produtos",
        title="Curva ABC de Produtos",
        category="vendas",
        description="Classificação de produtos por participação no faturamento (Pareto).",
        filters=PERIOD_FILTERS + [MARCA_FILTER, DIVISAO_FILTER],
        run=curva_abc_produtos,
        supports_analitico=True,
        icon="fa-ranking-star",
        order=4,
    )
)

register(
    Report(
        slug="produtos-vendidos",
        title="Produtos Vendidos no Período",
        category="vendas",
        description="Quanto saiu de cada produto, com marca, divisão, quantidade e preço médio.",
        filters=PERIOD_FILTERS
        + [
            VENDEDOR_FILTER,
            FilterSpec("fabricante", "Fabricante", "text", placeholder="Fabricante", col=2),
            MARCA_FILTER,
            DIVISAO_FILTER,
        ],
        run=produtos_vendidos,
        supports_analitico=True,
        icon="fa-box-open",
        order=5,
    )
)
