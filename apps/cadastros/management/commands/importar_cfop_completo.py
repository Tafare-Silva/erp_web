from django.core.management.base import BaseCommand
from apps.cadastros.models import CFOP


class Command(BaseCommand):
    help = 'Importa CFOPs completos'

    def handle(self, *args, **options):
        cfops = [
            # VENDAS DENTRO DO ESTADO
            ('5101', 'Venda de produção do estabelecimento', 'Venda dentro do estado de produto fabricado'),
            ('5102', 'Venda de mercadoria adquirida ou recebida de terceiros', 'Venda dentro do estado de produto comprado para revenda'),
            ('5103', 'Venda de produção do estabelecimento, efetuada fora do estabelecimento', 'Venda ambulante dentro do estado'),
            ('5104', 'Venda de mercadoria adquirida ou recebida de terceiros, efetuada fora do estabelecimento', 'Venda ambulante de mercadoria de terceiros'),
            ('5405', 'Venda de mercadoria sujeita ao regime de substituição tributária', 'Venda com ST dentro do estado'),
            ('5949', 'Outra saída não especificada', 'Outras saídas dentro do estado'),
            
            # VENDAS FORA DO ESTADO
            ('6101', 'Venda de produção do estabelecimento', 'Venda interestadual de produto fabricado'),
            ('6102', 'Venda de mercadoria adquirida ou recebida de terceiros', 'Venda interestadual de produto comprado para revenda'),
            ('6103', 'Venda de produção do estabelecimento, efetuada fora do estabelecimento', 'Venda ambulante interestadual'),
            ('6104', 'Venda de mercadoria adquirida ou recebida de terceiros, efetuada fora do estabelecimento', 'Venda ambulante interestadual de terceiros'),
            ('6405', 'Venda de mercadoria sujeita ao regime de substituição tributária', 'Venda com ST interestadual'),
            ('6949', 'Outra saída não especificada', 'Outras saídas interestaduais'),
            
            # COMPRAS DENTRO DO ESTADO
            ('1102', 'Compra para comercialização', 'Compra para revenda dentro do estado'),
            ('1101', 'Compra para industrialização ou produção rural', 'Compra de matéria-prima dentro do estado'),
            ('1556', 'Compra de material para uso ou consumo', 'Material de uso/consumo dentro do estado'),
            ('1949', 'Outra entrada não especificada', 'Outras entradas dentro do estado'),
            
            # COMPRAS FORA DO ESTADO
            ('2102', 'Compra para comercialização', 'Compra para revenda interestadual'),
            ('2101', 'Compra para industrialização ou produção rural', 'Compra de matéria-prima interestadual'),
            ('2556', 'Compra de material para uso ou consumo', 'Material de uso/consumo interestadual'),
            ('2949', 'Outra entrada não especificada', 'Outras entradas interestaduais'),
            
            # DEVOLUÇÃO
            ('5202', 'Devolução de compra para comercialização', 'Devolução de compra dentro do estado'),
            ('5201', 'Devolução de compra para industrialização', 'Devolução de matéria-prima dentro do estado'),
            ('6202', 'Devolução de compra para comercialização', 'Devolução de compra interestadual'),
            ('6201', 'Devolução de compra para industrialização', 'Devolução de matéria-prima interestadual'),
            ('1202', 'Devolução de venda de mercadoria adquirida de terceiros', 'Entrada por devolução dentro do estado'),
            ('2202', 'Devolução de venda de mercadoria adquirida de terceiros', 'Entrada por devolução interestadual'),
            
            # TRANSFERÊNCIA
            ('5151', 'Transferência de produção do estabelecimento', 'Transferência de produção própria dentro do estado'),
            ('5152', 'Transferência de mercadoria adquirida de terceiros', 'Transferência de revenda dentro do estado'),
            ('6151', 'Transferência de produção do estabelecimento', 'Transferência de produção própria interestadual'),
            ('6152', 'Transferência de mercadoria adquirida de terceiros', 'Transferência de revenda interestadual'),
            ('1152', 'Entrada de mercadoria recebida em transferência', 'Recebimento em transferência dentro do estado'),
            ('2152', 'Entrada de mercadoria recebida em transferência', 'Recebimento em transferência interestadual'),
            
            # REMESSA
            ('5915', 'Remessa para conserto ou reparo', 'Remessa para conserto dentro do estado'),
            ('5916', 'Retorno de conserto ou reparo', 'Retorno de conserto dentro do estado'),
            ('5917', 'Remessa em consignação mercantil', 'Consignação dentro do estado'),
            ('5918', 'Devolução de consignação mercantil', 'Devolução de consignação dentro do estado'),
            ('6915', 'Remessa para conserto ou reparo', 'Remessa para conserto interestadual'),
            ('6916', 'Retorno de conserto ou reparo', 'Retorno de conserto interestadual'),
            ('6917', 'Remessa em consignação mercantil', 'Consignação interestadual'),
            ('6918', 'Devolução de consignação mercantil', 'Devolução de consignação interestadual'),
            
            # BONIFICAÇÃO/BRINDE
            ('5910', 'Remessa em bonificação, doação ou brinde', 'Bonificação dentro do estado'),
            ('6910', 'Remessa em bonificação, doação ou brinde', 'Bonificação interestadual'),
            
            # DEMONSTRAÇÃO
            ('5912', 'Remessa para demonstração', 'Demonstração dentro do estado'),
            ('5913', 'Retorno de demonstração', 'Retorno de demonstração dentro do estado'),
            ('6912', 'Remessa para demonstração', 'Demonstração interestadual'),
            ('6913', 'Retorno de demonstração', 'Retorno de demonstração interestadual'),
            
            # EXPORTAÇÃO
            ('7101', 'Venda de produção do estabelecimento para o exterior', 'Exportação direta'),
            ('7102', 'Venda de mercadoria adquirida de terceiros para o exterior', 'Exportação de revenda'),
        ]

        contador = 0
        for codigo, nome, descricao in cfops:
            # ✅ CAMPO CORRETO: cfop (não codigo)
            cfop, created = CFOP.objects.get_or_create(
                cfop=codigo,
                defaults={
                    'nome': nome,
                    'descricao': descricao,
                    'aplicacao': 'Saída' if codigo[0] in ['5', '6', '7'] else 'Entrada'
                }
            )
            if created:
                contador += 1
                self.stdout.write(f'✅ {codigo} - {nome}')
            else:
                self.stdout.write(f'⏭️  {codigo} - já existe')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 {contador} CFOPs importados!'))