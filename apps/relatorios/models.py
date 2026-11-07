from django.conf import settings
from django.db import models


class ExportacaoRelatorio(models.Model):
    FORMATO_CHOICES = [
        ("csv", "CSV"),
        ("xlsx", "Excel (XLSX)"),
        ("pdf", "PDF"),
    ]

    relatorio = models.CharField(max_length=120)
    titulo = models.CharField(max_length=255)
    formato = models.CharField(max_length=10, choices=FORMATO_CHOICES)
    modelo = models.CharField(max_length=20, default="sintetico")
    filtros = models.JSONField(default=dict, blank=True)
    total_linhas = models.PositiveIntegerField(default=0)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exportacoes_relatorios",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "relatorios_exportacoes"
        ordering = ["-criado_em"]
        verbose_name = "Exportação de relatório"
        verbose_name_plural = "Exportações de relatórios"

    def __str__(self):
        return f"{self.titulo} ({self.formato}) em {self.criado_em:%d/%m/%Y %H:%M}"
