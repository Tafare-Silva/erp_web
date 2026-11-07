from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    kind: str = "text"  # text | money | number | percent | date
    align: str = ""
    sum_key: bool = False
    width: int | None = None

    @property
    def align_class(self) -> str:
        if self.align:
            return self.align
        return "right" if self.is_numeric else "left"

    @property
    def is_numeric(self) -> bool:
        return self.kind in ("money", "number", "percent")


@dataclass
class ReportResult:
    columns: list[Column]
    rows: list[dict[str, Any]]
    totals: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    subtitle: str = ""


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def format_money(value: Any) -> str:
    number = _to_decimal(value).quantize(Decimal("0.01"))
    formatted = f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def format_number(value: Any, decimals: int = 2) -> str:
    number = _to_decimal(value)
    formatted = f"{number:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(",")
    return formatted or "0"


def format_percent(value: Any) -> str:
    number = _to_decimal(value)
    return f"{number:.2f}".replace(".", ",") + "%"


def format_date(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def format_value(value: Any, kind: str = "text") -> str:
    if kind == "money":
        return format_money(value)
    if kind == "number":
        return format_number(value)
    if kind == "percent":
        return format_percent(value)
    if kind == "date":
        return format_date(value)
    if value is None:
        return "-"
    return str(value)


def export_value(value: Any, kind: str = "text") -> str:
    """Valor para CSV/planilha: números com vírgula decimal e sem milhar."""
    if kind == "money":
        return f"{_to_decimal(value):.2f}".replace(".", ",")
    if kind == "number":
        number = _to_decimal(value)
        text = f"{number:.4f}".rstrip("0").rstrip(".")
        return text.replace(".", ",") if text else "0"
    if kind == "percent":
        return f"{_to_decimal(value):.2f}".replace(".", ",")
    if kind == "date":
        return format_date(value) if value else ""
    if value is None:
        return ""
    return str(value)


def make_result(
    columns: list[Column],
    rows: list[dict[str, Any]],
    sum_keys: tuple[str, ...] = (),
    notes: list[str] | None = None,
    subtitle: str = "",
) -> ReportResult:
    totals: dict[str, Any] = {}
    for key in sum_keys:
        totals[key] = sum((_to_decimal(row.get(key)) for row in rows), Decimal("0"))
    return ReportResult(
        columns=columns,
        rows=rows,
        totals=totals,
        notes=notes or [],
        subtitle=subtitle,
    )


def percent(part: Any, total: Any) -> Decimal:
    total_d = _to_decimal(total)
    if not total_d:
        return Decimal("0")
    return (_to_decimal(part) / total_d * Decimal("100")).quantize(Decimal("0.01"))


def safe_div(part: Any, total: Any) -> Decimal:
    total_d = _to_decimal(total)
    if not total_d:
        return Decimal("0")
    return (_to_decimal(part) / total_d).quantize(Decimal("0.01"))
