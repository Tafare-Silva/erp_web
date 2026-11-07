import traceback

from django.core.management.base import BaseCommand

from apps.cadastros.models import Produto
from apps.relatorios.export import build_csv, build_pdf, build_xlsx
from apps.relatorios.filters import build_filters, build_filter_summary
from apps.relatorios.registry import all_reports


class Command(BaseCommand):
    help = "Executa todos os relatórios e exportações para validar o módulo."

    def handle(self, *args, **options):
        failures = 0
        total = 0
        for report in all_reports():
            modes = ["sintetico"]
            if report.supports_analitico:
                modes.append("analitico")
            for mode in modes:
                total += 1
                try:
                    filters, _ = build_filters(report.filters, {})
                    if report.slug == "kardex" and not filters.get("produto"):
                        primeiro = Produto.objects.values_list("pk_chave", flat=True).first()
                        filters["produto"] = str(primeiro) if primeiro else None
                    result = report.run(filters, mode)
                    meta = {
                        "title": report.title,
                        "subtitle": result.subtitle,
                        "mode_label": mode,
                        "filters_summary": build_filter_summary(report.filters, filters),
                        "brand_name": "Validacao",
                        "generated_at": "01/01/2026 00:00",
                    }
                    csv_bytes = build_csv(result)
                    xlsx_bytes = build_xlsx(result, meta)
                    pdf_bytes = build_pdf(result, meta)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"OK  {report.slug:32} {mode:10} linhas={len(result.rows):5} "
                            f"csv={len(csv_bytes):7} xlsx={len(xlsx_bytes):7} pdf={len(pdf_bytes):7}"
                        )
                    )
                except Exception:
                    failures += 1
                    self.stderr.write(self.style.ERROR(f"ERRO {report.slug} ({mode})"))
                    traceback.print_exc()

        if failures:
            self.stderr.write(self.style.ERROR(f"{failures} de {total} execuções falharam."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Todos os {total} relatórios/exportações passaram."))
