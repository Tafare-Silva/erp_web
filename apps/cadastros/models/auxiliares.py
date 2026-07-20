from django.db import models


class Marca(models.Model):
    nome = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name='Nome da Marca',
        help_text='Nome da marca do produto'
    )

    class Meta:
        db_table = 'marcas'
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Divisao(models.Model):
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código de usuário da divisão. Ex: 1.1, 2.5.6'
    )
    nome = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name='Nome da Divisão',
        help_text='Descrição da divisão dos produtos'
    )
    pai = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subdivisoes',
        to_field='nome',
        verbose_name='Divisão Pai',
        help_text='Divisão pai na hierarquia'
    )
    controla_lote = models.BooleanField(
        default=False,
        verbose_name='Controla Lote',
        help_text='Se os produtos desta divisão terão controle de lote'
    )
    palavras_chave_cadastro_por_xml = models.TextField(
        null=True,
        blank=True,
        verbose_name='Palavras-chave para XML',
        help_text='Palavras-chave para cadastro automático por XML'
    )
    permitir_estoque_negativo = models.BooleanField(
        default=False,
        verbose_name='Permite Estoque Negativo',
        help_text='Se permite estoque negativo para produtos desta divisão'
    )

    class Meta:
        db_table = 'divisoes'
        verbose_name = 'Divisão'
        verbose_name_plural = 'Divisões'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def get_nivel(self):
        nivel = 0
        pai_atual = self.pai
        while pai_atual:
            nivel += 1
            pai_atual = pai_atual.pai
        return nivel

    def get_caminho_completo(self):
        caminho = [self.nome]
        pai_atual = self.pai
        while pai_atual:
            caminho.insert(0, pai_atual.nome)
            pai_atual = pai_atual.pai
        return ' > '.join(caminho)


class Unidade(models.Model):
    nome = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name='Nome',
        help_text='Nome da unidade. Ex: Metro quadrado, Quilograma'
    )
    simbolo = models.CharField(
        max_length=3,
        verbose_name='Símbolo',
        help_text='Símbolo da unidade. Ex: UN, KG, M²'
    )

    class Meta:
        db_table = 'unidades'
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.simbolo})"


class Banco(models.Model):
    codigo_banco = models.IntegerField(
        primary_key=True,
        verbose_name='Código do Banco',
        help_text='Código do banco'
    )
    nome = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Nome',
        help_text='Nome do banco'
    )
    taxa_cobranca_simples = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Taxa Cobrança Simples',
        help_text='Taxa de cobrança simples'
    )
    banco_boleto = models.SmallIntegerField(
        default=0,
        verbose_name='Banco Boleto',
        help_text='Código do banco para boleto'
    )
    orientacoes_banco = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Orientações',
        help_text='Orientações do banco'
    )
    local_pagamento_boleto = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Local de Pagamento',
        help_text='Local de pagamento do boleto'
    )

    class Meta:
        db_table = 'bancos'
        verbose_name = 'Banco'
        verbose_name_plural = 'Bancos'
        ordering = ['codigo_banco', 'nome']

    def __str__(self):
        return f"{self.codigo_banco} - {self.nome}" if self.nome else str(self.codigo_banco)