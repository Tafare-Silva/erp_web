from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal


chassi_validator = RegexValidator(
    r'^[A-Za-z0-9]{17}$',
    'O chassi deve conter exatamente 17 caracteres alfanuméricos.',
)


class MarcaVeiculo(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name='Marca')

    class Meta:
        db_table = 'veiculo_marca'
        verbose_name = 'Marca de Veículo'
        verbose_name_plural = 'Marcas de Veículos'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class ModeloVeiculo(models.Model):
    marca = models.ForeignKey(
        MarcaVeiculo, on_delete=models.CASCADE,
        related_name='modelos', verbose_name='Marca'
    )
    nome = models.CharField(max_length=150, verbose_name='Modelo')
    ano_modelo = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name='Ano do Modelo'
    )

    class Meta:
        db_table = 'veiculo_modelo'
        verbose_name = 'Modelo de Veículo'
        verbose_name_plural = 'Modelos de Veículos'
        ordering = ['marca__nome', 'nome']
        unique_together = ['marca', 'nome', 'ano_modelo']

    def __str__(self):
        return f'{self.marca.nome} {self.nome} {self.ano_modelo or ""}'.strip()


class Veiculo(models.Model):
    COMBUSTIVEL_CHOICES = [
        ('G', 'Gasolina'),
        ('A', 'Álcool'),
        ('D', 'Diesel'),
        ('F', 'Flex'),
        ('E', 'Elétrico'),
        ('H', 'Híbrido'),
        ('GNV', 'GNV'),
    ]

    CARROCERIA_CHOICES = [
        ('HATCH', 'Hatch'),
        ('SEDA', 'Sedã'),
        ('SUV', 'SUV'),
        ('PICK', 'Picape'),
        ('UTI', 'Utilitário'),
        ('MOTO', 'Motocicleta'),
        ('CAMI', 'Caminhão'),
        ('OUT', 'Outros'),
    ]

    ESPECIE_CHOICES = [
        ('PASSAGEIRO', 'Passageiro'),
        ('CARGA', 'Carga'),
        ('MISTO', 'Misto'),
        ('CORRIDA', 'Corrida'),
        ('TRACAO', 'Tração'),
    ]

    STATUS_CHOICES = [
        ('EM_ESTOQUE', 'Em Estoque'),
        ('RESERVADO', 'Reservado'),
        ('VENDIDO', 'Vendido'),
        ('EM_AVALIACAO', 'Em Avaliação'),
    ]

    chassi = models.CharField(
        max_length=17, unique=True, validators=[chassi_validator],
        verbose_name='Chassi'
    )
    renavam = models.CharField(
        max_length=11, blank=True, verbose_name='Renavam'
    )
    placa = models.CharField(
        max_length=8, blank=True, verbose_name='Placa'
    )
    marca = models.ForeignKey(
        MarcaVeiculo, on_delete=models.PROTECT,
        related_name='veiculos', verbose_name='Marca'
    )
    modelo = models.ForeignKey(
        ModeloVeiculo, on_delete=models.PROTECT,
        related_name='veiculos', verbose_name='Modelo'
    )
    cor = models.CharField(max_length=50, blank=True, verbose_name='Cor')
    ano_fabricacao = models.PositiveSmallIntegerField(
        verbose_name='Ano de Fabricação'
    )
    ano_modelo = models.PositiveSmallIntegerField(
        verbose_name='Ano do Modelo'
    )
    motor = models.CharField(max_length=50, blank=True, verbose_name='Motor')
    combustivel = models.CharField(
        max_length=10, choices=COMBUSTIVEL_CHOICES,
        default='G', verbose_name='Combustível'
    )
    carroceria = models.CharField(
        max_length=10, choices=CARROCERIA_CHOICES,
        default='SEDA', verbose_name='Carroceria'
    )
    especie = models.CharField(
        max_length=15, choices=ESPECIE_CHOICES,
        default='PASSAGEIRO', verbose_name='Espécie'
    )
    kilometragem = models.PositiveIntegerField(
        default=0, verbose_name='Kilometragem'
    )
    potencia = models.CharField(
        max_length=4, blank=True, default='0', verbose_name='Potência (CV)'
    )
    cilindradas = models.CharField(
        max_length=4, blank=True, default='0', verbose_name='Cilindradas (cm³)'
    )
    peso_liquido = models.CharField(
        max_length=9, blank=True, default='0', verbose_name='Peso Líquido (kg)'
    )
    peso_bruto = models.CharField(
        max_length=9, blank=True, default='0', verbose_name='Peso Bruto (kg)'
    )
    codigo_modelo = models.CharField(
        max_length=21, blank=True, verbose_name='Código do Modelo'
    )
    capacidade = models.CharField(
        max_length=9, blank=True, default='0', verbose_name='Capacidade (kg)'
    )

    # ----- Dados fiscais / tributação -----
    dono_recibo = models.ForeignKey(
        'cadastros.Pessoa', on_delete=models.PROTECT,
        null=True, blank=True, related_name='veiculos_recibo',
        verbose_name='Dono do Veículo (Recibo)',
        help_text='Nome de quem está no recibo (quem vendeu o carro à loja). '
                  'Usado como vendedor/fornecedor na nota de compra.'
    )
    ncm = models.CharField(
        max_length=8, default='87032310', verbose_name='NCM'
    )
    cfop = models.CharField(
        max_length=4, default='5101', verbose_name='CFOP'
    )
    origem = models.CharField(
        max_length=1, default='0', verbose_name='Origem'
    )
    cst_icms = models.CharField(
        max_length=3, blank=True, default='00', verbose_name='CST ICMS'
    )
    csosn = models.CharField(
        max_length=4, blank=True, default='', verbose_name='CSOSN'
    )
    aliquota_icms = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Alíquota ICMS %'
    )
    cst_pis = models.CharField(max_length=2, blank=True, default='01', verbose_name='CST PIS')
    aliquota_pis = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.00'), verbose_name='Aliq PIS %')
    cst_cofins = models.CharField(max_length=2, blank=True, default='01', verbose_name='CST COFINS')
    aliquota_cofins = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.00'), verbose_name='Aliq COFINS %')

    valor_custo = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Valor de Custo'
    )
    preco_venda = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Preço de Venda'
    )
    tabela_fipe = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Valor Tabela FIPE'
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='EM_ESTOQUE', verbose_name='Status'
    )

    local = models.ForeignKey(
        'cadastros.LocalEstoque', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='veiculos',
        verbose_name='Local de Estoque'
    )
    vendedor = models.ForeignKey(
        'cadastros.Pessoa', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='veiculos_responsaveis',
        limit_choices_to={'vendedor': True}, verbose_name='Vendedor'
    )
    produto = models.ForeignKey(
        'cadastros.Produto', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='veiculos',
        verbose_name='Produto (integração NF-e)',
        help_text='Produto associado para emissão futura de NF-e.'
    )

    observacoes = models.TextField(blank=True, verbose_name='Observações')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        db_table = 'veiculo'
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'
        ordering = ['-atualizado_em']

    def __str__(self):
        return f'{self.marca} {self.modelo.nome} {self.placa}'.strip()

    # ----- Métodos fiscais (grupo veicProd da NF-e) -----

    def get_tp_comb_fiscal(self):
        """Código do combustível (tpComb) conforme Tabela da NF-e."""
        return {
            'G': '01', 'A': '02', 'D': '03', 'GNV': '06',
            'F': '03', 'E': '16', 'H': '16',
        }.get(self.combustivel, '01')

    def get_combustivel_fiscal(self):
        return {
            'G': '01', 'A': '02', 'D': '03', 'GNV': '06',
            'F': '03', 'E': '16', 'H': '16',
        }.get(self.combustivel, '01')

    def get_tp_veic(self):
        """Tipo do veículo (tpVeic). Default 01 = passageiro."""
        return '01'

    def get_esp_veic(self):
        """Espécie do veículo (espVeic). Default 01 = passageiro."""
        return {
            'PASSAGEIRO': '01', 'CARGA': '02', 'MISTO': '03',
            'CORRIDA': '04', 'TRACAO': '05',
        }.get(self.especie, '01')

    def get_cc_or(self):
        """Carroceria (ccOr). Default 01 = não aplicável."""
        return '01'