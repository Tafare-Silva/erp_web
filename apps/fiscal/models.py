from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class CertificadoDigital(models.Model):
    TIPO_CHOICES = [
        ('A1', 'A1 (Arquivo)'),
        ('A3', 'A3 (Token/Cartão)'),
    ]

    empresa = models.ForeignKey(
        'cadastros.Empresa', on_delete=models.CASCADE,
        related_name='certificados', verbose_name='Empresa'
    )
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default='A1')
    arquivo = models.FileField(
        upload_to='certificados/', null=True, blank=True,
        verbose_name='Arquivo PFX/P12'
    )
    senha = models.CharField(max_length=255, verbose_name='Senha do Certificado')
    validade_inicio = models.DateField(verbose_name='Início Validade')
    validade_fim = models.DateField(verbose_name='Fim Validade')
    emissor = models.CharField(max_length=255, blank=True, verbose_name='Emissor')
    cnpj = models.CharField(max_length=18, verbose_name='CNPJ do Certificado')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        db_table = 'certificados_digitais'
        verbose_name = 'Certificado Digital'
        verbose_name_plural = 'Certificados Digitais'
        ordering = ['-validade_fim']

    def __str__(self):
        return f'{self.cnpj} - {self.get_tipo_display()}'

    def clean(self):
        if self.validade_fim and self.validade_fim < self.validade_inicio:
            raise ValidationError('Data fim deve ser posterior à data início')


class LoteNFe(models.Model):
    STATUS_CHOICES = [
        ('DIGITACAO', 'Em Digitação'),
        ('ASSINADO', 'Assinado'),
        ('ENVIADO', 'Enviado para SEFAZ'),
        ('AUTORIZADO', 'Autorizado'),
        ('REJEITADO', 'Rejeitado'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        'cadastros.Empresa', on_delete=models.PROTECT,
        related_name='lotes_nfe', verbose_name='Empresa'
    )
    numero_lote = models.IntegerField(verbose_name='Número do Lote')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DIGITACAO')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data Criação')
    xml_retorno = models.TextField(blank=True, verbose_name='XML Retorno SEFAZ')
    protocolo = models.CharField(max_length=50, blank=True, verbose_name='Protocolo')
    mensagem_retorno = models.TextField(blank=True, verbose_name='Mensagem Retorno')

    class Meta:
        db_table = 'lotes_nfe'
        verbose_name = 'Lote NF-e'
        verbose_name_plural = 'Lotes NF-e'
        ordering = ['-data_criacao']
        unique_together = [['empresa', 'numero_lote']]

    def __str__(self):
        return f'Lote {self.numero_lote} - {self.get_status_display()}'


