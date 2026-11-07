from decimal import Decimal

from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from ..columns import Column, make_result, percent
from ..filters import (
    FilterSpec,
    divisoes_choices,
    hoje,
    inicio_mes,
    locais_choices,
    marcas_choices,
    produtos_choices,
)
from ..helpers import dec, norm, safe_div
from ..registry import Report, register
from apps.cadastros.models import ItemMovimentacaoEstoque, Produto, SaldoEstoque

ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=18, decimal_places=4))


def _saldo_expr(local=None):
    if local:
        return Coalesce(
            Sum("saldos_estoque__quantidade", filter=Q(saldos_estoque__local_id=local)),
            ZERO,
            output_field=DecimalField(max_digits=18, decimal_places=4),
        )
    return Coalesce(
        Sum("saldos_estoque__quantidade"),
        ZERO,
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )


def _produtos_base(filters):
    qs = Produto.objects.all()
    if filters.get("marca"):
        qs = qs.filter(marca_id=filters["marca"])
    if filters.get("divisao"):
        qs = qs.filter(divisao_id=filters["divisao"])
    return qs


def posicao_estoque(filters, mode):
    if mode == "analitico":
        qs = SaldoEstoque.objects.select_related("produto", "local").order_by("produto__nome", "local__local")
        if filters.get("local"):
            qs = qs.filter(local_id=filters["local"])
        if filters.get("marca"):
            qs = qs.filter(produto__marca_id=filters["marca"])
        if filters.get("divisao"):
            qs = qs.filter(produto__divisao_id=filters["divisao"])
        if filters.get("incluir_zerados") != "sim":
            qs = qs.exclude(quantidade=0)
        columns = [
            Column("codigo", "Código"),
            Column("produto", "Produto"),
            Column("local", "Local"),
            Column("unidade", "Un."),
            Column("saldo", "Saldo", "number", sum_key=True),
            Column("custo", "Custo unit.", "money"),
            Column("valor", "Valor total", "money", sum_key=True),
        ]
        rows = [
            {
                "codigo": item.produto.codigo or "",
                "produto": item.produto.nome,
                "local": item.local.local,
                "unidade": item.produto.unidade_venda_id or "",
                "saldo": dec(item.quantidade),
                "custo": dec(item.produto.custo_referencia),
                "valor": dec(item.quantidade) * dec(item.produto.custo_referencia),
            }
            for item in qs
        ]
        return make_result(
            columns,
            rows,
            sum_keys=("saldo", "valor"),
            subtitle="Posição de estoque por produto e local",
        )

    produtos = _produtos_base(filters).annotate(saldo=_saldo_expr(filters.get("local")))
    if filters.get("incluir_zerados") != "sim":
        produtos = produtos.exclude(saldo=0)
    produtos = produtos.select_related("marca", "divisao", "unidade_venda").order_by("nome")

    rows = []
    for produto in produtos:
        saldo = dec(produto.saldo)
        custo = dec(produto.custo_referencia)
        minimo = dec(produto.estoque_minimo)
        if saldo <= 0:
            status = "Sem estoque"
        elif minimo and saldo < minimo:
            status = "Abaixo do mínimo"
        else:
            status = "OK"
        rows.append(
            {
                "codigo": produto.codigo or "",
                "produto": produto.nome,
                "marca": produto.marca_id or "-",
                "divisao": produto.divisao_id or "-",
                "unidade": produto.unidade_venda_id or "",
                "saldo": saldo,
                "custo": custo,
                "valor": saldo * custo,
                "minimo": minimo,
                "status": status,
            }
        )

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("marca", "Marca"),
        Column("divisao", "Divisão"),
        Column("unidade", "Un."),
        Column("saldo", "Saldo", "number", sum_key=True),
        Column("custo", "Custo unit.", "money"),
        Column("valor", "Valor total", "money", sum_key=True),
        Column("minimo", "Mínimo", "number"),
        Column("status", "Status"),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("saldo", "valor"),
        subtitle="Posição de estoque consolidada por produto",
        notes=["Saldo obtido de SaldoEstoque; valoriza pelo custo de referência do produto."],
    )


