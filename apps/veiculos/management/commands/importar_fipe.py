from django.core.management.base import BaseCommand

from apps.veiculos.models import MarcaVeiculo, ModeloVeiculo
from apps.veiculos.services import FipeClient


class Command(BaseCommand):
    help = 'Importa marcas (e opcionalmente modelos) de veículos da tabela FIPE.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--modelos', type=int, default=0,
            help='Importar também os modelos das primeiras N marcas (0 = só marcas).',
        )
        parser.add_argument(
            '--marca', type=str, default='',
            help='Importar modelos de uma marca específica (nome parcial).',
        )

    def handle(self, *args, **options):
        client = FipeClient()
        self.stdout.write('Buscando marcas na FIPE...')
        try:
            marcas_api = client.listar_marcas()
        except Exception as e:
            self.stderr.write(f'Erro ao buscar marcas: {e}')
            return

        criadas = 0
        for m in marcas_api:
            _, created = MarcaVeiculo.objects.get_or_create(nome=m['nome'].strip())
            if created:
                criadas += 1
        self.stdout.write(self.style.SUCCESS(f'Marcas: {criadas} novas de {len(marcas_api)} na API.'))

        alvo_modelos = options['modelos']
        marca_filtro = options['marca']
        if not alvo_modelos and not marca_filtro:
            self.stdout.write('Para importar modelos use --modelos N ou --marca "Nome".')
            return

        alvo = marca_filtro or alvo_modelos
        for m in marcas_api:
            nome = m['nome'].strip()
            if marca_filtro and marca_filtro.lower() not in nome.lower():
                continue
            db_marca = MarcaVeiculo.objects.filter(nome=nome).first()
            if not db_marca:
                continue
            self.stdout.write(f'Buscando modelos de {nome}...')
            try:
                modelos = client.listar_modelos(m['codigo'])
            except Exception as e:
                self.stderr.write(f'  Erro em {nome}: {e}')
                continue
            mcriados = 0
            for mod in modelos.get('modelos', []):
                nome_mod = mod['nome'].strip()
                _, created = ModeloVeiculo.objects.get_or_create(
                    marca=db_marca, nome=nome_mod, ano_modelo=None
                )
                if created:
                    mcriados += 1
            self.stdout.write(f'  {mcriados} novos modelos.')
            if not marca_filtro:
                alvo -= 1
                if alvo <= 0:
                    break