class NFe(models.Model):
    MODELO_CHOICES = [
        ('55', 'NF-e (55)'),
        ('65', 'NFC-e (65)'),
    ]

    TIPO_EMISSAO_CHOICES = [
        (1, 'Normal'),
        (2, 'Contingência SCAN'),
        (3, 'Contingência DPEC'),
        (4, 'Contingência FSDA'),
        (5, 'Contingência SVC'),
        (6, 'Contingência SVC-RS'),
        (7, 'Contingência SVC-SP'),
        (9, 'Contingência Off-line NFC-e'),
    ]

    STATUS_CHOICES = [
        ('DIGITACAO', 'Em Digitação'),
        ('VALIDADO', 'Validado'),
        ('ASSINADO', 'Assinado'),
        ('ENVIADO', 'Enviado para SEFAZ'),
        ('AUTORIZADO', 'Autorizado'),
        ('REJEITADO', 'Rejeitado'),
        ('CANCELADO', 'Cancelado'),
        ('DENEGADO', 'Denegado'),
        ('CCE', 'Carta de Correção'),
    ]

    movimentacao = models.ForeignKey(
        'cadastros.MovimentacaoEstoque', on_delete=models.PROTECT,
        related_name='notas_fiscais', verbose_name='Movimentação Origem',
        null=True, blank=True
    )
    empresa = models.ForeignKey(
        'cadastros.Empresa', on_delete=models.PROTECT,
        related_name='notas_fiscais', verbose_name='Empresa'
    )
    destinatario = models.ForeignKey(
        'cadastros.Pessoa', on_delete=models.PROTECT,
        related_name='notas_fiscais_recebidas', verbose_name='Destinatário'
    )
    lote = models.ForeignKey(
        LoteNFe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notas', verbose_name='Lote'
    )

    modelo = models.CharField(max_length=2, choices=MODELO_CHOICES, default='55', verbose_name='Modelo')
    serie = models.IntegerField(default=1, verbose_name='Série')
    numero = models.IntegerField(verbose_name='Número')
    chave_acesso = models.CharField(max_length=44, unique=True, verbose_name='Chave de Acesso')
    tipo_emissao = models.IntegerField(choices=TIPO_EMISSAO_CHOICES, default=1, verbose_name='Tipo Emissão')
    natureza_operacao = models.CharField(max_length=255, verbose_name='Natureza da Operação')
    finalidade = models.IntegerField(
        choices=[(1, 'Normal'), (2, 'Complementar'), (3, 'Ajuste'), (4, 'Devolução')],
        default=1, verbose_name='Finalidade'
    )
    consumo_final = models.BooleanField(default=False, verbose_name='Consumo Final')
    presenca_comprador = models.IntegerField(
        choices=[(0, 'Não'), (1, 'Presencial'), (2, 'Internet'), (3, 'Teleatendimento'),
                 (4, 'NFC-e entrega'), (5, 'Presencial fora'), (9, 'Outros')],
        default=1, verbose_name='Presença do Comprador'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DIGITACAO', verbose_name='Status')
    protocolo = models.CharField(max_length=50, blank=True, verbose_name='Protocolo SEFAZ')
    xml_enviado = models.TextField(blank=True, verbose_name='XML Enviado')
    xml_retorno = models.TextField(blank=True, verbose_name='XML Retorno')
    xml_danfe = models.TextField(blank=True, verbose_name='XML DANFE')
    mensagem_retorno = models.TextField(blank=True, verbose_name='Mensagem Retorno')
    codigo_erro = models.CharField(max_length=10, blank=True, verbose_name='Código Erro')

    data_emissao = models.DateTimeField(auto_now_add=True, verbose_name='Data Emissão')
    data_envio = models.DateTimeField(null=True, blank=True, verbose_name='Data Envio')
    data_autorizacao = models.DateTimeField(null=True, blank=True, verbose_name='Data Autorização')
    data_cancelamento = models.DateTimeField(null=True, blank=True, verbose_name='Data Cancelamento')
    justificativa_cancelamento = models.TextField(blank=True, verbose_name='Justificativa Cancelamento')

    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor Total')
    valor_base_calculo_icms = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='BC ICMS')
    valor_icms = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor ICMS')
    valor_base_calculo_icms_st = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='BC ICMS ST')
    valor_icms_st = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor ICMS ST')
    valor_total_produtos = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Total Produtos')
    valor_frete = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor Frete')
    valor_seguro = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor Seguro')
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor Desconto')
    valor_outras_despesas = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Outras Despesas')
    valor_ipi = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor IPI')
    valor_pis = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor PIS')
    valor_cofins = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor COFINS')

    informacoes_adicionais = models.TextField(blank=True, verbose_name='Informações Adicionais')

    # ── Transporte / Frete ──
    modalidade_frete = models.IntegerField(
        choices=[
            (0, '0 - Contratação Frete por conta Emitente'),
            (1, '1 - Contratação Frete por conta Destinatário'),
            (2, '2 - Contratação Frete por conta Terceiros'),
            (3, '3 - Transporte Próprio por conta Remetente'),
            (4, '4 - Transporte Próprio por conta Destinatário'),
            (9, '9 - Sem Ocorrência de Transporte'),
        ],
        default=9, verbose_name='Modalidade do Frete'
    )
    transportadora = models.ForeignKey(
        'cadastros.Pessoa', on_delete=models.PROTECT,
        related_name='notas_fiscais_transporte', verbose_name='Transportadora',
        null=True, blank=True
    )
    volumes = models.DecimalField(max_digits=6, decimal_places=0, default=0, verbose_name='Quantidade de Volumes')
    especie = models.CharField(max_length=60, blank=True, verbose_name='Espécie',
                               help_text='Ex.: CAIXA, PALLET, SACO')
    peso_bruto = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='Peso Bruto (kg)')
    peso_liquido = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='Peso Líquido (kg)')

    class Meta:
        db_table = 'nfe'
        verbose_name = 'NF-e / NFC-e'
        verbose_name_plural = 'NF-e / NFC-e'
        ordering = ['-data_emissao']
        unique_together = [['empresa', 'serie', 'numero']]

    def __str__(self):
        return f'{self.get_modelo_display()} #{self.numero} - {self.destinatario.nome}'

    @property
    def is_nfce(self):
        return self.modelo == '65'

    @property
    def is_autorizada(self):
        return self.status == 'AUTORIZADO'