def abaixo_minimo(filters, mode):
    produtos = (
        _produtos_base(filters)
        .annotate(saldo=_saldo_expr(filters.get("local")))
        .filter(estoque_minimo__gt=0, saldo__lt=F("estoque_minimo"))
        .select_related("marca", "divisao", "unidade_venda")
        .order_by("saldo")
    )
    rows = []
    for produto in produtos:
        saldo = dec(produto.saldo)
        minimo = dec(produto.estoque_minimo)
        ponto = dec(produto.ponto_reposicao)
        sugestao = max(minimo - saldo, Decimal("0"))
        custo = dec(produto.custo_referencia)
        rows.append(
            {
                "codigo": produto.codigo or "",
                "produto": produto.nome,
                "marca": produto.marca_id or "-",
                "divisao": produto.divisao_id or "-",
                "unidade": produto.unidade_venda_id or "",
                "saldo": saldo,
                "minimo": minimo,
                "ponto": ponto,
                "sugestao": sugestao,
                "custo": custo,
                "valor": sugestao * custo,
            }
        )

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("marca", "Marca"),
        Column("divisao", "Divisão"),
        Column("unidade", "Un."),
        Column("saldo", "Saldo", "number", sum_key=True),
        Column("minimo", "Mínimo", "number", sum_key=True),
        Column("ponto", "Ponto reposição", "number"),
        Column("sugestao", "Sugestão compra", "number", sum_key=True),
        Column("custo", "Custo unit.", "money"),
        Column("valor", "Custo da reposição", "money", sum_key=True),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("saldo", "minimo", "sugestao", "valor"),
        subtitle="Produtos abaixo do estoque mínimo",
        notes=["Sugestão de compra = estoque mínimo menos saldo atual (nunca negativa)."],
    )


def curva_abc_estoque(filters, mode):
    produtos = _produtos_base(filters).annotate(saldo=_saldo_expr(filters.get("local")))
    registros = []
    for produto in produtos.select_related("marca", "divisao").order_by("nome"):
        saldo = dec(produto.saldo)
        custo = dec(produto.custo_referencia)
        registros.append(
            {
                "codigo": produto.codigo or "",
                "produto": produto.nome,
                "marca": produto.marca_id or "-",
                "divisao": produto.divisao_id or "-",
                "unidade": produto.unidade_venda_id or "",
                "saldo": saldo,
                "custo": custo,
                "valor": saldo * custo,
            }
        )
    registros.sort(key=lambda r: r["valor"], reverse=True)
    total = sum((r["valor"] for r in registros), Decimal("0"))
    acumulado = Decimal("0")
    rows = []
    for index, item in enumerate(registros, start=1):
        acumulado += item["valor"]
        acumulado_part = percent(acumulado, total)
        if acumulado_part <= 80:
            classe = "A"
        elif acumulado_part <= 95:
            classe = "B"
        else:
            classe = "C"
        rows.append(
            {
                "posicao": index,
                **item,
                "part": percent(item["valor"], total),
                "acumulado": acumulado_part,
                "classe": classe,
            }
        )

    columns = [
        Column("posicao", "#", "number"),
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("marca", "Marca"),
        Column("divisao", "Divisão"),
        Column("unidade", "Un."),
        Column("saldo", "Saldo", "number", sum_key=True),
        Column("custo", "Custo unit.", "money"),
        Column("valor", "Valor imobilizado", "money", sum_key=True),
        Column("part", "Part. %", "percent"),
        Column("acumulado", "Acum. %", "percent"),
        Column("classe", "Classe"),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("saldo", "valor"),
        subtitle="Curva ABC do estoque por valor imobilizado",
        notes=["Classe A: até 80% acumulado · B: até 95% · C: demais."],
    )


