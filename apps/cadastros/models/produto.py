from django.db import models
from .auxiliares import Marca, Divisao, Unidade
from .reservados import NCM, DivisaoImpostosSaida
from .pessoa import Pessoa


class LocalEstoque(models.Model):
    local = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name='Local de Estoque',
        help_text='Nome do local de estoque (ex: Loja Principal, Depósito)'
    )
    descricao = models.TextField(
        null=True,
        blank=True,
        verbose_name='Descrição'
    )
    ativo = models.BooleanField(  
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        db_table = 'local_estoque'
        verbose_name = 'Local de Estoque'
        verbose_name_plural = 'Locais de Estoque'
        ordering = ['local']

    def __str__(self):
        return self.local


class Produto(models.Model):
    TIPO_CHOICES = [
        ('REVENDA', 'Revenda'),
        ('PRODUTO ACABADO', 'Produto Acabado (Fabricação Própria)'),
        ('MATERIA PRIMA', 'Matéria Prima'),
        ('PRODUTO INTERMEDIARIO', 'Produto Intermediário'),
        ('USO E CONSUMO', 'Uso e Consumo'),
        ('EMBALAGEM', 'Embalagem'),
        ('SERVICO', 'Serviço'),
        ('OUTRO', 'Outro'),
    ]

    ORIGEM_CHOICES = [
        ('0', '0 - Nacional'),
        ('1', '1 - Estrangeira - Importação direta'),
        ('2', '2 - Estrangeira - Adquirida no mercado interno'),
        ('3', '3 - Nacional - Conteúdo de Importação > 40%'),
        ('4', '4 - Nacional - Processos Produtivos Básicos'),
        ('5', '5 - Nacional - Conteúdo de Importação ≤ 40%'),
        ('6', '6 - Estrangeira - Importação direta, sem similar nacional'),
        ('7', '7 - Estrangeira - Merc. interno, sem similar nacional'),
        ('8', '8 - Nacional - Conteúdo de Importação > 70%'),
    ]

    REGULATORIO_CHOICES = [
        ('COMUM', 'Nenhum (produto comum)'),
        ('MEDICAMENTO', 'Medicamento'),
        ('ARMAMENTO', 'Armamento'),
        ('COMBUSTIVEL', 'Combustível'),
        ('OUTRO', 'Outro'),
    ]

    pk_chave = models.AutoField(primary_key=True, verbose_name='Código')
    nome = models.CharField(max_length=255, verbose_name='Nome do Produto')
    descricao_reduzida = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name='Desc. Reduzida',
        help_text='Descrição para PDV, cupom fiscal e etiquetas'
    )
    codigo = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Código',
        help_text='Código interno / SKU próprio da loja'
    )
    referencia = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Referência',
        help_text='Código de referência do fabricante ou catálogo'
    )
    
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='produtos',
        verbose_name='Marca'
    )
    divisao = models.ForeignKey(
        Divisao,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='produtos',
        verbose_name='Divisão'
    )
    fabricante = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name='Fabricante'
    )
    ncm = models.ForeignKey(
        NCM,
        on_delete=models.PROTECT,
        to_field='ncm',
        related_name='produtos',
        verbose_name='NCM'
    )
    unidade_venda = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='produtos',
        verbose_name='Unidade Venda'
    )
    
    preco_venda = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Preço Venda'
    )
    custo_referencia = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Custo Referência'
    )
    pode_alterar_preco_venda = models.BooleanField(
        default=False,
        verbose_name='Pode Alterar Preço'
    )
    
    inativo = models.BooleanField(default=False, verbose_name='Inativo')
    data_cadastramento = models.DateField(auto_now_add=True, verbose_name='Data Cadastro')
    tipo_produto = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default='REVENDA',
        verbose_name='Tipo de Produto'
    )
    tipo_regulatorio = models.CharField(
        max_length=30,
        choices=REGULATORIO_CHOICES,
        default='COMUM',
        verbose_name='Tipo Regulatório'
    )
    
    referencia_fabrica = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Referência Fábrica'
    )
    
    divisao_impostos_saida = models.ForeignKey(
        DivisaoImpostosSaida,
        on_delete=models.SET_NULL,
        to_field='divisao',
        related_name='produtos',
        blank=True,
        null=True,
        verbose_name='Divisão Impostos Saída (Perfil Fiscal)'
    )
    cest = models.CharField(max_length=7, default='0000000', verbose_name='CEST')
    cest_isento = models.BooleanField(default=False, verbose_name='CEST não se aplica')
    
    controla_estoque = models.BooleanField(default=True, verbose_name='Controla Estoque')
    permite_venda = models.BooleanField(default=True, verbose_name='Permite Venda')
    permite_compra = models.BooleanField(default=True, verbose_name='Permite Compra')
    
    descricao = models.TextField(blank=True, null=True, verbose_name='Descrição Técnica')
    descricao_comercial = models.TextField(blank=True, null=True, verbose_name='Descrição Comercial')
    
    estoque_minimo = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Estoque Mínimo'
    )
    ponto_reposicao = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Ponto de Reposição'
    )
    estoque_maximo = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Estoque Máximo'
    )
    controla_lote = models.BooleanField(
        default=False,
        verbose_name='Controla lote (rastreabilidade + FEFO)'
    )
    controla_serie = models.BooleanField(
        default=False,
        verbose_name='Controla número de série'
    )
    permitir_estoque_negativo = models.BooleanField(
        default=False,
        verbose_name='Permitir Estoque Negativo'
    )
    local_padrao = models.ForeignKey(
        LocalEstoque,
        on_delete=models.SET_NULL,
        to_field='local',
        related_name='produtos',
        blank=True,
        null=True,
        verbose_name='Local Estoque Padrão'
    )
    
    fornecedor_principal = models.ForeignKey(
        Pessoa,
        on_delete=models.SET_NULL,
        limit_choices_to={'fornecedor': True},
        related_name='produtos_fornecidos',
        blank=True,
        null=True,
        verbose_name='Fornecedor Principal'
    )
    
    imagem_principal = models.ForeignKey(
        'ImagemProduto',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Imagem Principal'
    )
    
    aplicacao = models.TextField(blank=True, null=True, verbose_name='Aplicação')
    tamanho = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tamanho')
    cor = models.CharField(max_length=50, blank=True, null=True, verbose_name='Cor')
    genero = models.CharField(max_length=100, blank=True, null=True, verbose_name='Gênero')
    colecao = models.CharField(max_length=100, blank=True, null=True, verbose_name='Coleção')
    categoria = models.CharField(max_length=200, blank=True, null=True, verbose_name='Categoria')

    # =========================================================
    # CAMPOS FISCAIS (NF-e / NFC-e)
    # =========================================================
    origem = models.CharField(
        max_length=1, choices=ORIGEM_CHOICES, default='0',
        verbose_name='Origem da Mercadoria'
    )

    # ICMS
    cst_icms = models.CharField(
        max_length=3, blank=True, default='',
        verbose_name='CST/CSOSN ICMS',
        help_text='Régime Normal: 00,10,20,30,40,41,50,60,70,90 | Simples: 101,102,103,201,202,203,300,400,500,900'
    )
    cfop_venda_estadual = models.CharField(
        max_length=4, blank=True, default='',
        verbose_name='CFOP Venda Estadual',
        help_text='Ex: 5102, 5405'
    )
    cfop_venda_interestadual = models.CharField(
        max_length=4, blank=True, default='',
        verbose_name='CFOP Venda Interestadual',
        help_text='Ex: 6102, 6404'
    )
    aliquota_icms = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Alíquota ICMS (%)'
    )
    reducao_bc_icms = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Redução BC ICMS (%)'
    )
    modalidade_bc_icms = models.IntegerField(
        default=3,
        verbose_name='Modalidade BC ICMS',
        help_text='0=MVA | 1=Pauta | 2=Preço Tabelado | 3=Valor da Operação'
    )

    # ICMS-ST (Substituição Tributária)
    aliquota_icms_st = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Alíquota ICMS-ST (%)'
    )
    aliquota_mva = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='MVA (%)',
        help_text='Margem de Valor Agregado para ICMS-ST'
    )
    reducao_bc_icms_st = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Redução BC ICMS-ST (%)'
    )

    # PIS
    cst_pis = models.CharField(
        max_length=2, blank=True, default='',
        verbose_name='CST PIS',
        help_text='Ex: 01=Alíquota básica | 07=Operação isenta | 49=Outras operações | 99=Outras'
    )
    aliquota_pis = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name='Alíquota PIS (%)'
    )

    # COFINS
    cst_cofins = models.CharField(
        max_length=2, blank=True, default='',
        verbose_name='CST COFINS',
        help_text='Ex: 01=Alíquota básica | 07=Operação isenta | 49=Outras operações | 99=Outras'
    )
    aliquota_cofins = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name='Alíquota COFINS (%)'
    )

    # IPI
    cst_ipi = models.CharField(
        max_length=2, blank=True, null=True,
        verbose_name='CST IPI',
        help_text='Ex: 50=Saída tributada | 99=Outras saídas'
    )
    aliquota_ipi = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Alíquota IPI (%)'
    )

    # =========================================================
    # LOGÍSTICA
    # =========================================================
    peso_liquido = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name='Peso Líquido (kg)'
    )
    peso_bruto = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name='Peso Bruto (kg)'
    )
    comprimento = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name='Comprimento (cm)'
    )
    largura = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name='Largura (cm)'
    )
    altura = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name='Altura (cm)'
    )
    cubagem = models.DecimalField(
        max_digits=14, decimal_places=6, default=0,
        verbose_name='Cubagem (m³)',
        help_text='Volume cúbico em m³ (ex: Altura x Largura x Comprimento / 1.000.000)'
    )
    tipo_embalagem = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Tipo Embalagem',
        help_text='Ex: Caixa, Pacote/Envelope, Rolo/Cilindro'
    )
    multiplo_venda = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        verbose_name='Múltiplo Venda',
        help_text='Passo ou múltiplo mínimo de venda'
    )
    qtd_embalagem = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        verbose_name='Qtd. Embalagem',
        help_text='Quantidade contida na embalagem de fábrica'
    )
    prazo_separacao_dias = models.PositiveIntegerField(
        default=0,
        verbose_name='Prazo de Separação (dias)',
        help_text='Dias úteis para separar e despachar o pedido'
    )

    # =========================================================
    # CANAIS E MARKETING
    # =========================================================
    VISIBILIDADE_CHOICES = [
        ('TODOS', 'Catálogo e Vendas'),
        ('VENDAS', 'Somente Vendas'),
        ('CATALOGO', 'Somente Catálogo'),
        ('OCULTO', 'Oculto (uso interno)'),
    ]
    visibilidade = models.CharField(
        max_length=10, choices=VISIBILIDADE_CHOICES, default='TODOS',
        verbose_name='Visibilidade'
    )
    produto_destaque = models.BooleanField(
        default=False,
        verbose_name='Produto em Destaque'
    )
    seo_titulo = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name='Título SEO'
    )
    seo_descricao = models.TextField(
        blank=True, null=True,
        verbose_name='Descrição SEO'
    )
    palavras_chave = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name='Palavras-chave',
        help_text='Separadas por vírgula'
    )
    url_amigavel = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name='URL Amigável'
    )

    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def __str__(self):
        return f"{self.pk_chave} - {self.nome}"


