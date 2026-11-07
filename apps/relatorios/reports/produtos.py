from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Abs

from apps.cadastros.models import ItemMovimentacaoEstoque

from ..columns import Column, make_result, percent
from ..filters import FilterSpec, divisoes_choices, hoje, inicio_mes, marcas_choices
from ..helpers import dec, norm, period_text, safe_div, sale_items, today
from ..registry import Report, register
from .estoque import _saldo_expr

BASE_FILTERS = [
    FilterSpec("marca", "Marca", "select", choices=marcas_choices, col=2),
    FilterSpec("divisao", "Divisão", "select", choices=divisoes_choices, col=2),
]


def catalogo_produtos(filters, mode):
    from apps.cadastros.models import Produto

    qs = Produto.objects.all()
    if filters.get("marca"):
        qs = qs.filter(marca_id=filters["marca"])
    if filters.get("divisao"):
        qs = qs.filter(divisao_id=filters["divisao"])
    if filters.get("inativos") == "nao":
        qs = qs.filter(inativo=False)
    elif filters.get("inativos") == "somente":
        qs = qs.filter(inativo=True)
    qs = (
        qs.annotate(saldo=_saldo_expr())
        .select_related("marca", "divisao", "unidade_venda", "ncm")
        .order_by("nome")
    )

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("marca", "Marca"),
        Column("divisao", "Divisão"),
        Column("unidade", "Un."),
        Column("ncm", "NCM"),
        Column("preco", "Preço venda", "money"),
        Column("custo", "Custo", "money"),
        Column("saldo", "Estoque", "number", sum_key=True),
        Column("situacao", "Situação"),
    ]
    rows = []
    for produto in qs:
        rows.append(
            {
                "codigo": produto.codigo or "",
                "produto": produto.nome,
                "marca": produto.marca_id or "-",
                "divisao": produto.divisao_id or "-",
                "unidade": produto.unidade_venda_id or "",
                "ncm": produto.ncm_id or "-",
                "preco": dec(produto.preco_venda),
                "custo": dec(produto.custo_referencia),
                "saldo": dec(produto.saldo),
                "situacao": "Inativo" if produto.inativo else "Ativo",
            }
        )
    return make_result(
        columns,
        rows,
        sum_keys=("saldo",),
        subtitle="Catálogo de produtos",
        notes=["O catálogo traz o cadastro completo com preço, custo e saldo consolidado."],
    )


def margem_lucro(filters, mode):
    cmv_expr = ExpressionWrapper(
        F("quantidade") * F("produto__custo_referencia"),
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )
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
            Column("receita", "Receita", "money", sum_key=True),
            Column("cmv", "CMV", "money", sum_key=True),
            Column("lucro", "Lucro", "money", sum_key=True),
            Column("margem", "Margem %", "percent"),
        ]
        rows = []
        for item in items:
            receita = norm(item.vr_total_liquido)
            cmv = norm(item.quantidade) * dec(item.produto.custo_referencia)
            lucro = receita - cmv
            rows.append(
                {
                    "data": item.movimentacao.data,
                    "cliente": item.movimentacao.pessoa.nome if item.movimentacao.pessoa else "-",
                    "produto": item.produto.nome,
                    "qtd": norm(item.quantidade),
                    "receita": receita,
                    "cmv": cmv,
                    "lucro": lucro,
                    "margem": percent(lucro, receita),
                }
            )
        result = make_result(columns, rows, sum_keys=("qtd", "receita", "cmv", "lucro"), subtitle=period_text(filters))
        result.totals["margem"] = percent(result.totals["lucro"], result.totals["receita"])
        return result

    grouped = (
        sale_items(filters)
        .values("produto__pk_chave", "produto__nome", "produto__codigo", "produto__custo_referencia")
        .annotate(
            qtd=Abs(Sum("quantidade")),
            receita=Abs(Sum("vr_total_liquido")),
            cmv=Abs(Sum(cmv_expr)),
        )
        .order_by("-receita")
    )
    rows = []
    for item in grouped:
        receita = norm(item["receita"])
        cmv = norm(item["cmv"])
        qtd = norm(item["qtd"])
        lucro = receita - cmv
        rows.append(
            {
                "codigo": item["produto__codigo"] or "",
                "produto": item["produto__nome"] or "Produto removido",
                "qtd": qtd,
                "receita": receita,
                "cmv": cmv,
                "lucro": lucro,
                "margem": percent(lucro, receita),
                "lucro_unit": safe_div(lucro, qtd),
            }
        )

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("qtd", "Qtde", "number", sum_key=True),
        Column("receita", "Receita", "money", sum_key=True),
        Column("cmv", "CMV", "money", sum_key=True),
        Column("lucro", "Lucro", "money", sum_key=True),
        Column("margem", "Margem %", "percent"),
        Column("lucro_unit", "Lucro unit.", "money"),
    ]
    result = make_result(
        columns,
        rows,
        sum_keys=("qtd", "receita", "cmv", "lucro"),
        subtitle=f"Margem de lucro por produto · {period_text(filters)}",
        notes=["CMV calculado pelo custo de referência do cadastro do produto multiplicado pela quantidade vendida."],
    )
    result.totals["margem"] = percent(result.totals["lucro"], result.totals["receita"])
    result.totals["lucro_unit"] = safe_div(result.totals["lucro"], result.totals["qtd"])
    return result


