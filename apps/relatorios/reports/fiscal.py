from decimal import Decimal

from django.db.models import Count, Sum

from ..columns import Column, make_result, percent
from ..filters import (
    FilterSpec,
    hoje,
    inicio_mes,
    nfe_modelo_choices,
    nfe_status_choices,
    tipo_operacao_choices,
)
from ..helpers import dec, norm, period_text, safe_div
from ..registry import Report, register
from apps.fiscal.models import NFe, NFeItem

PERIOD_FILTERS = [
    FilterSpec("data_ini", "Emissão de", "date", default=inicio_mes, col=2),
    FilterSpec("data_fim", "Emissão até", "date", default=hoje, col=2),
]

STATUS_FILTER = FilterSpec("status", "Status", "select", choices=nfe_status_choices, col=2)
MODELO_FILTER = FilterSpec("modelo", "Modelo", "select", choices=nfe_modelo_choices, col=2)
OPERACAO_FILTER = FilterSpec("tipo_operacao", "Operação", "select", choices=tipo_operacao_choices, col=2)


def _nfe_qs(filters, tipo_operacao=None):
    qs = NFe.objects.select_related("destinatario", "movimentacao", "movimentacao__pessoa", "empresa")
    if filters.get("data_ini"):
        qs = qs.filter(data_emissao__date__gte=filters["data_ini"])
    if filters.get("data_fim"):
        qs = qs.filter(data_emissao__date__lte=filters["data_fim"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("modelo"):
        qs = qs.filter(modelo=filters["modelo"])
    if tipo_operacao is not None:
        qs = qs.filter(tipo_operacao=tipo_operacao)
    elif filters.get("tipo_operacao"):
        qs = qs.filter(tipo_operacao=filters["tipo_operacao"])
    return qs


def _contraparte(nfe):
    if nfe.tipo_operacao == "2" and nfe.movimentacao and nfe.movimentacao.pessoa:
        return nfe.movimentacao.pessoa.nome
    if nfe.tipo_operacao == "2":
        return nfe.destinatario.nome if nfe.destinatario else "-"
    return nfe.destinatario.nome if nfe.destinatario else "-"


def nfe_emitidas(filters, mode):
    qs = _nfe_qs(filters, tipo_operacao="1").order_by("-data_emissao")
    if mode == "analitico":
        columns = [
            Column("numero", "Número"),
            Column("serie", "Série"),
            Column("modelo", "Modelo"),
            Column("emissao", "Emissão", "date"),
            Column("destinatario", "Destinatário"),
            Column("valor", "Valor total", "money", sum_key=True),
            Column("icms", "ICMS", "money", sum_key=True),
            Column("status", "Status"),
        ]
        rows = [
            {
                "numero": nfe.numero,
                "serie": nfe.serie,
                "modelo": nfe.get_modelo_display(),
                "emissao": nfe.data_emissao,
                "destinatario": nfe.destinatario.nome if nfe.destinatario else "-",
                "valor": dec(nfe.valor_total),
                "icms": dec(nfe.valor_icms),
                "status": nfe.get_status_display(),
            }
            for nfe in qs
        ]
        return make_result(columns, rows, sum_keys=("valor", "icms"), subtitle=period_text(filters))

    grouped = qs.values("status").annotate(
        n=Count("id"),
        valor=Sum("valor_total"),
        icms=Sum("valor_icms"),
        ipi=Sum("valor_ipi"),
        pis=Sum("valor_pis"),
        cofins=Sum("valor_cofins"),
    ).order_by("status")
    rows = [
        {
            "status": dict(nfe_status_choices()).get(item["status"], item["status"]),
            "n": item["n"],
            "valor": dec(item["valor"]),
            "icms": dec(item["icms"]),
            "ipi": dec(item["ipi"]),
            "pis": dec(item["pis"]),
            "cofins": dec(item["cofins"]),
        }
        for item in grouped
    ]
    columns = [
        Column("status", "Status"),
        Column("n", "Notas", "number", sum_key=True),
        Column("valor", "Valor total", "money", sum_key=True),
        Column("icms", "ICMS", "money", sum_key=True),
        Column("ipi", "IPI", "money", sum_key=True),
        Column("pis", "PIS", "money", sum_key=True),
        Column("cofins", "COFINS", "money", sum_key=True),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("n", "valor", "icms", "ipi", "pis", "cofins"),
        subtitle=f"NF-e e NFC-e emitidas · {period_text(filters)}",
        notes=["Para apuração de receita considere apenas as notas com status Autorizado."],
    )


def nfe_recebidas(filters, mode):
    qs = _nfe_qs(filters, tipo_operacao="2").order_by("-data_emissao")
    if mode == "analitico":
        columns = [
            Column("numero", "Número"),
            Column("serie", "Série"),
            Column("emissao", "Emissão", "date"),
            Column("fornecedor", "Fornecedor"),
            Column("valor", "Valor total", "money", sum_key=True),
            Column("icms", "ICMS", "money", sum_key=True),
            Column("ipi", "IPI", "money", sum_key=True),
            Column("status", "Status"),
        ]
        rows = [
            {
                "numero": nfe.numero,
                "serie": nfe.serie,
                "emissao": nfe.data_emissao,
                "fornecedor": _contraparte(nfe),
                "valor": dec(nfe.valor_total),
                "icms": dec(nfe.valor_icms),
                "ipi": dec(nfe.valor_ipi),
                "status": nfe.get_status_display(),
            }
            for nfe in qs
        ]
        return make_result(columns, rows, sum_keys=("valor", "icms", "ipi"), subtitle=period_text(filters))

    grouped = {}
    for nfe in qs:
        key = _contraparte(nfe)
        row = grouped.setdefault(
            key, {"fornecedor": key, "n": 0, "valor": Decimal("0"), "icms": Decimal("0"), "ipi": Decimal("0")}
        )
        row["n"] += 1
        row["valor"] += dec(nfe.valor_total)
        row["icms"] += dec(nfe.valor_icms)
        row["ipi"] += dec(nfe.valor_ipi)
    rows = sorted(grouped.values(), key=lambda r: r["valor"], reverse=True)
    total = sum((r["valor"] for r in rows), Decimal("0"))
    for row in rows:
        row["part"] = percent(row["valor"], total)

    columns = [
        Column("fornecedor", "Fornecedor"),
        Column("n", "Notas", "number", sum_key=True),
        Column("valor", "Valor total", "money", sum_key=True),
        Column("icms", "ICMS", "money", sum_key=True),
        Column("ipi", "IPI", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "valor", "icms", "ipi"),
        subtitle=f"NF-e recebidas (entrada) · {period_text(filters)}",
    )
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def documentos_fiscais(filters, mode):
    qs = _nfe_qs(filters)
    item_qs = NFeItem.objects.filter(nfe__in=qs).select_related("nfe", "produto")

    if mode == "analitico":
        columns = [
            Column("emissao", "Emissão", "date"),
            Column("numero", "Nota"),
            Column("tipo", "Operação"),
            Column("cfop", "CFOP"),
            Column("ncm", "NCM"),
            Column("produto", "Produto"),
            Column("cst", "CST/CSOSN"),
            Column("qtd", "Qtde", "number", sum_key=True),
            Column("valor", "Valor", "money", sum_key=True),
            Column("icms", "ICMS", "money", sum_key=True),
            Column("ipi", "IPI", "money", sum_key=True),
            Column("pis", "PIS", "money", sum_key=True),
            Column("cofins", "COFINS", "money", sum_key=True),
        ]
        rows = []
        for item in item_qs.order_by("nfe__data_emissao", "nfe_id", "numero_item"):
            rows.append(
                {
                    "emissao": item.nfe.data_emissao,
                    "numero": f"{item.nfe.serie}/{item.nfe.numero}",
                    "tipo": item.nfe.get_tipo_operacao_display(),
                    "cfop": item.cfop or "-",
                    "ncm": item.ncm or "-",
                    "produto": item.nome or (item.produto.nome if item.produto else "-"),
                    "cst": item.csosn or item.cst_icms or "-",
                    "qtd": dec(item.quantidade),
                    "valor": dec(item.valor_total),
                    "icms": dec(item.valor_icms),
                    "ipi": dec(item.valor_ipi),
                    "pis": dec(item.valor_pis),
                    "cofins": dec(item.valor_cofins),
                }
            )
        return make_result(
            columns,
            rows,
            sum_keys=("qtd", "valor", "icms", "ipi", "pis", "cofins"),
            subtitle=f"Documentos fiscais analíticos · {period_text(filters)}",
        )

    grouped = (
        item_qs.values("cfop")
        .annotate(
            n=Count("id"),
            qtd=Sum("quantidade"),
            valor=Sum("valor_total"),
            icms=Sum("valor_icms"),
            ipi=Sum("valor_ipi"),
            pis=Sum("valor_pis"),
            cofins=Sum("valor_cofins"),
        )
        .order_by("-valor")
    )
    rows = []
    total = Decimal("0")
    for item in grouped:
        valor = dec(item["valor"])
        total += valor
        rows.append(
            {
                "cfop": item["cfop"] or "-",
                "n": item["n"],
                "qtd": dec(item["qtd"]),
                "valor": valor,
                "icms": dec(item["icms"]),
                "ipi": dec(item["ipi"]),
                "pis": dec(item["pis"]),
                "cofins": dec(item["cofins"]),
                "part": percent(valor, total) if total else Decimal("0"),
            }
        )
    for row in rows:
        row["part"] = percent(row["valor"], total)

    columns = [
        Column("cfop", "CFOP"),
        Column("n", "Itens", "number", sum_key=True),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("valor", "Valor", "money", sum_key=True),
        Column("icms", "ICMS", "money", sum_key=True),
        Column("ipi", "IPI", "money", sum_key=True),
        Column("pis", "PIS", "money", sum_key=True),
        Column("cofins", "COFINS", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("n", "qtd", "valor", "icms", "ipi", "pis", "cofins"),
        subtitle=f"Documentos fiscais por CFOP · {period_text(filters)}",
        notes=["Somatórios pelos itens das notas. Status padrão: Autorizado."],
    )
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def produtos_documento_fiscal(filters, mode):
    filters = {**filters, "status": filters.get("status") or "AUTORIZADO"}
    qs = _nfe_qs(filters, tipo_operacao="1")
    item_qs = NFeItem.objects.filter(nfe__in=qs).select_related("nfe", "produto")

    if mode == "analitico":
        columns = [
            Column("emissao", "Emissão", "date"),
            Column("nota", "Nota"),
            Column("cfop", "CFOP"),
            Column("ncm", "NCM"),
            Column("produto", "Produto"),
            Column("cst", "CST/CSOSN"),
            Column("qtd", "Qtde", "number", sum_key=True),
            Column("valor", "Valor", "money", sum_key=True),
            Column("icms", "ICMS", "money", sum_key=True),
            Column("ipi", "IPI", "money", sum_key=True),
        ]
        rows = [
            {
                "emissao": item.nfe.data_emissao,
                "nota": f"{item.nfe.serie}/{item.nfe.numero}",
                "cfop": item.cfop or "-",
                "ncm": item.ncm or "-",
                "produto": item.nome or (item.produto.nome if item.produto else "-"),
                "cst": item.csosn or item.cst_icms or "-",
                "qtd": dec(item.quantidade),
                "valor": dec(item.valor_total),
                "icms": dec(item.valor_icms),
                "ipi": dec(item.valor_ipi),
            }
            for item in item_qs.order_by("nfe__data_emissao", "numero_item")
        ]
        return make_result(
            columns,
            rows,
            sum_keys=("qtd", "valor", "icms", "ipi"),
            subtitle=f"Produtos vendidos com documento fiscal · {period_text(filters)}",
        )

    grouped = (
        item_qs.values("produto__pk_chave", "produto__nome", "codigo_produto", "ncm", "cfop")
        .annotate(qtd=Sum("quantidade"), valor=Sum("valor_total"), icms=Sum("valor_icms"), ipi=Sum("valor_ipi"))
        .order_by("-valor")
    )
    rows = []
    total = Decimal("0")
    for item in grouped:
        valor = dec(item["valor"])
        total += valor
        rows.append(
            {
                "codigo": item["codigo_produto"] or "",
                "produto": item["produto__nome"] or "-",
                "ncm": item["ncm"] or "-",
                "cfop": item["cfop"] or "-",
                "qtd": dec(item["qtd"]),
                "valor": valor,
                "icms": dec(item["icms"]),
                "ipi": dec(item["ipi"]),
            }
        )
    for row in rows:
        row["part"] = percent(row["valor"], total)

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("ncm", "NCM"),
        Column("cfop", "CFOP"),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("valor", "Valor", "money", sum_key=True),
        Column("icms", "ICMS", "money", sum_key=True),
        Column("ipi", "IPI", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("qtd", "valor", "icms", "ipi"),
        subtitle=f"Produtos com nota autorizada · {period_text(filters)}",
    )
    result.totals["part"] = Decimal("100") if total else Decimal("0")
    return result


def resumo_tributos(filters, mode):
    qs = _nfe_qs(filters)
    if not filters.get("status"):
        qs = qs.filter(status="AUTORIZADO")

    if mode == "analitico":
        columns = [
            Column("emissao", "Emissão", "date"),
            Column("nota", "Nota"),
            Column("tipo", "Operação"),
            Column("contraparte", "Destinatário / Fornecedor"),
            Column("valor", "Valor total", "money", sum_key=True),
            Column("icms", "ICMS", "money", sum_key=True),
            Column("icms_st", "ICMS ST", "money", sum_key=True),
            Column("ipi", "IPI", "money", sum_key=True),
            Column("pis", "PIS", "money", sum_key=True),
            Column("cofins", "COFINS", "money", sum_key=True),
        ]
        rows = [
            {
                "emissao": nfe.data_emissao,
                "nota": f"{nfe.serie}/{nfe.numero}",
                "tipo": nfe.get_tipo_operacao_display(),
                "contraparte": _contraparte(nfe),
                "valor": dec(nfe.valor_total),
                "icms": dec(nfe.valor_icms),
                "icms_st": dec(nfe.valor_icms_st),
                "ipi": dec(nfe.valor_ipi),
                "pis": dec(nfe.valor_pis),
                "cofins": dec(nfe.valor_cofins),
            }
            for nfe in qs.order_by("data_emissao")
        ]
        return make_result(
            columns,
            rows,
            sum_keys=("valor", "icms", "icms_st", "ipi", "pis", "cofins"),
            subtitle=f"Resumo de tributos analítico · {period_text(filters)}",
        )

    tributos = [
        ("ICMS", "valor_icms"),
        ("ICMS ST", "valor_icms_st"),
        ("IPI", "valor_ipi"),
        ("PIS", "valor_pis"),
        ("COFINS", "valor_cofins"),
    ]
    rows = []
    for label, field in tributos:
        debito = qs.filter(tipo_operacao="1").aggregate(total=Sum(field))["total"] or Decimal("0")
        credito = qs.filter(tipo_operacao="2").aggregate(total=Sum(field))["total"] or Decimal("0")
        rows.append(
            {
                "tributo": label,
                "debito": dec(debito),
                "credito": dec(credito),
                "saldo": dec(debito) - dec(credito),
            }
        )
    columns = [
        Column("tributo", "Tributo"),
        Column("debito", "Débito (saídas)", "money", sum_key=True),
        Column("credito", "Crédito (entradas)", "money", sum_key=True),
        Column("saldo", "Saldo gerencial", "money", sum_key=True),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("debito", "credito", "saldo"),
        subtitle=f"Resumo de tributos · {period_text(filters)}",
        notes=[
            "Valores destacados nas notas autorizadas. Apuração gerencial: não substitui o SPED.",
            "Débitos das saídas menos créditos das entradas.",
        ],
    )


register(
    Report(
        slug="nfe-emitidas",
        title="NF-e Emitidas",
        category="fiscal",
        description="NF-e e NFC-e emitidas no período, por status, com tributos destacados.",
        filters=PERIOD_FILTERS + [STATUS_FILTER, MODELO_FILTER],
        run=nfe_emitidas,
        supports_analitico=True,
        icon="fa-file-export",
        order=1,
    )
)

register(
    Report(
        slug="nfe-recebidas",
        title="NF-e Recebidas",
        category="fiscal",
        description="Notas fiscais de entrada lançadas no período, com impostos.",
        filters=PERIOD_FILTERS + [STATUS_FILTER],
        run=nfe_recebidas,
        supports_analitico=True,
        icon="fa-file-import",
        order=2,
    )
)

register(
    Report(
        slug="documentos-fiscais",
        title="Documentos Fiscais",
        category="fiscal",
        description="Todos os documentos fiscais do período, com tributos por CFOP (sintético e analítico).",
        filters=PERIOD_FILTERS + [OPERACAO_FILTER, STATUS_FILTER],
        run=documentos_fiscais,
        supports_analitico=True,
        icon="fa-file-invoice",
        order=3,
    )
)

register(
    Report(
        slug="produtos-documento-fiscal",
        title="Produtos Vendidos com Documento Fiscal",
        category="fiscal",
        description="Produtos que saíram com nota autorizada, com NCM, CFOP e tributos do item.",
        filters=PERIOD_FILTERS + [STATUS_FILTER],
        run=produtos_documento_fiscal,
        supports_analitico=True,
        icon="fa-receipt",
        order=4,
    )
)

register(
    Report(
        slug="resumo-tributos",
        title="Resumo de Tributos por Período",
        category="fiscal",
        description="Débito × crédito por tributo e o saldo gerencial do período.",
        filters=PERIOD_FILTERS + [STATUS_FILTER],
        run=resumo_tributos,
        supports_analitico=True,
        icon="fa-scale-balanced",
        order=5,
    )
)