class CodigoBarras(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='codigos_barras',
        verbose_name='Produto'
    )
    codigo_barras = models.CharField(
        max_length=13,
        verbose_name='Código de Barras',
        help_text='Código EAN-13 (até 13 dígitos)'
    )

    class Meta:
        db_table = 'codigo_barras'
        verbose_name = 'Código de Barras'
        verbose_name_plural = 'Códigos de Barras'
        unique_together = [['produto', 'codigo_barras']]

    def __str__(self):
        return f"{self.codigo_barras} - {self.produto.nome}"


class ConversaoUnidade(models.Model):
    """
    Conversão de unidade de venda do produto.
    Ex: 1 CX = 12 UN (unidade base cadastrada no produto).
    """
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='conversoes_unidade',
        verbose_name='Produto'
    )
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='conversoes',
        verbose_name='Unidade'
    )
    fator_conversao = models.DecimalField(
        max_digits=14, decimal_places=4, default=1,
        verbose_name='Fator de Estoque',
        help_text='Quantidade de unidades base contidas em 1 desta unidade'
    )
    fator_preco = models.DecimalField(
        max_digits=14, decimal_places=4, default=1,
        verbose_name='Fator de Preço',
        help_text='Multiplicador de preço para esta unidade'
    )
    sem_gtin = models.BooleanField(
        default=False,
        verbose_name='Sem GTIN'
    )
    codigo_barras = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name='Código de Barras',
        help_text='EAN/DUN da embalagem (opcional)'
    )
    sku = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='SKU'
    )
    permite_compra = models.BooleanField(
        default=True,
        verbose_name='Compra'
    )
    permite_venda = models.BooleanField(
        default=True,
        verbose_name='Venda'
    )

    class Meta:
        db_table = 'conversao_unidade'
        verbose_name = 'Conversão de Unidade'
        verbose_name_plural = 'Conversões de Unidade'
        unique_together = [['produto', 'unidade']]
        ordering = ['unidade__nome']

    def __str__(self):
        return f"1 {self.unidade.simbolo} = {self.fator_conversao} {self.produto.unidade_venda.simbolo}"