def produtos_sem_movimento(filters, mode):
    from apps.cadastros.models import Produto

    dias = filters.get("dias") or 60
    cutoff = today() - timedelta(days=int(dias))
    qs = Produto.objects.all()
    if filters.get("marca"):
        qs = qs.filter(marca_id=filters["marca"])
    if filters.get("divisao"):
        qs = qs.filter(divisao_id=filters["divisao"])
    ultima_venda = (
        ItemMovimentacaoEstoque.objects.filter(
            produto_id=OuterRef("pk"), movimentacao__tipo_movimento="VE"
        )
        .order_by("-movimentacao__data")
        .values("movimentacao__data")[:1]
    )
    qs = qs.annotate(
        saldo=_saldo_expr(),
        ultima=Subquery(ultima_venda),
    ).filter(Q(ultima__lt=cutoff) | Q(ultima__isnull=True))
    if filters.get("apenas_estoque") == "sim":
        qs = qs.filter(saldo__gt=0)

    rows = []
    for produto in qs.select_related("marca", "divisao").order_by("nome"):
        saldo = dec(produto.saldo)
        custo = dec(produto.custo_referencia)
        ultima = produto.ultima
        rows.append(
            {
                "codigo": produto.codigo or "",
                "produto": produto.nome,
                "marca": produto.marca_id or "-",
                "divisao": produto.divisao_id or "-",
                "ultima": ultima,
                "dias": (today() - ultima).days if ultima else None,
                "saldo": saldo,
                "custo": custo,
                "valor": saldo * custo,
            }
        )
    rows.sort(key=lambda r: r["valor"], reverse=True)

    columns = [
        Column("codigo", "Código"),
        Column("produto", "Produto"),
        Column("marca", "Marca"),
        Column("divisao", "Divisão"),
        Column("ultima", "Última venda", "date"),
        Column("dias", "Dias sem vender", "number"),
        Column("saldo", "Estoque", "number", sum_key=True),
        Column("custo", "Custo unit.", "money"),
        Column("valor", "Valor parado", "money", sum_key=True),
    ]
    return make_result(
        columns,
        rows,
        sum_keys=("saldo", "valor"),
        subtitle=f"Produtos sem venda há mais de {dias} dias",
        notes=["Inclui produtos que nunca foram vendidos. Valor parado = saldo × custo de referência."],
    )


register(
    Report(
        slug="catalogo-produtos",
        title="Catálogo de Produtos",
        category="produtos",
        description="Listagem do cadastro de produtos com preço, custo e estoque atual.",
        filters=BASE_FILTERS
        + [
            FilterSpec(
                "inativos",
                "Situação",
                "select",
                choices=[("ativos", "Somente ativos"), ("todos", "Todos"), ("somente", "Somente inativos")],
                default="ativos",
                col=2,
            )
        ],
        run=catalogo_produtos,
        icon="fa-book",
        order=1,
    )
)

register(
    Report(
        slug="margem-lucro",
        title="Margem de Lucro por Produto",
        category="produtos",
        description="Faturamento, CMV e margem de contribuição por produto.",
        filters=[
            FilterSpec("data_ini", "Data inicial", "date", default=inicio_mes, col=2),
            FilterSpec("data_fim", "Data final", "date", default=hoje, col=2),
            *BASE_FILTERS,
        ],
        run=margem_lucro,
        supports_analitico=True,
        icon="fa-percent",
        order=2,
    )
)

register(
    Report(
        slug="produtos-sem-movimento",
        title="Produtos sem Movimento",
        category="produtos",
        description="Produtos sem venda há N dias, com o valor parado em estoque.",
        filters=[
            FilterSpec("dias", "Sem venda há (dias)", "number", default=60, col=2),
            FilterSpec(
                "apenas_estoque",
                "Somente com estoque",
                "select",
                choices=[("sim", "Sim"), ("nao", "Não")],
                default="sim",
                col=2,
            ),
            *BASE_FILTERS,
        ],
        run=produtos_sem_movimento,
        icon="fa-hourglass-half",
        order=3,
    )
)