def kardex(filters, mode):
    produto_id = filters.get("produto")
    if not produto_id:
        return make_result(
            [],
            [],
            subtitle="Selecione um produto para gerar o kardex",
            notes=["O kardex mostra o histórico de movimentações de um produto e o saldo após cada movimento."],
        )

    qs = ItemMovimentacaoEstoque.objects.filter(produto_id=produto_id)
    if filters.get("local"):
        qs = qs.filter(Q(local_id=filters["local"]) | Q(movimentacao__local_id=filters["local"]))
    if filters.get("data_ini"):
        qs = qs.filter(movimentacao__data__gte=filters["data_ini"])
    if filters.get("data_fim"):
        qs = qs.filter(movimentacao__data__lte=filters["data_fim"])

    anterior = ItemMovimentacaoEstoque.objects.filter(produto_id=produto_id)
    if filters.get("local"):
        anterior = anterior.filter(Q(local_id=filters["local"]) | Q(movimentacao__local_id=filters["local"]))
    if filters.get("data_ini"):
        anterior = anterior.filter(movimentacao__data__lt=filters["data_ini"])
    saldo = dec(anterior.aggregate(total=Sum("quantidade"))["total"])

    rows = []
    for item in qs.select_related("movimentacao", "movimentacao__pessoa", "local", "movimentacao__local").order_by(
        "movimentacao__data", "movimentacao__pk_chave", "id"
    ):
        saldo += dec(item.quantidade)
        rows.append(
            {
                "data": item.movimentacao.data,
                "tipo": item.movimentacao.get_tipo_movimento_display(),
                "documento": item.movimentacao.nro_documento or f"#{item.movimentacao.pk_chave}",
                "pessoa": item.movimentacao.pessoa.nome if item.movimentacao.pessoa else "-",
                "local": (item.local or item.movimentacao.local).local if (item.local or item.movimentacao.local) else "-",
                "quantidade": dec(item.quantidade),
                "saldo": saldo,
                "custo": dec(item.vr_unitario_liquido),
                "total": dec(item.vr_total_liquido),
            }
        )

    columns = [
        Column("data", "Data", "date"),
        Column("tipo", "Tipo"),
        Column("documento", "Documento"),
        Column("pessoa", "Pessoa"),
        Column("local", "Local"),
        Column("quantidade", "Qtde", "number", sum_key=True),
        Column("saldo", "Saldo após", "number"),
        Column("custo", "Custo unit.", "money"),
        Column("total", "Total", "money", sum_key=True),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("quantidade", "total"),
        subtitle="Kardex do produto",
        notes=[
            "Quantidades de saída aparecem negativas e as de entrada positivas. "
            "O saldo após considera o saldo anterior ao período informado.",
        ],
    )


register(
    Report(
        slug="posicao-estoque",
        title="Posição de Estoque",
        category="estoque",
        description="Saldo atual por produto e local, com custo e valor imobilizado.",
        filters=[
            FilterSpec("local", "Local", "select", choices=locais_choices, col=2),
            FilterSpec("marca", "Marca", "select", choices=marcas_choices, col=2),
            FilterSpec("divisao", "Divisão", "select", choices=divisoes_choices, col=2),
            FilterSpec(
                "incluir_zerados",
                "Incluir zerados",
                "select",
                choices=[("nao", "Não"), ("sim", "Sim")],
                default="nao",
                col=2,
            ),
        ],
        run=posicao_estoque,
        supports_analitico=True,
        icon="fa-warehouse",
        order=1,
    )
)

register(
    Report(
        slug="abaixo-minimo",
        title="Abaixo do Estoque Mínimo",
        category="estoque",
        description="Produtos que precisam de reposição, com sugestão de compra e custo.",
        filters=[
            FilterSpec("local", "Local", "select", choices=locais_choices, col=2),
            FilterSpec("marca", "Marca", "select", choices=marcas_choices, col=2),
            FilterSpec("divisao", "Divisão", "select", choices=divisoes_choices, col=2),
        ],
        run=abaixo_minimo,
        icon="fa-triangle-exclamation",
        order=2,
    )
)

register(
    Report(
        slug="curva-abc-estoque",
        title="Curva ABC de Estoque",
        category="estoque",
        description="Produtos por valor imobilizado (saldo × custo), com classes A, B e C.",
        filters=[
            FilterSpec("local", "Local", "select", choices=locais_choices, col=2),
            FilterSpec("marca", "Marca", "select", choices=marcas_choices, col=2),
            FilterSpec("divisao", "Divisão", "select", choices=divisoes_choices, col=2),
        ],
        run=curva_abc_estoque,
        icon="fa-chart-simple",
        order=3,
    )
)

register(
    Report(
        slug="kardex",
        title="Kardex",
        category="estoque",
        description="Histórico de movimentações de um produto, com saldo após cada lançamento.",
        filters=[
            FilterSpec("produto", "Produto", "select", choices=produtos_choices, required=True, col=5),
            FilterSpec("local", "Local", "select", choices=locais_choices, col=2),
            FilterSpec("data_ini", "Data inicial", "date", default=inicio_mes, col=2),
            FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
        ],
        run=kardex,
        icon="fa-clock-rotate-left",
        order=4,
    )
)
