from django.db import models


class NCM(models.Model):
    """
    Nomenclatura Comum do Mercosul.
    Código de classificação fiscal de mercadorias.
    """
    ncm = models.CharField(
        max_length=8,
        primary_key=True,
        verbose_name='NCM',
        help_text='Código NCM (8 dígitos)'
    )
    nome = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Nome',
        help_text='Nome simplificado da NCM'
    )
    descricao = models.TextField(
        verbose_name='Descrição',
        help_text='Descrição da NCM'
    )

    class Meta:
        db_table = 'ncm'
        verbose_name = 'NCM'
        verbose_name_plural = 'NCMs'
        ordering = ['ncm']

    def __str__(self):
        return f"{self.ncm} - {self.descricao[:50]}"


class CST(models.Model):
    """
    Código de Situação Tributária.
    Define o regime de tributação de ICMS, PIS, COFINS, IPI.
    """
    TIPO_IMPOSTO_CHOICES = [
        ('ICMS', 'ICMS'),
        ('PIS', 'PIS'),
        ('COFINS', 'COFINS'),
        ('IPI', 'IPI'),
    ]

    cst = models.CharField(
        max_length=3,
        verbose_name='CST',
        help_text='Código CST (2 ou 3 dígitos)'
    )
    tipo_imposto = models.CharField(
        max_length=10,
        choices=TIPO_IMPOSTO_CHOICES,
        verbose_name='Tipo de Imposto'
    )
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'cst'
        verbose_name = 'CST'
        verbose_name_plural = 'CSTs'
        unique_together = [['cst', 'tipo_imposto']]
        ordering = ['tipo_imposto', 'cst']

    def __str__(self):
        return f"{self.tipo_imposto} - {self.cst} - {self.descricao}"


class CFOP(models.Model):
    """
    Código Fiscal de Operações e Prestações.
    Define a natureza da operação fiscal.
    """
    cfop = models.CharField(
        max_length=4,
        primary_key=True,
        verbose_name='CFOP',
        help_text='Código CFOP (4 dígitos)'
    )
    nome = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Nome',
        help_text='Nome simplificado da NCM'
    )
    descricao = models.TextField(
        verbose_name='Descrição',
        help_text='Descrição da operação'
    )
    aplicacao = models.TextField(
        null=True,
        blank=True,
        verbose_name='Aplicação',
        help_text='Quando utilizar este CFOP'
    )

    class Meta:
        db_table = 'cfop'
        verbose_name = 'CFOP'
        verbose_name_plural = 'CFOPs'
        ordering = ['cfop']

    def __str__(self):
        return f"{self.cfop} - {self.descricao[:50]}"


