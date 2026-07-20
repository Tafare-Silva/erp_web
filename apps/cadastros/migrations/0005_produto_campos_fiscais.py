from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0004_movimentacaoestoque_cfop_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='origem',
            field=models.CharField(
                choices=[
                    ('0', '0 - Nacional'),
                    ('1', '1 - Estrangeira - Importação direta'),
                    ('2', '2 - Estrangeira - Adquirida no mercado interno'),
                    ('3', '3 - Nacional - Conteúdo de Importação > 40%'),
                    ('4', '4 - Nacional - Processos Produtivos Básicos'),
                    ('5', '5 - Nacional - Conteúdo de Importação ≤ 40%'),
                    ('6', '6 - Estrangeira - Importação direta, sem similar nacional'),
                    ('7', '7 - Estrangeira - Merc. interno, sem similar nacional'),
                    ('8', '8 - Nacional - Conteúdo de Importação > 70%'),
                ],
                default='0',
                max_length=1,
                verbose_name='Origem da Mercadoria',
            ),
        ),
        migrations.AddField(
            model_name='produto',
            name='cst_icms',
            field=models.CharField(blank=True, default='', max_length=3, verbose_name='CST/CSOSN ICMS'),
        ),
        migrations.AddField(
            model_name='produto',
            name='cfop_venda_estadual',
            field=models.CharField(blank=True, default='', max_length=4, verbose_name='CFOP Venda Estadual'),
        ),
        migrations.AddField(
            model_name='produto',
            name='cfop_venda_interestadual',
            field=models.CharField(blank=True, default='', max_length=4, verbose_name='CFOP Venda Interestadual'),
        ),
        migrations.AddField(
            model_name='produto',
            name='aliquota_icms',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Alíquota ICMS (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='reducao_bc_icms',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Redução BC ICMS (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='modalidade_bc_icms',
            field=models.IntegerField(default=3, verbose_name='Modalidade BC ICMS'),
        ),
        migrations.AddField(
            model_name='produto',
            name='aliquota_icms_st',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Alíquota ICMS-ST (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='aliquota_mva',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='MVA (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='reducao_bc_icms_st',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Redução BC ICMS-ST (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='cst_pis',
            field=models.CharField(blank=True, default='', max_length=2, verbose_name='CST PIS'),
        ),
        migrations.AddField(
            model_name='produto',
            name='aliquota_pis',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=5, verbose_name='Alíquota PIS (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='cst_cofins',
            field=models.CharField(blank=True, default='', max_length=2, verbose_name='CST COFINS'),
        ),
        migrations.AddField(
            model_name='produto',
            name='aliquota_cofins',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=5, verbose_name='Alíquota COFINS (%)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='cst_ipi',
            field=models.CharField(blank=True, max_length=2, null=True, verbose_name='CST IPI'),
        ),
        migrations.AddField(
            model_name='produto',
            name='aliquota_ipi',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Alíquota IPI (%)'),
        ),
    ]
