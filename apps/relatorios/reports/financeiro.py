from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from ..columns import Column, make_result, percent
from ..filters import FilterSpec, hoje, inicio_mes, tipos_pagamento_choices
from ..helpers import (
    OPEN_SITUACOES,
    dec,
    norm,
    period_text,
    safe_div,
    titulos,
    today,
)
from ..registry import Report, register

CLIENTE_TEXT = FilterSpec("cliente", "Cliente", "text", placeholder="Nome ou CPF/CNPJ", col=3)


def _idade_bucket(dias: int) -> str:
    if dias <= 0:
        return "a_vencer"
    if dias <= 30:
        return "d30"
    if dias <= 60:
        return "d60"
    if dias <= 90:
        return "d90"
    return "d90_mais"


def _aging(filters, tipo, mode):
    is_receber = tipo == "R"
    qs = titulos(filters, tipo).filter(situacao__in=OPEN_SITUACOES)
    qs = qs.select_related("pessoa", "tipo_pagamento").order_by("data_vencimento", "pk_chave")

    hoje = today()
    registros = []
    for titulo in qs:
        venc = titulo.data_vencimento
        dias = (hoje - venc).days
        registros.append(
            {
                "pessoa": titulo.pessoa.nome if titulo.pessoa else "-",
                "documento": titulo.numero_documento or f"#{titulo.pk_chave}",
                "parcela": f"{titulo.parcela}/{titulo.total_parcelas}",
                "emissao": titulo.data_emissao,
                "vencimento": venc,
                "dias": dias,
                "valor": dec(titulo.valor_documento),
                "saldo": dec(titulo.valor_saldo),
                "situacao": titulo.get_situacao_display(),
                "tipo_pagamento": titulo.tipo_pagamento.tipo_pagamento if titulo.tipo_pagamento else "-",
                "bucket": _idade_bucket(dias),
            }
        )

    if mode == "analitico":
        columns = [
            Column("pessoa", "Cliente" if is_receber else "Fornecedor"),
            Column("documento", "Documento"),
            Column("parcela", "Parcela"),
            Column("vencimento", "Vencimento", "date"),
            Column("dias", "Dias em atraso", "number"),
            Column("valor", "Valor", "money", sum_key=True),
            Column("saldo", "Saldo", "money", sum_key=True),
            Column("situacao", "Situação"),
        ]
        return make_result(
            columns,
            registros,
            sum_keys=("valor", "saldo"),
            subtitle=f"{'Contas a receber' if is_receber else 'Contas a pagar'} em aberto · "
            + (period_text(filters) if filters.get("data_ini") or filters.get("data_fim") else "Todos os vencimentos"),
            notes=["Faixas calculadas pela data de vencimento em relação a hoje."],
        )

    grouped = {}
    for item in registros:
        row = grouped.setdefault(
            item["pessoa"],
            {
                "pessoa": item["pessoa"],
                "n": 0,
                "a_vencer": Decimal("0"),
                "d30": Decimal("0"),
                "d60": Decimal("0"),
                "d90": Decimal("0"),
                "d90_mais": Decimal("0"),
                "total": Decimal("0"),
            },
        )
        row["n"] += 1
        row[item["bucket"]] += item["saldo"]
        row["total"] += item["saldo"]

    rows = sorted(grouped.values(), key=lambda r: r["total"], reverse=True)
    total = sum((row["total"] for row in rows), Decimal("0"))
    for row in rows:
        row["part"] = percent(row["total"], total)

    columns = [
        Column("pessoa", "Cliente" if is_receber else "Fornecedor"),
        Column("n", "Títulos", "number", sum_key=True),
        Column("a_vencer", "A vencer", "money", sum_key=True),
        Column("d30", "1 a 30 dias", "money", sum_key=True),
        Column("d60", "31 a 60 dias", "money", sum_key=True),
        Column("d90", "61 a 90 dias", "money", sum_key=True),
        Column("d90_mais", "Acima de 90", "money", sum_key=True),
        Column("total", "Total", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "a_vencer", "d30", "d60", "d90", "d90_mais", "total"),
        subtitle=f"Aging {'a receber' if is_receber else 'a pagar'} · "
        + (period_text(filters) if filters.get("data_ini") or filters.get("data_fim") else "Todos os vencimentos"),
        notes=["Somente títulos em aberto, parciais ou atrasados. Faixas pela data de vencimento."],
    )
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def contas_receber_aging(filters, mode):
    return _aging(filters, "R", mode)


