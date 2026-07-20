from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from django.db import connection
from apps.cadastros.models import Produto
import base64


def imagem_list(request, produto_id):
    """Lista imagens do produto."""
    produto = get_object_or_404(Produto, pk_chave=produto_id)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT pk_chave, imagem
            FROM cadastros.imagem_produto
            WHERE "fk_produtos$produto" = %s
            ORDER BY pk_chave
        """, [produto_id])
        
        imagens = []
        for row in cursor.fetchall():
            pk_chave = row[0]
            imagem_bytea = row[1]
            # Converter BYTEA para base64 para exibir no HTML
            if imagem_bytea:
                imagem_base64 = base64.b64encode(bytes(imagem_bytea)).decode('utf-8')
                imagens.append({
                    'pk_chave': pk_chave,
                    'imagem_base64': imagem_base64
                })
    
    return render(request, 'cadastros/produtos/imagem_list.html', {
        'produto': produto,
        'imagens': imagens
    })


def imagem_create(request, produto_id):
    """Upload de imagem."""
    produto = get_object_or_404(Produto, pk_chave=produto_id)
    
    if request.method == 'POST' and request.FILES.get('imagem'):
        imagem_file = request.FILES['imagem']
        imagem_bytes = imagem_file.read()
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO cadastros.imagem_produto ("fk_produtos$produto", imagem)
                VALUES (%s, %s)
            """, [produto_id, imagem_bytes])
        
        messages.success(request, 'Imagem adicionada!')
        return redirect('cadastros:imagem_list', produto_id=produto_id)
    
    return render(request, 'cadastros/produtos/imagem_form.html', {
        'produto': produto
    })


def imagem_delete(request, produto_id, pk_imagem):
    """Excluir imagem."""
    produto = get_object_or_404(Produto, pk_chave=produto_id)
    
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM cadastros.imagem_produto
                WHERE pk_chave = %s AND "fk_produtos$produto" = %s
            """, [pk_imagem, produto_id])
        
        messages.success(request, 'Imagem excluída!')
        return redirect('cadastros:imagem_list', produto_id=produto_id)
    
    return render(request, 'cadastros/produtos/imagem_confirm_delete.html', {
        'produto': produto,
        'pk_imagem': pk_imagem
    })


def imagem_view(request, pk_imagem):
    """Retorna imagem em tamanho real."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT imagem FROM cadastros.imagem_produto WHERE pk_chave = %s
        """, [pk_imagem])
        row = cursor.fetchone()
        
        if row and row[0]:
            imagem_bytes = bytes(row[0])
            return HttpResponse(imagem_bytes, content_type='image/jpeg')
    
    return HttpResponse(status=404)
