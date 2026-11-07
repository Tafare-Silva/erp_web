from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from django.db.models import Q
from django.utils import timezone

from apps.cadastros.models import (
    CentroCusto,
    Divisao,
    LocalEstoque,
    Marca,
    Pessoa,
    PlanoContas,
    Produto,
    TipoPagamento,
)


def hoje() -> date:
    return timezone.localdate()


def inicio_mes() -> date:
    return hoje().replace(day=1)


def inicio_ano() -> date:
    return hoje().replace(month=1, day=1)


def dias_atras(dias: int) -> date:
    return hoje() - timedelta(days=dias)


@dataclass
class FilterSpec:
    name: str
    label: str
    kind: str = "text"  # date | select | text | number
    choices: Callable[[], list[tuple[str, str]]] | list[tuple[str, str]] | None = None
    default: Any = None
    required: bool = False
    placeholder: str = ""
    help_text: str = ""
    col: int = 3
    empty_label: str = "Todos"


def _pessoa_choices(flags: dict[str, bool]) -> list[tuple[str, str]]:
    query = Q()
    for flag, active in flags.items():
        if active:
            query |= Q(**{flag: True})
    pessoas = Pessoa.objects.filter(query).order_by("nome").values_list("chave", "nome")
    return [(str(pk), nome) for pk, nome in pessoas]


def vendedores_choices() -> list[tuple[str, str]]:
    return _pessoa_choices({"vendedor": True, "funcionario": True})


def clientes_choices() -> list[tuple[str, str]]:
    return _pessoa_choices({"cliente": True})


def fornecedores_choices() -> list[tuple[str, str]]:
    return _pessoa_choices({"fornecedor": True})


def marcas_choices() -> list[tuple[str, str]]:
    return [(m.nome, m.nome) for m in Marca.objects.order_by("nome")]


def divisoes_choices() -> list[tuple[str, str]]:
    return [(d.nome, d.nome) for d in Divisao.objects.order_by("nome")]


def locais_choices() -> list[tuple[str, str]]:
    return [(l.local, l.local) for l in LocalEstoque.objects.order_by("local")]


def produtos_choices() -> list[tuple[str, str]]:
    return [
        (str(pk), f"{codigo} - {nome}" if codigo else nome)
        for pk, nome, codigo in Produto.objects.order_by("nome").values_list("pk_chave", "nome", "codigo")
    ]


def planos_contas_choices() -> list[tuple[str, str]]:
    return [
        (str(pk), f"{codigo} - {nome}")
        for pk, codigo, nome in PlanoContas.objects.order_by("codigo").values_list("chave", "codigo", "nome")
    ]


def centros_custo_choices() -> list[tuple[str, str]]:
    return [
        (str(pk), f"{codigo} - {nome}")
        for pk, codigo, nome in CentroCusto.objects.order_by("codigo").values_list("chave", "codigo", "nome")
    ]


def tipos_pagamento_choices() -> list[tuple[str, str]]:
    return [
        (str(pk), nome)
        for pk, nome in TipoPagamento.objects.order_by("tipo_pagamento").values_list("pk_tipo_pagamento", "tipo_pagamento")
    ]


def nfe_status_choices() -> list[tuple[str, str]]:
    return [
        ("DIGITACAO", "Digitação"),
        ("VALIDADO", "Validado"),
        ("ASSINADO", "Assinado"),
        ("ENVIADO", "Enviado"),
        ("AUTORIZADO", "Autorizado"),
        ("REJEITADO", "Rejeitado"),
        ("CANCELADO", "Cancelado"),
        ("DENEGADO", "Denegado"),
        ("CCE", "CC-e"),
    ]


def nfe_modelo_choices() -> list[tuple[str, str]]:
    return [("55", "NF-e (55)"), ("65", "NFC-e (65)")]


def tipo_operacao_choices() -> list[tuple[str, str]]:
    return [("1", "Saída"), ("2", "Entrada")]


def titulo_situacao_choices() -> list[tuple[str, str]]:
    return [
        ("ABERTO", "Aberto"),
        ("PARCIAL", "Parcial"),
        ("ATRASADO", "Atrasado"),
        ("PAGO", "Pago"),
        ("CANCELADO", "Cancelado"),
    ]


def parse_date(value: Any, default: date | None = None) -> date | None:
    if not value:
        return default
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return default


def parse_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    if value in (None, ""):
        return default
    text = str(value).strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def clean_value(spec: FilterSpec, value: Any) -> Any:
    if spec.kind == "date":
        return parse_date(value, None)
    if spec.kind == "number":
        return parse_int(value, None)
    if value in (None, ""):
        return None
    return str(value).strip()


def resolve_choices(spec: FilterSpec) -> list[tuple[str, str]]:
    if not spec.choices:
        return []
    choices = spec.choices() if callable(spec.choices) else spec.choices
    return list(choices)


def build_filters(specs: list[FilterSpec], data) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Aplica defaults, limpa valores e devolve (valores, campos para o template)."""
    values: dict[str, Any] = {}
    fields: list[dict[str, Any]] = []
    for spec in specs:
        raw = data.get(spec.name) if hasattr(data, "get") else None
        if raw in (None, ""):
            default = spec.default() if callable(spec.default) else spec.default
            raw = default
        value = clean_value(spec, raw)
        values[spec.name] = value
        choices = resolve_choices(spec)
        current = "" if value is None else value
        fields.append(
            {
                "spec": spec,
                "value": current,
                "choices": choices,
                "label": spec.label,
                "name": spec.name,
                "kind": spec.kind,
                "required": spec.required,
                "placeholder": spec.placeholder,
                "help_text": spec.help_text,
                "col": spec.col,
                "empty_label": spec.empty_label,
            }
        )
    return values, fields


def filter_display(spec: FilterSpec, value: Any) -> str:
    if value in (None, ""):
        return "Todos"
    if spec.kind == "date":
        return value.strftime("%d/%m/%Y") if isinstance(value, (date, datetime)) else str(value)
    if spec.kind == "number":
        return str(value)
    if spec.choices:
        for key, label in resolve_choices(spec):
            if str(key) == str(value):
                return label
    return str(value)


def build_filter_summary(specs: list[FilterSpec], values: dict[str, Any]) -> list[dict[str, str]]:
    summary = []
    for spec in specs:
        value = values.get(spec.name)
        if spec.kind == "date" or spec.kind == "select" or value not in (None, ""):
            summary.append({"label": spec.label, "value": filter_display(spec, value)})
    return summary