def contas_pagar_aging(filters, mode):
    return _aging(filters, "P", mode)


def fluxo_caixa(filters, mode):
    from apps.cadastros.models import MovimentacaoCaixa

    qs = MovimentacaoCaixa.objects.select_related("tipo_pagamento", "titulo_financeiro", "caixa")
    if filters.get("data_ini"):
        qs = qs.filter(data_movimento__date__gte=filters["data_ini"])
    if filters.get("data_fim"):
        qs = qs.filter(data_movimento__date__lte=filters["data_fim"])
    if filters.get("tipo_pagamento"):
        qs = qs.filter(tipo_pagamento_id=filters["tipo_pagamento"])

    movimentos = list(qs.order_by("data_movimento"))

    if mode == "analitico":
        columns = [
            Column("data", "Data", "date"),
            Column("tipo", "Tipo"),
            Column("forma", "Forma de pagamento"),
            Column("historico", "Histórico"),
            Column("documento", "Título"),
            Column("entrada", "Entrada", "money", sum_key=True),
            Column("saida", "Saída", "money", sum_key=True),
            Column("valor", "Valor líquido", "money", sum_key=True),
        ]
        rows = []
        for mov in movimentos:
            entrada = dec(mov.valor) if mov.tipo_operacao == "E" else Decimal("0")
            saida = dec(mov.valor) if mov.tipo_operacao == "S" else Decimal("0")
            rows.append(
                {
                    "data": mov.data_movimento,
                    "tipo": mov.get_tipo_operacao_display(),
                    "forma": mov.tipo_pagamento.tipo_pagamento if mov.tipo_pagamento else "-",
                    "historico": mov.historico or "-",
                    "documento": mov.titulo_financeiro.numero_documento if mov.titulo_financeiro else "-",
                    "entrada": entrada,
                    "saida": saida,
                    "valor": entrada - saida,
                }
            )
        result = make_result(
            columns,
            rows,
            sum_keys=("entrada", "saida", "valor"),
            subtitle=f"Movimentações de caixa · {period_text(filters)}",
        )
        result.totals["saldo"] = result.totals["entrada"] - result.totals["saida"]
        return result

    agrupar = filters.get("agrupar") or "dia"
    grouped = defaultdict(lambda: {"entrada": Decimal("0"), "saida": Decimal("0")})
    for mov in movimentos:
        key = mov.data_movimento.date() if agrupar == "dia" else mov.data_movimento.date().replace(day=1)
        if mov.tipo_operacao == "E":
            grouped[key]["entrada"] += dec(mov.valor)
        else:
            grouped[key]["saida"] += dec(mov.valor)

    rows = []
    acumulado = Decimal("0")
    for key in sorted(grouped):
        entrada = grouped[key]["entrada"]
        saida = grouped[key]["saida"]
        saldo = entrada - saida
        acumulado += saldo
        rows.append(
            {
                "periodo": key,
                "entrada": entrada,
                "saida": saida,
                "saldo": saldo,
                "acumulado": acumulado,
            }
        )

    # Projeção de títulos em aberto no mesmo período
    projetado_receber = (
        titulos(filters, "R")
        .filter(situacao__in=OPEN_SITUACOES)
        .aggregate(total=Sum("valor_saldo"))["total"]
        or Decimal("0")
    )
    projetado_pagar = (
        titulos(filters, "P")
        .filter(situacao__in=OPEN_SITUACOES)
        .aggregate(total=Sum("valor_saldo"))["total"]
        or Decimal("0")
    )

    columns = [
        Column("periodo", "Dia" if agrupar == "dia" else "Mês", "date"),
        Column("entrada", "Entradas", "money", sum_key=True),
        Column("saida", "Saídas", "money", sum_key=True),
        Column("saldo", "Saldo", "money", sum_key=True),
        Column("acumulado", "Acumulado", "money"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("entrada", "saida", "saldo"),
        subtitle=f"Fluxo de caixa realizado · {period_text(filters)}",
        notes=[
            f"Projeção no período (títulos em aberto): a receber R$ {norm(projetado_receber):,.2f} · "
            f"a pagar R$ {norm(projetado_pagar):,.2f}.",
        ],
    )
    result.totals["acumulado"] = acumulado
    return result


def inadimplencia(filters, mode):
    qs = (
        titulos(filters, "R")
        .filter(situacao__in=OPEN_SITUACOES, data_vencimento__lt=today())
        .select_related("pessoa")
        .order_by("data_vencimento")
    )
    dias_minimos = filters.get("dias_minimos") or 1
    qs = qs.filter(data_vencimento__lte=today() - timedelta(days=int(dias_minimos) - 1))

    hoje = today()
    registros = []
    for titulo in qs:
        dias = (hoje - titulo.data_vencimento).days
        registros.append(
            {
                "pessoa": titulo.pessoa.nome if titulo.pessoa else "-",
                "documento": titulo.numero_documento or f"#{titulo.pk_chave}",
                "vencimento": titulo.data_vencimento,
                "dias": dias,
                "saldo": dec(titulo.valor_saldo),
            }
        )

    if mode == "analitico":
        columns = [
            Column("pessoa", "Cliente"),
            Column("documento", "Documento"),
            Column("vencimento", "Vencimento", "date"),
            Column("dias", "Dias em atraso", "number"),
            Column("saldo", "Valor vencido", "money", sum_key=True),
        ]
        return make_result(
            columns,
            registros,
            sum_keys=("saldo",),
            subtitle=f"Títulos vencidos · mais de {dias_minimos} dia(s)",
        )

    grouped = {}
    for item in registros:
        row = grouped.setdefault(
            item["pessoa"],
            {"pessoa": item["pessoa"], "n": 0, "saldo": Decimal("0"), "dias_pond": Decimal("0"), "dias_max": 0},
        )
        row["n"] += 1
        row["saldo"] += item["saldo"]
        row["dias_pond"] += item["saldo"] * item["dias"]
        row["dias_max"] = max(row["dias_max"], item["dias"])

    rows = sorted(grouped.values(), key=lambda r: r["saldo"], reverse=True)
    total = sum((row["saldo"] for row in rows), Decimal("0"))
    for row in rows:
        row["dias_medio"] = safe_div(row["dias_pond"], row["saldo"]) if row["saldo"] else Decimal("0")
        row["part"] = percent(row["saldo"], total)

    columns = [
        Column("pessoa", "Cliente"),
        Column("n", "Títulos", "number", sum_key=True),
        Column("saldo", "Valor vencido", "money", sum_key=True),
        Column("dias_medio", "Atraso médio (dias)", "number"),
        Column("dias_max", "Maior atraso (dias)", "number"),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "saldo"),
        subtitle=f"Inadimplência por cliente · vencidos há mais de {dias_minimos} dia(s)",
        notes=["O atraso médio é ponderado pelo valor de cada título."],
    )
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def contas_pagar_tipo_gasto(filters, mode):
    from apps.cadastros.models import TituloFinanceiro

    qs = TituloFinanceiro.objects.filter(tipo="P", valor_pago__gt=0)
    if filters.get("data_ini"):
        qs = qs.filter(data_pagamento__gte=filters["data_ini"])
    if filters.get("data_fim"):
        qs = qs.filter(data_pagamento__lte=filters["data_fim"])
    if filters.get("plano_contas"):
        qs = qs.filter(plano_contas_id=filters["plano_contas"])
    if filters.get("centro_custo"):
        qs = qs.filter(centro_custo_id=filters["centro_custo"])
    qs = qs.select_related("pessoa", "plano_contas", "centro_custo").order_by("data_pagamento")

    agrupar = filters.get("agrupar") or "plano"

    if mode == "analitico":
        columns = [
            Column("data", "Pagamento", "date"),
            Column("fornecedor", "Fornecedor"),
            Column("documento", "Documento"),
            Column("plano", "Plano de contas"),
            Column("centro", "Centro de custo"),
            Column("valor", "Valor pago", "money", sum_key=True),
        ]
        rows = [
            {
                "data": t.data_pagamento,
                "fornecedor": t.pessoa.nome if t.pessoa else "-",
                "documento": t.numero_documento or f"#{t.pk_chave}",
                "plano": f"{t.plano_contas.codigo} - {t.plano_contas.nome}" if t.plano_contas else "Sem plano",
                "centro": f"{t.centro_custo.codigo} - {t.centro_custo.nome}" if t.centro_custo else "Sem centro",
                "valor": dec(t.valor_pago),
            }
            for t in qs
        ]
        return make_result(columns, rows, sum_keys=("valor",), subtitle=period_text(filters))

    grouped = defaultdict(lambda: {"n": 0, "valor": Decimal("0")})
    for t in qs:
        if agrupar == "centro":
            key = f"{t.centro_custo.codigo} - {t.centro_custo.nome}" if t.centro_custo else "Sem centro de custo"
        else:
            key = f"{t.plano_contas.codigo} - {t.plano_contas.nome}" if t.plano_contas else "Sem plano de contas"
        grouped[key]["n"] += 1
        grouped[key]["valor"] += dec(t.valor_pago)

    rows = [{"grupo": key, **value} for key, value in grouped.items()]
    rows.sort(key=lambda r: r["valor"], reverse=True)
    total = sum((row["valor"] for row in rows), Decimal("0"))
    for row in rows:
        row["part"] = percent(row["valor"], total)

    columns = [
        Column("grupo", "Centro de custo" if agrupar == "centro" else "Plano de contas"),
        Column("n", "Títulos", "number", sum_key=True),
        Column("valor", "Valor pago", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "valor"),
        subtitle=f"Contas pagas · {period_text(filters)}",
        notes=["Considera títulos do tipo a pagar com valor pago no período."],
    )
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