class DivisaoImpostosSaida(models.Model):
    """
    Divisão de impostos para saída (vendas).
    Agrupa configurações fiscais de ICMS, PIS, COFINS, IPI.
    """
    divisao = models.CharField(
        max_length=5,
        primary_key=True,
        verbose_name='Divisão',
        help_text='Código da divisão fiscal'
    )
    nome = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Nome',
        help_text='Nome simplificado da divisão'
    )
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição'
    )
    uf = models.CharField(
        max_length=2,
        null=True,
        blank=True,
        verbose_name='UF',
        help_text='Estado específico para esta divisão (opcional)'
    )
    
    # CST - Códigos de Situação Tributária
    cst_icms = models.ForeignKey(
        CST,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo_imposto': 'ICMS'},
        related_name='divisoes_icms',
        verbose_name='CST ICMS'
    )
    cst_pis = models.ForeignKey(
        CST,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo_imposto': 'PIS'},
        related_name='divisoes_pis',
        verbose_name='CST PIS'
    )
    cst_cofins = models.ForeignKey(
        CST,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo_imposto': 'COFINS'},
        related_name='divisoes_cofins',
        verbose_name='CST COFINS'
    )
    cst_ipi = models.ForeignKey(
        CST,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo_imposto': 'IPI'},
        related_name='divisoes_ipi',
        verbose_name='CST IPI',
        null=True,
        blank=True
    )
    
    # CFOP - Códigos Fiscais de Operação
    cfop_dentro_estado = models.ForeignKey(
        CFOP,
        on_delete=models.PROTECT,
        related_name='divisoes_dentro_estado',
        verbose_name='CFOP Dentro do Estado'
    )
    cfop_fora_estado = models.ForeignKey(
        CFOP,
        on_delete=models.PROTECT,
        related_name='divisoes_fora_estado',
        verbose_name='CFOP Fora do Estado'
    )
    cfop_fora_estado_contribuinte = models.ForeignKey(
        CFOP,
        on_delete=models.PROTECT,
        related_name='divisoes_fora_estado_contrib',
        null=True,
        blank=True,
        verbose_name='CFOP Fora do Estado (Contribuinte)'
    )
    cfop_fora_estado_nao_contribuinte = models.ForeignKey(
        CFOP,
        on_delete=models.PROTECT,
        related_name='divisoes_fora_estado_nao_contrib',
        null=True,
        blank=True,
        verbose_name='CFOP Fora do Estado (Não Contribuinte)'
    )
    cfop_fora_pais = models.ForeignKey(
        CFOP,
        on_delete=models.PROTECT,
        related_name='divisoes_fora_pais',
        verbose_name='CFOP Fora do País',
        null=True,
        blank=True
    )
    
    # Alíquotas
    aliquota_icms = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Alíquota ICMS (%)'
    )
    aliquota_pis = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        verbose_name='Alíquota PIS (%)'
    )
    aliquota_cofins = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        verbose_name='Alíquota COFINS (%)'
    )
    aliquota_ipi = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Alíquota IPI (%)'
    )
    
    # ICMS - Base de Cálculo
    reducao_bc_icms = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Redução BC ICMS (%)'
    )
    percentual_reducao_base_calculo_icms = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Percentual Redução BC ICMS (%)',
        help_text='Alias para reducao_bc_icms'
    )
    modalidade_bc_icms = models.IntegerField(
        default=0,
        verbose_name='Modalidade BC ICMS',
        help_text='0=MVA; 1=Pauta; 2=Preço Tabelado; 3=Valor da Operação'
    )
    
    # ICMS-ST - Substituição Tributária
    aliquota_mva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='MVA (%)',
        help_text='Margem de Valor Agregado para ICMS-ST'
    )
    aliquota_icms_st = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Alíquota ICMS-ST (%)'
    )
    reducao_bc_icms_st = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Redução BC ICMS-ST (%)'
    )
    modalidade_bc_icms_st = models.IntegerField(
        default=4,
        verbose_name='Modalidade BC ICMS-ST',
        help_text='0=Preço tab/máx sugerido; 4=MVA; 5=Pauta'
    )
    
    # Flags de composição de base de cálculo
    somar_frete_bc_icms = models.BooleanField(
        default=True,
        verbose_name='Somar Frete na BC ICMS'
    )
    somar_frete_bc_icms_st = models.BooleanField(
        default=True,
        verbose_name='Somar Frete na BC ICMS-ST'
    )
    somar_ipi_bc_icms_st = models.BooleanField(
        default=False,
        verbose_name='Somar IPI na BC ICMS-ST'
    )
    somar_seguro_bc_icms = models.BooleanField(
        default=True,
        verbose_name='Somar Seguro na BC ICMS'
    )
    somar_seguro_bc_icms_st = models.BooleanField(
        default=True,
        verbose_name='Somar Seguro na BC ICMS-ST'
    )
    somar_outras_desp_bc_icms = models.BooleanField(
        default=True,
        verbose_name='Somar Outras Despesas na BC ICMS'
    )
    somar_outras_desp_bc_icms_st = models.BooleanField(
        default=True,
        verbose_name='Somar Outras Despesas na BC ICMS-ST'
    )

    class Meta:
        db_table = 'divisao_impostos_saida'
        verbose_name = 'Divisão de Impostos Saída'
        verbose_name_plural = 'Divisões de Impostos Saída'
        ordering = ['divisao']

    def __str__(self):
        if self.nome:
            return f"{self.divisao} - {self.nome}"
        return f"{self.divisao} - {self.descricao}"


class Estado(models.Model):
    """
    Estados brasileiros (UF).
    """
    uf = models.CharField(
        max_length=2,
        primary_key=True,
        verbose_name='UF',
        help_text='Sigla do estado (ex: SP, RJ, MG)'
    )
    nome = models.CharField(
        max_length=100,
        verbose_name='Nome do Estado'
    )
    codigo_ibge = models.IntegerField(
        unique=True,
        verbose_name='Código IBGE',
        help_text='Código IBGE do estado'
    )

    class Meta:
        db_table = 'estados'
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'
        ordering = ['nome']

    def __str__(self):
        return f"{self.uf} - {self.nome}"


class Cidade(models.Model):
    """
    Cidades brasileiras.
    """
    codigo_ibge = models.IntegerField(
        primary_key=True,
        verbose_name='Código IBGE',
        help_text='Código IBGE da cidade'
    )
    nome = models.CharField(
        max_length=100,
        verbose_name='Nome da Cidade'
    )
    estado = models.ForeignKey(
        Estado,
        on_delete=models.PROTECT,
        related_name='cidades',
        verbose_name='Estado'
    )

    class Meta:
        db_table = 'cidades'
        verbose_name = 'Cidade'
        verbose_name_plural = 'Cidades'
        ordering = ['estado__nome', 'nome']

    def __str__(self):
        return f"{self.nome}/{self.estado.uf}"

    def get_nome_completo(self):
        return f"{self.nome} - {self.estado.nome}"