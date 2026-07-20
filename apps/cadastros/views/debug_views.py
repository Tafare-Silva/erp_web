"""
View de debug para testar carregamento de agências.
Acesse: /cadastros/debug-agencias/
"""

from django.http import HttpResponse
from apps.cadastros.models import AgenciaBancaria

def debug_agencias(request):
    html = "<h1>Debug - Agências Bancárias</h1>"
    
    html += "<h2>Método 1: Raw Query</h2>"
    try:
        agencias = AgenciaBancaria.objects.raw('''
            SELECT "fk_bancos$banco" as banco, agencia, digito
            FROM "cadastros"."agencias_bancarias"
            ORDER BY "fk_bancos$banco", agencia
        ''')
        
        html += "<ul>"
        count = 0
        for ag in agencias:
            html += f"<li>Banco: {ag.banco}, Agência: {ag.agencia}, Dígito: {ag.digito or 'N/A'}</li>"
            count += 1
        html += "</ul>"
        html += f"<p><strong>Total encontrado: {count}</strong></p>"
    except Exception as e:
        html += f"<p style='color: red;'>ERRO: {e}</p>"
    
    html += "<h2>Método 2: Query SQL Direta</h2>"
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM "cadastros"."agencias_bancarias"')
        total = cursor.fetchone()[0]
        html += f"<p><strong>Total no banco: {total}</strong></p>"
        
        if total > 0:
            cursor.execute('SELECT "fk_bancos$banco", agencia, digito FROM "cadastros"."agencias_bancarias" ORDER BY "fk_bancos$banco", agencia LIMIT 10')
            html += "<ul>"
            for row in cursor.fetchall():
                html += f"<li>Banco: {row[0]}, Agência: {row[1]}, Dígito: {row[2] or 'N/A'}</li>"
            html += "</ul>"
    
    return HttpResponse(html)
