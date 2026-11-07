from dataclasses import dataclass, field
from typing import Callable

from .columns import ReportResult
from .filters import FilterSpec

CATEGORIES: list[dict[str, str]] = [
    {
        "slug": "vendas",
        "title": "Vendas",
        "icon": "fa-cash-register",
        "description": "Faturamento, evolução, ranking de clientes, curva ABC e produtos vendidos.",
    },
    {
        "slug": "clientes",
        "title": "Clientes",
        "icon": "fa-users",
        "description": "Carteira, inativos, positivados, limite de crédito e comportamento de compra.",
    },
    {
        "slug": "financeiro",
        "title": "Financeiro",
        "icon": "fa-coins",
        "description": "Contas a receber e a pagar, aging, inadimplência e fluxo de caixa.",
    },
    {
        "slug": "estoque",
        "title": "Estoque",
        "icon": "fa-boxes-stacked",
        "description": "Posição, estoque mínimo, curva ABC e kardex.",
    },
    {
        "slug": "produtos",
        "title": "Produtos",
        "icon": "fa-tags",
        "description": "Catálogo, margem de lucro e produtos sem movimento.",
    },
    {
        "slug": "compras",
        "title": "Compras",
        "icon": "fa-truck-fast",
        "description": "Compras por fornecedor e por produto.",
    },
    {
        "slug": "fiscal",
        "title": "Fiscal",
        "icon": "fa-file-invoice-dollar",
        "description": "NF-e emitidas e recebidas, documentos fiscais e resumo de tributos.",
    },
]

_SLUGS = {category["slug"] for category in CATEGORIES}


@dataclass
class Report:
    slug: str
    title: str
    category: str
    description: str
    filters: list[FilterSpec]
    run: Callable[[dict, str], ReportResult]
    supports_analitico: bool = False
    icon: str = "fa-chart-line"
    permission: str | None = None
    order: int = 0

    @property
    def category_title(self) -> str:
        for category in CATEGORIES:
            if category["slug"] == self.category:
                return category["title"]
        return self.category

    @property
    def url_name(self) -> str:
        return "relatorios:report"


_REGISTRY: dict[str, Report] = {}


def register(report: Report) -> Report:
    if report.category not in _SLUGS:
        raise ValueError(f"Categoria inválida no relatório {report.slug}: {report.category}")
    if report.slug in _REGISTRY:
        raise ValueError(f"Relatório duplicado: {report.slug}")
    _REGISTRY[report.slug] = report
    return report


def get_report(slug: str) -> Report | None:
    _load_reports()
    return _REGISTRY.get(slug)


def all_reports() -> list[Report]:
    _load_reports()
    return sorted(_REGISTRY.values(), key=lambda r: (r.category, r.order, r.title))


def reports_by_category() -> list[dict]:
    _load_reports()
    grouped: list[dict] = []
    reports = all_reports()
    for category in CATEGORIES:
        items = [r for r in reports if r.category == category["slug"]]
        if items:
            grouped.append({**category, "reports": items})
    return grouped


_loaded = False


def _load_reports() -> None:
    global _loaded
    if _loaded:
        return
    from .reports import load_all  # noqa: F401

    load_all()
    _loaded = True
