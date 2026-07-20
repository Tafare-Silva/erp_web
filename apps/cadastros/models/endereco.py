from django.db import models
from .pessoa import Pessoa
from .reservados import Cidade


class EnderecoPessoa(models.Model):
    TIPO_CHOICES = [
        ('RESIDENCIAL', 'Residencial'),
        ('COMERCIAL', 'Comercial'),
        ('COBRANCA', 'Cobrança'),
        ('ENTREGA', 'Entrega'),
        ('OUTRO', 'Outro'),
    ]

    chave = models.AutoField(
        primary_key=True,
        verbose_name='Código'
    )
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='enderecos',
        verbose_name='Pessoa'
    )
    tipo_endereco = models.CharField(
        max_length=50,
        choices=TIPO_CHOICES,
        default='RESIDENCIAL',
        verbose_name='Tipo',
        help_text='Ex: Residencial, Comercial, Cobrança, Entrega'
    )
    cep = models.CharField(
        max_length=9,
        verbose_name='CEP'
    )
    logradouro = models.CharField(
        max_length=255,
        verbose_name='Logradouro',
        help_text='Nome da rua, avenida, etc'
    )
    numero = models.CharField(
        max_length=10,
        verbose_name='Número'
    )
    complemento = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Complemento',
        help_text='Apto, sala, bloco, etc'
    )
    bairro = models.CharField(
        max_length=100,
        verbose_name='Bairro'
    )
    cidade = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        related_name='enderecos',
        verbose_name='Cidade'
    )
    ponto_referencia = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Ponto de Referência'
    )

    class Meta:
        db_table = 'endereco_pessoas'
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
        ordering = ['pessoa', 'tipo_endereco']

    def __str__(self):
        return f"{self.logradouro}, {self.numero} - {self.bairro}"

    @property
    def endereco_completo(self):
        """Retorna o endereço formatado completo."""
        partes = [
            f"{self.logradouro}, {self.numero}",
            f"{self.complemento}" if self.complemento else None,
            f"{self.bairro}",
            f"{self.cidade}",
            f"CEP: {self.cep}"
        ]
        return " - ".join(filter(None, partes))


class EnderecoPrincipalPessoa(models.Model):
    """
    Relacionamento que indica qual é o endereço principal da pessoa.
    """
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='endereco_principal_rel',
        verbose_name='Pessoa'
    )
    endereco = models.ForeignKey(
        EnderecoPessoa,
        on_delete=models.CASCADE,
        related_name='principal_de',
        verbose_name='Endereço Principal'
    )

    class Meta:
        db_table = 'endereco_principal_pessoas'
        verbose_name = 'Endereço Principal'
        verbose_name_plural = 'Endereços Principais'

    def __str__(self):
        return f"Endereço principal de {self.pessoa}"