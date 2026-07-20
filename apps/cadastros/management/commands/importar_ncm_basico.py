from django.core.management.base import BaseCommand
from apps.cadastros.models import NCM


class Command(BaseCommand):
    help = 'Importa NCMs básicos mais comuns'

    def handle(self, *args, **options):
        # Lista dos NCMs mais comuns em ERPs
        ncms_basicos = [
            ('00000000', 'Não Tributado', 'Produto sem NCM específico'),
            ('84714100', 'Computadores portáteis', 'Notebooks e laptops'),
            ('84713000', 'Computadores de mesa', 'Desktops e all-in-one'),
            ('85171231', 'Telefones celulares', 'Smartphones'),
            ('94036000', 'Móveis de madeira', 'Móveis para escritório de madeira'),
            ('64029900', 'Calçados', 'Outros calçados'),
            ('61091000', 'Camisetas de malha', 'T-shirts de algodão'),
            ('62114200', 'Vestidos femininos', 'Vestidos de algodão'),
            ('15171000', 'Margarina', 'Margarina exceto margarina líquida'),
            ('19053100', 'Biscoitos doces', 'Biscoitos adicionados de edulcorante'),
            ('22021000', 'Refrigerantes', 'Águas gaseificadas açucaradas'),
            ('33049900', 'Cosméticos', 'Outros produtos de beleza'),
            ('39241000', 'Utensílios de plástico', 'Serviços de mesa e artigos'),
            ('69111000', 'Louças de porcelana', 'Artigos para serviço de mesa'),
            ('73211100', 'Fogões a gás', 'Fogões de uso doméstico'),
            ('85165000', 'Micro-ondas', 'Fornos de micro-ondas'),
            ('84501100', 'Máquinas de lavar roupa', 'De capacidade até 10 kg'),
            ('85094000', 'Liquidificadores', 'Trituradores e misturadores de alimentos'),
            ('95030010', 'Brinquedos', 'Triciclos, patinetes e carros de pedais'),
            ('49019900', 'Livros impressos', 'Outros livros, brochuras e impressos'),
        ]

        contador = 0
        for ncm_cod, nome, descricao in ncms_basicos:
            ncm, created = NCM.objects.get_or_create(
                ncm=ncm_cod,
                defaults={
                    'nome': nome,
                    'descricao': descricao
                }
            )
            if created:
                contador += 1
                self.stdout.write(f'✅ {ncm_cod} - {nome}')
            else:
                self.stdout.write(f'⏭️  {ncm_cod} - já existe')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 {contador} NCMs importados!'))