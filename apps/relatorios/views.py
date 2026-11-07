from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from .columns import format_value
from .export import build_csv, build_pdf, build_xlsx, safe_filename
from .filters import build_filter_summary, build_filters
from .models import ExportacaoRelatorio
from .registry import all_reports, get_report, reports_by_category
from apps.core.context_processors import branding

PREVIEW_LIMIT = 1000


def _get_report(slug: str):
    report = get_report(slug)
    if not report:
        raise Http404("Relatório não encontrado.")
    return report


def _check_permission(request, report):
    if report.permission and not request.user.has_perm(report.permission):
        raise PermissionDenied


def _mode(report, request):
    if report.supports_analitico and request.GET.get("modelo") == "analitico":
        return "analitico"
    return "sintetico"


def _mode_label(mode: str) -> str:
    return "Analítico" if mode == "analitico" else "Sintético"


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _common_context(request, report, mode):
    filters, fields = build_filters(report.filters, request.GET)
    result = report.run(filters, mode)
    filters_summary = build_filter_summary(report.filters, filters)

    params = request.GET.copy()
    params.pop("formato", None)
    query_string = params.urlencode()

    mode_params = request.GET.copy()
    mode_params.pop("formato", None)
    mode_params.pop("modelo", None)
    mode_query = mode_params.urlencode()

    totals_display = {
        column.key: format_value(result.totals.get(column.key), column.kind)
        for column in result.columns
        if column.key in result.totals
    }

    return {
        "report": report,
        "result": result,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "fields": fields,
        "filters": filters,
        "filters_summary": filters_summary,
        "query_string": query_string,
        "mode_query": mode_query,
        "totals_display": totals_display,
        "generated_at": timezone.localtime(),
        "brand_name_report": None,
        "all_reports_count": len(all_reports()),
    }


class RelatorioIndexView(LoginRequiredMixin, View):
    def get(self, request):
        reports = all_reports()
        recentes = ExportacaoRelatorio.objects.filter(usuario=request.user)[:5]
        return render(
            request,
            "relatorios/index.html",
            {
                "groups": reports_by_category(),
                "total_reports": len(reports),
                "recentes": recentes,
            },
        )


class RelatorioDetailView(LoginRequiredMixin, View):
    def get(self, request, slug):
        report = _get_report(slug)
        _check_permission(request, report)
        mode = _mode(report, request)
        context = _common_context(request, report, mode)
        context["preview_limit"] = PREVIEW_LIMIT
        context["rows_display"] = context["result"].rows[:PREVIEW_LIMIT]
        context["total_rows"] = len(context["result"].rows)
        context["truncated"] = context["total_rows"] > PREVIEW_LIMIT
        return render(request, "relatorios/report.html", context)


class RelatorioPrintView(LoginRequiredMixin, View):
    def get(self, request, slug):
        report = _get_report(slug)
        _check_permission(request, report)
        mode = _mode(report, request)
        context = _common_context(request, report, mode)
        context["rows_display"] = context["result"].rows
        context["total_rows"] = len(context["result"].rows)
        context["truncated"] = False
        return render(request, "relatorios/print.html", context)


class RelatorioExportView(LoginRequiredMixin, View):
    def get(self, request, slug):
        report = _get_report(slug)
        _check_permission(request, report)
        formato = request.GET.get("formato", "csv")
        if formato not in ("csv", "xlsx", "pdf"):
            raise Http404("Formato de exportação inválido.")

        mode = _mode(report, request)
        context = _common_context(request, report, mode)
        result = context["result"]
        generated_at = timezone.localtime()
        brand = branding(request)
        meta = {
            "title": report.title,
            "subtitle": result.subtitle,
            "mode_label": _mode_label(mode),
            "filters_summary": context["filters_summary"],
            "brand_name": brand.get("brand_name") or "",
            "brand_color": brand.get("brand_color") or "#0F1E36",
            "generated_at": generated_at.strftime("%d/%m/%Y %H:%M"),
        }

        if formato == "csv":
            content = build_csv(result)
            content_type = "text/csv; charset=utf-8"
        elif formato == "xlsx":
            content = build_xlsx(result, meta)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content = build_pdf(result, meta)
            content_type = "application/pdf"

        ExportacaoRelatorio.objects.create(
            relatorio=report.slug,
            titulo=report.title,
            formato=formato,
            modelo=mode,
            filtros=_json_safe(context["filters"]),
            total_linhas=len(result.rows),
            usuario=request.user,
        )

        extension = {"csv": "csv", "xlsx": "xlsx", "pdf": "pdf"}[formato]
        filename = f"{safe_filename(report.title)}-{generated_at:%Y%m%d-%H%M}.{extension}"
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