register(
    Report(
        slug="contas-receber-aging",
        title="Contas a Receber (Aging)",
        category="financeiro",
        description="Recebíveis em aberto por faixa de vencimento, agrupados por cliente.",
        filters=[
            FilterSpec("data_ini", "Vencimento de", "date", default=None, col=2),
            FilterSpec("data_fim", "Vencimento até", "date", default=None, col=2),
            CLIENTE_TEXT,
        ],
        run=contas_receber_aging,
        supports_analitico=True,
        icon="fa-hand-holding-dollar",
        order=1,
    )
)

register(
    Report(
        slug="contas-pagar-aging",
        title="Contas a Pagar (Aging)",
        category="financeiro",
        description="Contas a pagar em aberto por faixa de vencimento, agrupadas por fornecedor.",
        filters=[
            FilterSpec("data_ini", "Vencimento de", "date", default=None, col=2),
            FilterSpec("data_fim", "Vencimento até", "date", default=None, col=2),
            CLIENTE_TEXT,
        ],
        run=contas_pagar_aging,
        supports_analitico=True,
        icon="fa-file-invoice",
        order=2,
    )
)

register(
    Report(
        slug="fluxo-caixa",
        title="Fluxo de Caixa",
        category="financeiro",
        description="Entradas e saídas realizadas no caixa, com saldo e acumulado por dia ou mês.",
        filters=[
            FilterSpec("data_ini", "Data inicial", "date", default=inicio_mes, col=2),
            FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
            FilterSpec(
                "agrupar",
                "Agrupar por",
                "select",
                choices=[("dia", "Dia"), ("mes", "Mês")],
                default="dia",
                col=2,
            ),
            FilterSpec("tipo_pagamento", "Forma de pagamento", "select", choices=tipos_pagamento_choices, col=3),
        ],
        run=fluxo_caixa,
        supports_analitico=True,
        icon="fa-money-bill-trend-up",
        order=3,
    )
)

