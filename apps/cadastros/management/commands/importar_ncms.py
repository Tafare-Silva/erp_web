"""
Importa a tabela completa de NCM (Nomenclatura Comum do Mercosul).

Aceita CSV (separado por ';' ou ',') ou XLSX/XLSM, de arquivo local ou URL.

Uso:
    python manage.py importar_ncms --arquivo data/ncm.csv
    python manage.py importar_ncms --url https://exemplo/ncm.xlsx
    python manage.py importar_ncms            # procura data/ncm.csv ou data/ncm.xlsx

Formato esperado (cabeçalho flexível): uma coluna com o código de 8 dígitos
(ex.: "NCM", "Codigo", "Código", "Code") e uma coluna de descrição
(ex.: "Descrição", "Descricao", "Desc", "Nome").
"""
import csv
import io
import os
import re

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.cadastros.models import NCM


CAMPOS_CODIGO = ('ncm', 'codigo', 'código', 'code', 'cod')
CAMPOS_DESCRICAO = ('descricao', 'descrição', 'desc', 'nome', 'texto')


def _normalizar(texto):
    return re.sub(r'[^a-z]', '', (texto or '').lower())


def _detectar_colunas(cabecalho):
    idx_codigo = idx_desc = None
    for i, nome in enumerate(cabecalho):
        chave = _normalizar(nome)
        if idx_codigo is None and any(c in chave for c in CAMPOS_CODIGO):
            idx_codigo = i
        if idx_desc is None and any(c in chave for c in CAMPOS_DESCRICAO):
            idx_desc = i
    return idx_codigo, idx_desc


class Command(BaseCommand):
    help = 'Importa a tabela completa de NCM a partir de CSV/XLSX (arquivo local ou URL).'

    def add_arguments(self, parser):
        parser.add_argument('--arquivo', dest='arquivo', help='Caminho do arquivo CSV/XLSX.')
        parser.add_argument('--url', dest='url', help='URL para baixar o arquivo CSV/XLSX.')

    def handle(self, *args, **options):
        arquivo = options.get('arquivo')
        url = options.get('url')

        if not arquivo and not url:
            for candidato in ('data/ncm.csv', 'data/ncm.xlsx', 'data/NCM.csv', 'data/NCM.xlsx'):
                caminho = os.path.join(settings.BASE_DIR, candidato)
                if os.path.exists(caminho):
                    arquivo = caminho
                    break
        if not arquivo and not url:
            raise CommandError(
                'Nenhum arquivo informado. Use --arquivo CAMINHO ou --url URL, '
                'ou coloque o arquivo em data/ncm.csv.'
            )

        if url:
            conteudo, eh_xlsx = self._baixar(url)
        else:
            if not os.path.exists(arquivo):
                raise CommandError(f'Arquivo não encontrado: {arquivo}')
            with open(arquivo, 'rb') as fh:
                conteudo = fh.read()
            eh_xlsx = arquivo.lower().endswith(('.xlsx', '.xlsm'))

        linhas = self._ler_xlsx(conteudo) if eh_xlsx else self._ler_csv(conteudo)
        if not linhas:
            raise CommandError('Não foi possível ler nenhuma linha do arquivo.')

        cabecalho = linhas[0]
        idx_codigo, idx_desc = _detectar_colunas(cabecalho)
        if idx_codigo is None or idx_desc is None:
            raise CommandError(
                'Não encontrei as colunas de código e descrição no cabeçalho: '
                f'{cabecalho}. Renomeie para "NCM"/"Codigo" e "Descricao".'
            )

        criados = atualizados = ignorados = 0
        for linha in linhas[1:]:
            if not linha:
                continue
            codigo = ''.join(filter(str.isdigit, str(linha[idx_codigo] if idx_codigo < len(linha) else '')))
            descricao = str(linha[idx_desc] if idx_desc < len(linha) else '').strip()
            if len(codigo) != 8 or not descricao:
                ignorados += 1
                continue
            _, created = NCM.objects.update_or_create(
                ncm=codigo,
                defaults={'descricao': descricao, 'nome': descricao[:100]},
            )
            if created:
                criados += 1
            else:
                atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {criados} criados, {atualizados} atualizados, '
            f'{ignorados} ignorados. Total na base: {NCM.objects.count()}.'
        ))

    def _baixar(self, url):
        import requests
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        eh_xlsx = url.lower().endswith(('.xlsx', '.xlsm')) or resp.content[:2] == b'PK'
        return resp.content, eh_xlsx

    def _ler_csv(self, conteudo):
        try:
            texto = conteudo.decode('utf-8-sig')
        except UnicodeDecodeError:
            texto = conteudo.decode('latin1')
        amostra = texto[:4096]
        try:
            dialect = csv.Sniffer().sniff(amostra, delimiters=';,\t')
        except csv.Error:
            dialect = csv.excel
        leitor = csv.reader(io.StringIO(texto), dialect)
        return [linha for linha in leitor]

    def _ler_xlsx(self, conteudo):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        ws = wb.active
        return [list(linha) for linha in ws.iter_rows(values_only=True)]
