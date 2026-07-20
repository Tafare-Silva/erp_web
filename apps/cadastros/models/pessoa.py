from django.db import models


class Pessoa(models.Model):
    chave = models.AutoField(
        primary_key=True,
        verbose_name='Chave'
    )
    nome = models.CharField(
        max_length=255,
        verbose_name='Nome/Razão Social'
    )
    cpf_cnpj = models.CharField(
        max_length=18,
        unique=True,
        verbose_name='CPF/CNPJ'
    )
    rg_ie = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='RG/IE'
    )
    nome_fantasia = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Nome Fantasia'
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='E-mail'
    )
    telefone_fixo = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='Telefone Fixo'
    )
    celular_principal = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        verbose_name='Celular'
    )
    
    inativo = models.BooleanField(default=False, verbose_name='Inativo')
    cliente = models.BooleanField(default=True, verbose_name='Cliente')
    fornecedor = models.BooleanField(default=False, verbose_name='Fornecedor')
    funcionario = models.BooleanField(default=False, verbose_name='Funcionário')
    vendedor = models.BooleanField(default=False, verbose_name='Vendedor')
    usuario = models.BooleanField(default=False, verbose_name='Usuário')
    motorista = models.BooleanField(default=False, verbose_name='Motorista')
    transportador = models.BooleanField(default=False, verbose_name='Transportador')
    
    somar_frete_bc_icms_st = models.BooleanField(default=True)
    somar_ipi_bc_icms_st = models.BooleanField(default=True)
    somar_oda_bc_icms_st = models.BooleanField(default=True)
    nao_destacar_impostos_nfse = models.BooleanField(default=False)
    ins_municipal = models.CharField(max_length=20, blank=True, null=True)
    
    data_cadastro = models.DateField(auto_now_add=True)
    data_ultima_atualizacao = models.DateField(auto_now=True, null=True, blank=True)
    data_para_vencimentos = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)
    ddg_0800 = models.CharField(max_length=255, blank=True, null=True)
    rota = models.CharField(max_length=255, blank=True, null=True)
    cep_migracao = models.CharField(max_length=20, blank=True, null=True)
    situacao_cadastro = models.CharField(
        max_length=255,
        default='NORMAL',
        blank=True,
        verbose_name='Situação Cadastro'
    )

    class Meta:
        db_table = 'pessoas'
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def is_pf(self):
        cpf_limpo = ''.join(filter(str.isdigit, self.cpf_cnpj or ''))
        return len(cpf_limpo) == 11

    def get_classificacoes(self):
        c = []
        if self.cliente: c.append('Cliente')
        if self.fornecedor: c.append('Fornecedor')
        if self.funcionario: c.append('Funcionário')
        if self.vendedor: c.append('Vendedor')
        return ', '.join(c) if c else 'Nenhuma'


class PessoaFisica(models.Model):
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='dados_pf',
        verbose_name='Pessoa'
    )
    data_nascimento = models.DateField(null=True, blank=True)
    estado_civil = models.CharField(max_length=255, blank=True, null=True)
    nome_pai = models.CharField(max_length=255, blank=True, null=True)
    nome_mae = models.CharField(max_length=255, blank=True, null=True)
    empresa_trabalho = models.CharField(max_length=255, blank=True, null=True)
    profissao = models.CharField(max_length=255, blank=True, null=True)
    telefone_trabalho = models.CharField(max_length=15, blank=True, null=True)
    data_admissao = models.DateField(null=True, blank=True)
    nome_conjuge = models.CharField(max_length=255, blank=True, null=True)
    renda_familiar = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'pessoas_fisicas'
        verbose_name = 'Pessoa Física'
        verbose_name_plural = 'Pessoas Físicas'


class FuncionarioDetalhes(models.Model):
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='detalhes_funcionario',
        verbose_name='Pessoa'
    )
    e_vendedor = models.BooleanField(default=False, verbose_name='É Vendedor?')

    class Meta:
        db_table = 'funcionarios'
        verbose_name = 'Detalhes Funcionário'
        verbose_name_plural = 'Detalhes Funcionários'

    def __str__(self):
        return f"{self.pessoa.nome} - Vendedor: {self.e_vendedor}"


# Aliases para facilitar o uso
Cliente = Pessoa
Fornecedor = Pessoa
Funcionario = Pessoa
Vendedor = Pessoa
Transportador = Pessoa