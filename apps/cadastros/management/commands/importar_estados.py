from django.core.management.base import BaseCommand
from apps.cadastros.models import Estado


class Command(BaseCommand):
    help = 'Importa todos os estados brasileiros com código IBGE'

    def handle(self, *args, **options):
        estados = [
            ('AC', 'Acre', 12),
            ('AL', 'Alagoas', 27),
            ('AP', 'Amapá', 16),
            ('AM', 'Amazonas', 13),
            ('BA', 'Bahia', 29),
            ('CE', 'Ceará', 23),
            ('DF', 'Distrito Federal', 53),
            ('ES', 'Espírito Santo', 32),
            ('GO', 'Goiás', 52),
            ('MA', 'Maranhão', 21),
            ('MT', 'Mato Grosso', 51),
            ('MS', 'Mato Grosso do Sul', 50),
            ('MG', 'Minas Gerais', 31),
            ('PA', 'Pará', 15),
            ('PB', 'Paraíba', 25),
            ('PR', 'Paraná', 41),
            ('PE', 'Pernambuco', 26),
            ('PI', 'Piauí', 22),
            ('RJ', 'Rio de Janeiro', 33),
            ('RN', 'Rio Grande do Norte', 24),
            ('RS', 'Rio Grande do Sul', 43),
            ('RO', 'Rondônia', 11),
            ('RR', 'Roraima', 14),
            ('SC', 'Santa Catarina', 42),
            ('SP', 'São Paulo', 35),
            ('SE', 'Sergipe', 28),
            ('TO', 'Tocantins', 17),
        ]

        contador = 0
        for uf, nome, codigo_ibge in estados:
            estado, created = Estado.objects.get_or_create(
                uf=uf,
                defaults={
                    'nome': nome,
                    'codigo_ibge': codigo_ibge
                }
            )
            if created:
                contador += 1
                self.stdout.write(f'✅ {uf} - {nome} (IBGE: {codigo_ibge})')
            else:
                self.stdout.write(f'⏭️  {uf} - {nome} já existe')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 {contador} estados importados!'))