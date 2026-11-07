from datetime import date, datetime
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.cadastros.models import ItemMovimentacaoEstoque, MovimentacaoEstoque, TituloFinanceiro

OPEN_SITUACOES = ("ABERTO", "ATRASADO", "PARCIAL")


def dec(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def norm(value) -> Decimal:
    return abs(dec(value))


def codigo_produto(produto) -> str:
    return produto.codigo or str(produto.pk_chave)


def safe_div(part, total) -> Decimal:
    total_d = dec(total)
    if not total_d:
        return Decimal("0")
    return (dec(part) / total_d).quantize(Decimal("0.01"))


def percent_of(part, total) -> Decimal:
    total_d = dec(total)
    if not total_d:
        return Decimal("0")
    return (dec(part) / total_d * Decimal("100")).quantize(Decimal("0.01"))


def today() -> date:
    return timezone.localdate()


def apply_period(qs, field: str, filters: dict, date_lookup: str | None = None):
    lookup = date_lookup or f"{field}__gte"
    if filters.get("data_ini"):
        qs = qs.filter(**{lookup: filters["data_ini"]})
        end_lookup = lookup.replace("__gte", "__lte")
        if filters.get("data_fim"):
            qs = qs.filter(**{end_lookup: filters["data_fim"]})
    elif filters.get("data_fim"):
        qs = qs.filter(**{field + "__lte": filters["data_fim"]})
    return qs


def sale_headers(filters: dict):
    qs = MovimentacaoEstoque.objects.filter(tipo_movimento="VE")
    qs = apply_period(qs, "data", filters, "data__gte")
    if filters.get("vendedor"):
        qs = qs.filter(vendedor_id=filters["vendedor"])
    if filters.get("cliente"):
        text = filters["cliente"]
        qs = qs.filter(Q(pessoa__nome__icontains=text) | Q(pessoa__cpf_cnpj__icontains=text))
    if filters.get("local"):
        qs = qs.filter(local_id=filters["local"])
    return qs


def sale_items(filters: dict):
    qs = ItemMovimentacaoEstoque.objects.filter(movimentacao__tipo_movimento="VE")
    qs = apply_period(qs, "movimentacao__data", filters, "movimentacao__data__gte")
    if filters.get("vendedor"):
        qs = qs.filter(movimentacao__vendedor_id=filters["vendedor"])
    if filters.get("cliente"):
        text = filters["cliente"]
        qs = qs.filter(
            Q(movimentacao__pessoa__nome__icontains=text)
            | Q(movimentacao__pessoa__cpf_cnpj__icontains=text)
        )
    if filters.get("marca"):
        qs = qs.filter(produto__marca_id=filters["marca"])
    if filters.get("divisao"):
        qs = qs.filter(produto__divisao_id=filters["divisao"])
    if filters.get("fabricante"):
        qs = qs.filter(produto__fabricante__icontains=filters["fabricante"])
    if filters.get("produto"):
        qs = qs.filter(produto_id=filters["produto"])
    if filters.get("local"):
        qs = qs.filter(Q(local_id=filters["local"]) | Q(movimentacao__local_id=filters["local"]))
    return qs


def purchase_headers(filters: dict):
    qs = MovimentacaoEstoque.objects.filter(tipo_movimento__in=["CO", "E"])
    qs = apply_period(qs, "data", filters, "data__gte")
    if filters.get("fornecedor"):
        qs = qs.filter(pessoa_id=filters["fornecedor"])
    return qs


def purchase_items(filters: dict):
    qs = ItemMovimentacaoEstoque.objects.filter(movimentacao__tipo_movimento__in=["CO", "E"])
    qs = apply_period(qs, "movimentacao__data", filters, "movimentacao__data__gte")
    if filters.get("fornecedor"):
        qs = qs.filter(movimentacao__pessoa_id=filters["fornecedor"])
    if filters.get("marca"):
        qs = qs.filter(produto__marca_id=filters["marca"])
    if filters.get("divisao"):
        qs = qs.filter(produto__divisao_id=filters["divisao"])
    if filters.get("produto"):
        qs = qs.filter(produto_id=filters["produto"])
    return qs


def titulos(filters: dict, tipo: str):
    qs = TituloFinanceiro.objects.filter(tipo=tipo)
    if filters.get("situacao"):
        qs = qs.filter(situacao=filters["situacao"])
    if filters.get("cliente"):
        cliente = str(filters["cliente"])
        if cliente.isdigit():
            qs = qs.filter(pessoa_id=cliente)
        else:
            qs = qs.filter(pessoa__nome__icontains=cliente)
    if filters.get("data_ini"):
        qs = qs.filter(data_vencimento__gte=filters["data_ini"])
    if filters.get("data_fim"):
        qs = qs.filter(data_vencimento__lte=filters["data_fim"])
    return qs


def period_text(filters: dict) -> str:
    ini = filters.get("data_ini")
    fim = filters.get("data_fim")
    if ini and fim:
        return f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}"
    if ini:
        return f"A partir de {ini:%d/%m/%Y}"
    if fim:
        return f"Até {fim:%d/%m/%Y}"
    return "Todo o período"


def as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None