class ProdutoVariacao(models.Model):
    """
    Variações de produto (ex: tamanhos, cores, grades).
    """
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='variacoes',
        verbose_name='Produto Principal'
    )
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição',
        help_text='Ex: Cor: Azul, Tamanho: G'
    )
    codigo = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Código'
    )
    referencia = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Referência'
    )
    sku = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='SKU'
    )
    codigo_barras = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name='Cód. de Barras (EAN/GTIN)'
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    preco_venda = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        verbose_name='Preço de Venda'
    )
    estoque_atual = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name='Estoque Atual'
    )

    class Meta:
        db_table = 'produto_variacao'
        verbose_name = 'Variação de Produto'
        verbose_name_plural = 'Variações de Produtos'
        ordering = ['descricao']

    def __str__(self):
        return f"{self.produto.nome} - {self.descricao}"


class ProdutoCanal(models.Model):
    """
    Canais de venda / Marketplace para anúncios do produto.
    """
    CANAL_CHOICES = [
        ('MERCADO_LIVRE', 'Mercado Livre'),
        ('SHOPEE', 'Shopee'),
        ('LOJA_INTEGRADA', 'Loja Integrada'),
        ('NUVEMSHOP', 'Nuvemshop'),
        ('WOOCOMMERCE', 'WooCommerce'),
        ('AMAZON', 'Amazon'),
        ('CATALOGO_WHATSAPP', 'Catálogo WhatsApp'),
        ('OUTRO', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('PAUSADO', 'Pausado'),
    ]

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='canais',
        verbose_name='Produto'
    )
    canal = models.CharField(
        max_length=50,
        choices=CANAL_CHOICES,
        default='MERCADO_LIVRE',
        verbose_name='Canal'
    )
    titulo = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name='Título'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ATIVO',
        verbose_name='Status'
    )
    preco = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        verbose_name='Preço'
    )
    unidade = models.CharField(
        max_length=50, default='Padrão',
        verbose_name='Unidade'
    )
    sku_canal = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name='SKU Canal'
    )
    url = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name='URL'
    )

    class Meta:
        db_table = 'produto_canal'
        verbose_name = 'Canal do Produto'
        verbose_name_plural = 'Canais do Produto'
        ordering = ['canal']

    def __str__(self):
        return f"{self.produto.nome} - {self.get_canal_display()}"


class ImagemProduto(models.Model):
    pk_chave = models.AutoField(primary_key=True, verbose_name='Código')
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='imagens',
        verbose_name='Produto'
    )
    imagem = models.BinaryField(verbose_name='Imagem (Binário)')

    class Meta:
        db_table = 'imagem_produto'
        verbose_name = 'Imagem de Produto'
        verbose_name_plural = 'Imagens de Produtos'

    def __str__(self):
        return f"Imagem {self.pk_chave} - {self.produto.nome}"

class SaldoEstoque(models.Model):
    """
    Saldo atual de um produto em um local de estoque.
    Atualizado automaticamente a cada movimentação.
    """
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='saldos_estoque',
        verbose_name='Produto'
    )
    local = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name='saldos',
        verbose_name='Local'
    )
    quantidade = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=0,
        verbose_name='Quantidade'
    )
    ultima_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )

    class Meta:
        db_table = 'estoque_saldo'
        verbose_name = 'Saldo de Estoque'
        verbose_name_plural = 'Saldos de Estoque'
        unique_together = [['produto', 'local']]
        ordering = ['produto__nome']

    def __str__(self):
        return f"{self.produto.nome} | {self.local.local}: {self.quantidade}"
