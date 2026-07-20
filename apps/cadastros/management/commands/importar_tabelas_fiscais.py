"""
Comando Django para importar tabelas fiscais oficiais.
Uso: python manage.py importar_tabelas_fiscais
"""
from django.core.management.base import BaseCommand
from apps.cadastros.models import NCM, CFOP, CST
import pandas as pd
import requests
from io import BytesIO


class Command(BaseCommand):
    help = 'Importa tabelas fiscais oficiais (NCM, CFOP, CST)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tabela',
            type=str,
            choices=['ncm', 'cfop', 'cst', 'todas'],
            default='todas',
            help='Qual tabela importar (ncm, cfop, cst ou todas)'
        )

    def handle(self, *args, **options):
        tabela = options['tabela']
        
        if tabela in ['ncm', 'todas']:
            self.importar_ncm()
        
        if tabela in ['cfop', 'todas']:
            self.importar_cfop()
        
        if tabela in ['cst', 'todas']:
            self.importar_cst()
        
        self.stdout.write(self.style.SUCCESS('✅ Importação concluída!'))

    def importar_ncm(self):
        """Importa tabela NCM da Receita Federal."""
        self.stdout.write('📦 Importando NCM...')
        
        # URL oficial do governo (pode precisar atualizar)
        # Alternativa: baixar manualmente e colocar na pasta /data/
        url = "http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=mhWPkJbIKfU="
        
        try:
            # Tentar baixar do site oficial
            response = requests.get(url, timeout=30)
            df = pd.read_excel(BytesIO(response.content))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Não foi possível baixar automaticamente: {e}'
            ))
            self.stdout.write(
                'Baixe manualmente de: '
                'https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/'
                'classificacao-fiscal-de-mercadorias/download-ncm-nomenclatura-comum-do-mercosul'
            )
            return
        
        # Processar e importar
        contador = 0
        for _, row in df.iterrows():
            try:
                ncm_codigo = str(row['Código']).replace('.', '').strip()
                descricao = str(row['Descrição']).strip()
                
                if len(ncm_codigo) == 8:  # NCM tem 8 dígitos
                    NCM.objects.update_or_create(
                        ncm=ncm_codigo,
                        defaults={
                            'descricao': descricao,
                            'nome': descricao[:100]  # Resumo
                        }
                    )
                    contador += 1
            except Exception as e:
                continue
        
        self.stdout.write(self.style.SUCCESS(f'✅ {contador} NCMs importados!'))

    def importar_cfop(self):
        """Importa tabela CFOP oficial."""
        self.stdout.write('📋 Importando CFOP...')
        
        # URL oficial do Siscomex
        url = "https://www.gov.br/siscomex/pt-br/informacoes/tratamento-administrativos/tratamento-administrativo-de-exportacao-1/cfop.xlsx"
        
        try:
            response = requests.get(url, timeout=30)
            df = pd.read_excel(BytesIO(response.content), skiprows=7)  # Pular cabeçalho
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Erro ao baixar CFOP: {e}'))
            self._importar_cfop_manual()
            return
        
        contador = 0
        for _, row in df.iterrows():
            try:
                cfop_codigo = str(row.iloc[0]).strip()
                descricao = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                
                if cfop_codigo and cfop_codigo.isdigit() and len(cfop_codigo) == 4:
                    CFOP.objects.update_or_create(
                        cfop=cfop_codigo,
                        defaults={'descricao': descricao}
                    )
                    contador += 1
            except Exception:
                continue
        
        self.stdout.write(self.style.SUCCESS(f'✅ {contador} CFOPs importados!'))

    def _importar_cfop_manual(self):
        """CFOP mais comuns para importação manual."""
        self.stdout.write('📝 Importando CFOPs principais...')
        
        cfops_principais = [
            ('5101', 'Venda de produção do estabelecimento'),
            ('5102', 'Venda de mercadoria adquirida ou recebida de terceiros'),
            ('5403', 'Venda de mercadoria adquirida ou recebida de terceiros em operação com mercadoria sujeita ao regime de substituição tributária, na condição de substituto tributário'),
            ('5405', 'Venda de mercadoria adquirida ou recebida de terceiros em operação com mercadoria sujeita ao regime de substituição tributária, na condição de substituído tributário'),
            ('6101', 'Venda de produção do estabelecimento'),
            ('6102', 'Venda de mercadoria adquirida ou recebida de terceiros'),
            ('6108', 'Venda de mercadoria adquirida ou recebida de terceiros, destinada à Zona Franca de Manaus ou Áreas de Livre Comércio'),
            ('6403', 'Venda de mercadoria adquirida ou recebida de terceiros em operação com mercadoria sujeita ao regime de substituição tributária, na condição de substituto tributário'),
            ('1102', 'Compra para comercialização'),
            ('1403', 'Compra para comercialização em operação com mercadoria sujeita ao regime de substituição tributária'),
            ('2102', 'Compra para comercialização'),
            ('2403', 'Compra para comercialização em operação com mercadoria sujeita ao regime de substituição tributária'),
            ('5949', 'Outra saída de mercadoria ou prestação de serviço não especificado'),
            ('6949', 'Outra saída de mercadoria ou prestação de serviço não especificado'),
        ]
        
        for cfop, descricao in cfops_principais:
            CFOP.objects.update_or_create(
                cfop=cfop,
                defaults={'descricao': descricao}
            )
        
        self.stdout.write(self.style.SUCCESS(f'✅ {len(cfops_principais)} CFOPs principais importados!'))

    def importar_cst(self):
        """Importa tabelas CST (ICMS, PIS, COFINS, IPI)."""
        self.stdout.write('🏷️  Importando CST...')
        
        # CST ICMS
        cst_icms = [
            ('00', 'ICMS', 'Tributada integralmente'),
            ('10', 'ICMS', 'Tributada e com cobrança do ICMS por substituição tributária'),
            ('20', 'ICMS', 'Com redução de base de cálculo'),
            ('30', 'ICMS', 'Isenta ou não tributada e com cobrança do ICMS por substituição tributária'),
            ('40', 'ICMS', 'Isenta'),
            ('41', 'ICMS', 'Não tributada'),
            ('50', 'ICMS', 'Suspensão'),
            ('51', 'ICMS', 'Diferimento'),
            ('60', 'ICMS', 'ICMS cobrado anteriormente por substituição tributária'),
            ('70', 'ICMS', 'Com redução de base de cálculo e cobrança do ICMS por substituição tributária'),
            ('90', 'ICMS', 'Outras'),
        ]
        
        # CST PIS/COFINS
        cst_pis_cofins = [
            ('01', 'PIS', 'Operação Tributável com Alíquota Básica'),
            ('01', 'COFINS', 'Operação Tributável com Alíquota Básica'),
            ('02', 'PIS', 'Operação Tributável com Alíquota Diferenciada'),
            ('02', 'COFINS', 'Operação Tributável com Alíquota Diferenciada'),
            ('04', 'PIS', 'Operação Tributável Monofásica - Revenda a Alíquota Zero'),
            ('04', 'COFINS', 'Operação Tributável Monofásica - Revenda a Alíquota Zero'),
            ('06', 'PIS', 'Operação Tributável a Alíquota Zero'),
            ('06', 'COFINS', 'Operação Tributável a Alíquota Zero'),
            ('07', 'PIS', 'Operação Isenta da Contribuição'),
            ('07', 'COFINS', 'Operação Isenta da Contribuição'),
            ('08', 'PIS', 'Operação sem Incidência da Contribuição'),
            ('08', 'COFINS', 'Operação sem Incidência da Contribuição'),
            ('09', 'PIS', 'Operação com Suspensão da Contribuição'),
            ('09', 'COFINS', 'Operação com Suspensão da Contribuição'),
        ]
        
        # CST IPI
        cst_ipi = [
            ('00', 'IPI', 'Entrada com Recuperação de Crédito'),
            ('01', 'IPI', 'Entrada Tributada com Alíquota Zero'),
            ('02', 'IPI', 'Entrada Isenta'),
            ('03', 'IPI', 'Entrada Não-Tributada'),
            ('04', 'IPI', 'Entrada Imune'),
            ('05', 'IPI', 'Entrada com Suspensão'),
            ('49', 'IPI', 'Outras Entradas'),
            ('50', 'IPI', 'Saída Tributada'),
            ('51', 'IPI', 'Saída Tributada com Alíquota Zero'),
            ('52', 'IPI', 'Saída Isenta'),
            ('53', 'IPI', 'Saída Não-Tributada'),
            ('54', 'IPI', 'Saída Imune'),
            ('55', 'IPI', 'Saída com Suspensão'),
            ('99', 'IPI', 'Outras Saídas'),
        ]
        
        # Importar todos
        contador = 0
        for cst, tipo, descricao in cst_icms + cst_pis_cofins + cst_ipi:
            CST.objects.update_or_create(
                cst=cst,
                tipo_imposto=tipo,
                defaults={'descricao': descricao}
            )
            contador += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ {contador} CSTs importados!'))