class NFeItem(models.Model):
    nfe = models.ForeignKey(
        NFe, on_delete=models.CASCADE,
        related_name='itens', verbose_name='NF-e'
    )
    item_movimentacao = models.ForeignKey(
        'cadastros.ItemMovimentacaoEstoque', on_delete=models.PROTECT,
        related_name='itens_nfe', null=True, blank=True,
        verbose_name='Item Movimentação'
    )
    produto = models.ForeignKey(
        'cadastros.Produto', on_delete=models.PROTECT,
        related_name='itens_nfe', verbose_name='Produto'
    )
    numero_item = models.IntegerField(verbose_name='Nº Item')
    codigo_produto = models.CharField(max_length=60, verbose_name='Código Produto')
    ean = models.CharField(max_length=14, blank=True, default='SEM GTIN', verbose_name='EAN')
    nome = models.CharField(max_length=255, verbose_name='Nome')
    ncm = models.CharField(max_length=8, verbose_name='NCM')
    cest = models.CharField(max_length=7, default='0000000', verbose_name='CEST')
    cfop = models.CharField(max_length=4, verbose_name='CFOP')
    unidade = models.CharField(max_length=6, verbose_name='Unidade')
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, verbose_name='Quantidade')
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=6, verbose_name='Valor Unitário')
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Valor Total')
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Desconto')
    valor_frete = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Frete')
    valor_seguro = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Seguro')
    valor_outras = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Outras Despesas')
    informacoes_adicionais = models.CharField(max_length=500, blank=True, verbose_name='Info Adicionais')

    origem = models.CharField(max_length=1, default='0', verbose_name='Origem')
    cst_icms = models.CharField(max_length=3, blank=True, default='', verbose_name='CST ICMS')
    csosn = models.CharField(max_length=4, blank=True, default='', verbose_name='CSOSN')
    aliquota_icms = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Aliq ICMS %')
    base_calculo_icms = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='BC ICMS')
    valor_icms = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor ICMS')

    cst_pis = models.CharField(max_length=2, blank=True, default='', verbose_name='CST PIS')
    aliquota_pis = models.DecimalField(max_digits=5, decimal_places=4, default=0, verbose_name='Aliq PIS %')
    base_calculo_pis = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='BC PIS')
    valor_pis = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor PIS')

    cst_cofins = models.CharField(max_length=2, blank=True, default='', verbose_name='CST COFINS')
    aliquota_cofins = models.DecimalField(max_digits=5, decimal_places=4, default=0, verbose_name='Aliq COFINS %')
    base_calculo_cofins = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='BC COFINS')
    valor_cofins = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor COFINS')

    cst_ipi = models.CharField(max_length=2, blank=True, default='', verbose_name='CST IPI')
    aliquota_ipi = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Aliq IPI %')
    base_calculo_ipi = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='BC IPI')
    valor_ipi = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor IPI')

    class Meta:
        db_table = 'nfe_itens'
        verbose_name = 'Item NF-e'
        verbose_name_plural = 'Itens NF-e'
        ordering = ['numero_item']

    def __str__(self):
        return f'{self.numero_item} - {self.nome}'


class NFePagamento(models.Model):
    nfe = models.ForeignKey(
        NFe, on_delete=models.CASCADE,
        related_name='pagamentos', verbose_name='NF-e'
    )
    tipo_pagamento = models.ForeignKey(
        'cadastros.TipoPagamento', on_delete=models.PROTECT,
        verbose_name='Tipo Pagamento'
    )
    forma_pagamento = models.IntegerField(
        verbose_name='Forma Pagamento NF-e',
        help_text='01=Dinheiro, 02=Cheque, 03=Cartão Crédito, 04=Cartão Débito, '
                  '05=Cartão Crédito Loja, 10=Vale Alimentação, 11=Vale Refeição, '
                  '12=Vale Presente, 13=Vale Combustível, 14=Duplicata Mercantil, '
                  '15=Boleto, 16=Depósito, 17=Pagamento Instantâneo (PIX), '
                  '18=Transferência, 19=Fidelidade, 90=Sem pagamento, 99=Outros'
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Valor')
    integracao_pagamento = models.CharField(
        max_length=1, choices=[('N', 'NFC-e integrada'), ('O', 'Outros')],
        default='O'
    )
    cnpj_intermediador = models.CharField(max_length=18, blank=True, verbose_name='CNPJ Intermediador')
    bandeira = models.CharField(max_length=50, blank=True, verbose_name='Bandeira Cartão')

    class Meta:
        db_table = 'nfe_pagamentos'
        verbose_name = 'Pagamento NF-e'
        verbose_name_plural = 'Pagamentos NF-e'

    def __str__(self):
        return f'{self.get_forma_pagamento_display()} - R$ {self.valor}'


class NFeEvento(models.Model):
    TIPO_CHOICES = [
        ('CANCELAMENTO', 'Cancelamento'),
        ('CCE', 'Carta de Correção'),
    ]

    nfe = models.ForeignKey(
        NFe, on_delete=models.CASCADE,
        related_name='eventos', verbose_name='NF-e'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo Evento')
    sequencia = models.IntegerField(default=1, verbose_name='Sequência')
    protocolo = models.CharField(max_length=50, blank=True, verbose_name='Protocolo')
    data_evento = models.DateTimeField(auto_now_add=True, verbose_name='Data Evento')
    xml_enviado = models.TextField(blank=True, verbose_name='XML Enviado')
    xml_retorno = models.TextField(blank=True, verbose_name='XML Retorno')
    justificativa = models.TextField(verbose_name='Justificativa')
    numero_cce = models.IntegerField(null=True, blank=True, verbose_name='Nº CCE')
    correcao_cce = models.TextField(blank=True, verbose_name='Correção')

    class Meta:
        db_table = 'nfe_eventos'
        verbose_name = 'Evento NF-e'
        verbose_name_plural = 'Eventos NF-e'
        ordering = ['-data_evento']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.nfe.chave_acesso}'