register(
    Report(
        slug="inadimplencia",
        title="Inadimplência por Cliente",
        category="financeiro",
        description="Títulos vencidos e atraso médio por cliente.",
        filters=[
            FilterSpec("dias_minimos", "Atraso mínimo (dias)", "number", default=1, col=2),
            FilterSpec("data_ini", "Vencimento de", "date", default=None, col=2),
            FilterSpec("data_fim", "Vencimento até", "date", default=None, col=2),
            CLIENTE_TEXT,
        ],
        run=inadimplencia,
        supports_analitico=True,
        icon="fa-triangle-exclamation",
        order=4,
    )
)

register(
    Report(
        slug="contas-pagar-tipo-gasto",
        title="Contas a Pagar por Tipo de Gasto",
        category="financeiro",
        description="Para onde foi o dinheiro no período, por plano de contas ou centro de custo.",
        filters=[
            FilterSpec("data_ini", "Pagamento de", "date", default=inicio_mes, col=2),
            FilterSpec("data_fim", "Pagamento até", "date", default=hoje, col=2),
            FilterSpec(
                "agrupar",
                "Agrupar por",
                "select",
                choices=[("plano", "Plano de contas"), ("centro", "Centro de custo")],
                default="plano",
                col=2,
            ),
        ],
        run=contas_pagar_tipo_gasto,
        supports_analitico=True,
        icon="fa-chart-bar",
        order=5,
    )
)
