from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.RelatorioIndexView.as_view(), name="index"),
    path("<slug:slug>/", views.RelatorioDetailView.as_view(), name="report"),
    path("<slug:slug>/exportar/", views.RelatorioExportView.as_view(), name="export"),
    path("<slug:slug>/imprimir/", views.RelatorioPrintView.as_view(), name="print"),
]
