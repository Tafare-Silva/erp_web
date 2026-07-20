"""Importa tabelas fiscais completas: NCM (capítulos), CFOP, Estados e Cidades."""
import json
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from apps.cadastros.models import NCM, CFOP, Cidade, Estado


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
MUNICIPIOS_FILE = os.path.join(DATA_DIR, 'municipios_ibge.json')


ESTADOS = [
    ('RO', 'Rondônia', 11),
    ('AC', 'Acre', 12),
    ('AM', 'Amazonas', 13),
    ('RR', 'Roraima', 14),
    ('PA', 'Pará', 15),
    ('AP', 'Amapá', 16),
    ('TO', 'Tocantins', 17),
    ('MA', 'Maranhão', 21),
    ('PI', 'Piauí', 22),
    ('CE', 'Ceará', 23),
    ('RN', 'Rio Grande do Norte', 24),
    ('PB', 'Paraíba', 25),
    ('PE', 'Pernambuco', 26),
    ('AL', 'Alagoas', 27),
    ('SE', 'Sergipe', 28),
    ('BA', 'Bahia', 29),
    ('MG', 'Minas Gerais', 31),
    ('ES', 'Espírito Santo', 32),
    ('RJ', 'Rio de Janeiro', 33),
    ('SP', 'São Paulo', 35),
    ('PR', 'Paraná', 41),
    ('SC', 'Santa Catarina', 42),
    ('RS', 'Rio Grande do Sul', 43),
    ('MS', 'Mato Grosso do Sul', 50),
    ('MT', 'Mato Grosso', 51),
    ('GO', 'Goiás', 52),
    ('DF', 'Distrito Federal', 53),
]


NCMS = [
    ('01', 'Animais vivos', 'Animais vivos'),
    ('02', 'Carnes e miudezas', 'Carnes e miudezas, comestíveis'),
    ('03', 'Peixes e crustáceos', 'Peixes e crustáceos, moluscos e outros invertebrados aquáticos'),
    ('04', 'Leite e laticínios', 'Leite e laticínios; ovos; mel natural'),
    ('06', 'Plantas vivas', 'Plantas vivas e produtos de floricultura'),
    ('07', 'Hortaliças', 'Hortaliças, plantas, raízes e tubérculos, comestíveis'),
    ('08', 'Frutas e castanhas', 'Frutas e castanhas comestíveis; cascas de citrinos'),
    ('09', 'Café e chá', 'Café, chá, mate e especiarias'),
    ('10', 'Cereais', 'Cereais'),
    ('11', 'Farinharia', 'Produtos da indústria de moagem; malte; amidos e féculas'),
    ('12', 'Sementes e oleaginosas', 'Sementes e frutos oleaginosos; grãos, sementes e frutos diversos'),
    ('15', 'Gorduras e óleos', 'Gorduras e óleos animais ou vegetais'),
    ('16', 'Preparações de carne', 'Preparações de carne, peixes ou crustáceos'),
    ('17', 'Açúcares', 'Açúcares e produtos de confeitaria'),
    ('18', 'Cacau', 'Cacau e suas preparações'),
    ('19', 'Preparações de cereais', 'Preparações à base de cereais, farinha, amido'),
    ('20', 'Preparações de hortaliças', 'Preparações de hortaliças, frutas e outras partes de plantas'),
    ('21', 'Preparações alimentícias', 'Preparações alimentícias diversas'),
    ('22', 'Bebidas', 'Bebidas, líquidos alcoólicos e vinagres'),
    ('23', 'Resíduos alimentares', 'Resíduos e desperdícios das indústrias alimentares'),
    ('24', 'Tabaco', 'Tabaco e seus sucedâneos'),
    ('25', 'Sal e enxofre', 'Sal; enxofre; terras e pedras; gesso, cal e cimento'),
    ('27', 'Combustíveis', 'Combustíveis minerais, óleos minerais e produtos de sua destilação'),
    ('28', 'Produtos químicos inorgânicos', 'Produtos químicos inorgânicos; compostos inorgânicos ou orgânicos'),
    ('29', 'Produtos químicos orgânicos', 'Produtos químicos orgânicos'),
    ('30', 'Produtos farmacêuticos', 'Produtos farmacêuticos'),
    ('31', 'Adubos e fertilizantes', 'Adubos ou fertilizantes'),
    ('32', 'Extratos tanantes', 'Extratos tanantes e tintoriais; taninos e seus derivados'),
    ('33', 'Óleos essenciais', 'Óleos essenciais e resinoides; produtos de perfumaria'),
    ('34', 'Sabões', 'Sabões, agentes orgânicos de superfície, preparações para lavagem'),
    ('35', 'Matérias albuminoideas', 'Matérias albuminoideas; colas; enzimas'),
    ('36', 'Pólvoras e explosivos', 'Pólvoras e explosivos; artigos de pirotecnia'),
    ('37', 'Produtos fotográficos', 'Produtos fotográficos ou cinematográficos'),
    ('38', 'Produtos químicos diversos', 'Produtos químicos diversos'),
    ('39', 'Plásticos', 'Plásticos e suas obras'),
    ('40', 'Borracha', 'Borracha e suas obras'),
    ('41', 'Peles e couros', 'Peles e couros'),
    ('42', 'Obras de couro', 'Obras de couro; artigos de correeiro ou seleiro'),
    ('43', 'Peles com pelo', 'Peles com pelo, artificiais'),
    ('44', 'Madeira', 'Madeira e suas obras; carvão vegetal'),
    ('45', 'Cortiça', 'Cortiça e suas obras'),
    ('46', 'Palha', 'Obras de palha, espartaria ou de outras matérias trançadas'),
    ('47', 'Pastas de madeira', 'Pastas de madeira ou de outras matérias fibrosas'),
    ('48', 'Papel e cartão', 'Papel e cartão; obras de pasta de celulose'),
    ('49', 'Livros e jornais', 'Livros, jornais, gravuras e outros produtos indústrias gráficas'),
    ('50', 'Seda', 'Seda'),
    ('51', 'Lã', 'Lã, pelos finos ou grosseiros; fios de crina'),
    ('52', 'Algodão', 'Algodão'),
    ('53', 'Outras fibras têxteis', 'Outras fibras têxteis vegetais'),
    ('54', 'Filamentos sintéticos', 'Filamentos sintéticos ou artificiais'),
    ('55', 'Fibras sintéticas', 'Fibras sintéticas ou artificiais descontínuas'),
    ('56', 'Pastas e feltros', 'Pastas, feltros e falsos tecidos'),
    ('57', 'Tapetes', 'Tapetes e outros revestimentos para pavimentos'),
    ('58', 'Tecidos especiais', 'Tecidos especiais; rendas, tapeçarias'),
    ('59', 'Tecidos impregnados', 'Tecidos impregnados, revestidos, recobertos'),
    ('60', 'Tecidos de malha', 'Tecidos de malha'),
    ('61', 'Vestuário em malha', 'Vestuário e seus acessórios, de malha'),
    ('62', 'Vestuário exceto malha', 'Vestuário e seus acessórios, exceto de malha'),
    ('63', 'Outros artefatos têxteis', 'Outros artefatos têxteis confeccionados'),
    ('64', 'Calçados', 'Calçados, polainas e artefatos semelhantes'),
    ('65', 'Chapéus', 'Chapéus e artefatos de uso semelhante'),
    ('66', 'Guarda-chuvas', 'Guarda-chuvas, guarda-sóis, bengalas'),
    ('68', 'Obras de pedra', 'Obras de pedra, gesso, cimento, amianto, mica'),
    ('69', 'Produtos cerâmicos', 'Produtos cerâmicos'),
    ('70', 'Vidro', 'Vidro e suas obras'),
    ('71', 'Pérolas e pedras', 'Pérolas naturais ou cultivadas, pedras preciosas'),
    ('72', 'Ferro fundido', 'Ferro fundido, ferro e aço'),
    ('73', 'Obras de ferro', 'Obras de ferro fundido, ferro e aço'),
    ('74', 'Cobre', 'Cobre e suas obras'),
    ('75', 'Níquel', 'Níquel e suas obras'),
    ('76', 'Alumínio', 'Alumínio e suas obras'),
    ('78', 'Chumbo', 'Chumbo e suas obras'),
    ('79', 'Zinco', 'Zinco e suas obras'),
    ('80', 'Estanho', 'Estanho e suas obras'),
    ('82', 'Ferramentas', 'Ferramentas, artefatos de cutelaria e talheres'),
    ('83', 'Obras diversas de metais', 'Obras diversas de metais comuns'),
    ('84', 'Máquinas e reatores', 'Reatores nucleares, caldeiras, máquinas e instrumentos mecânicos'),
    ('85', 'Máquinas elétricas', 'Máquinas, aparelhos e materiais elétricos'),
    ('86', 'Veículos ferroviários', 'Veículos e material para vias férreas'),
    ('87', 'Veículos terrestres', 'Veículos automóveis, tratores e suas partes'),
    ('88', 'Aeronaves', 'Aeronaves e veículos espaciais'),
    ('89', 'Embarcações', 'Embarcações e estruturas flutuantes'),
    ('90', 'Instrumentos ópticos', 'Instrumentos e aparelhos de óptica, fotografia, cinema'),
    ('91', 'Relojoaria', 'Relojoaria'),
    ('92', 'Instrumentos musicais', 'Instrumentos musicais'),
    ('94', 'Móveis', 'Móveis; mobiliário médico-cirúrgico; colchões'),
    ('95', 'Brinquedos', 'Brinquedos, jogos, artigos para divertimento'),
    ('96', 'Obras diversas', 'Obras diversas'),
    ('97', 'Antiguidades', 'Objetos de arte, de coleção e antiguidades'),
]


CFOPS = [
    ('1000', 'Entradas - Dentro do Estado', 'Entradas de mercadorias dentro do estado'),
    ('1100', 'Compras para industrialização', 'Compra para industrialização ou produção rural'),
    ('1101', 'Compra para industrialização', 'Compra para industrialização'),
    ('1102', 'Compra para comercialização', 'Compra para comercialização'),
    ('1111', 'Compra para industrialização com ST', 'Compra para industrialização sujeita a ST'),
    ('1113', 'Compra para comercialização com ST', 'Compra para comercialização sujeita a ST'),
    ('1201', 'Devolução de venda', 'Devolução de venda de produção do estabelecimento'),
    ('1202', 'Devolução de venda mercadoria', 'Devolução de venda de mercadoria adquirida'),
    ('1400', 'Outras entradas', 'Outras entradas dentro do estado'),
    ('1403', 'Transferência de mercadoria', 'Transferência para industrialização ou comercialização'),
    ('1411', 'Retorno de remessa', 'Retorno de mercadoria do estabelecimento'),
    ('1500', 'Entradas - Fora do Estado', 'Entradas de mercadorias de fora do estado'),
    ('2100', 'Compras do exterior', 'Compras do exterior'),
    ('2200', 'Entradas do exterior', 'Entradas do exterior para o estado'),
    ('3000', 'Saídas - Dentro do Estado', 'Saídas de mercadorias dentro do estado'),
    ('3100', 'Vendas dentro do estado', 'Vendas dentro do estado'),
    ('3101', 'Venda de produção', 'Venda de produção do estabelecimento'),
    ('3102', 'Venda de mercadoria', 'Venda de mercadoria adquirida'),
    ('3103', 'Venda de produção com ST', 'Venda de produção sujeita a ST'),
    ('3104', 'Venda de mercadoria com ST', 'Venda de mercadoria sujeita a ST'),
    ('3201', 'Devolução de compra', 'Devolução de compra para industrialização'),
    ('3202', 'Devolução de compra mercadoria', 'Devolução de compra de mercadoria'),
    ('3400', 'Outras saídas dentro do estado', 'Outras saídas dentro do estado'),
    ('3401', 'Remessa para industrialização', 'Remessa para industrialização'),
    ('3403', 'Remessa para comercialização', 'Remessa para comercialização'),
    ('3500', 'Saídas - Fora do Estado', 'Saídas de mercadorias para fora do estado'),
    ('5000', 'Saídas - Fora do Estado', 'Saídas para fora do estado'),
    ('5101', 'Venda interestadual produção', 'Venda de produção para fora do estado'),
    ('5102', 'Venda interestadual mercadoria', 'Venda de mercadoria para fora do estado'),
    ('5103', 'Venda interestadual com ST produção', 'Venda interestadual sujeita a ST (produção)'),
    ('5104', 'Venda interestadual com ST mercadoria', 'Venda interestadual sujeita a ST (mercadoria)'),
    ('5201', 'Devolução compra interestadual', 'Devolução de compra interestadual'),
    ('5401', 'Remessa interestadual', 'Remessa interestadual para industrialização'),
    ('5403', 'Remessa interestadual comercialização', 'Remessa interestadual para comercialização'),
    ('5405', 'Venda interestadual', 'Venda interestadual de mercadoria adquirida'),
    ('5901', 'Remessa interestadual', 'Remessa interestadual'),
    ('6000', 'Serviços', 'Prestação de serviços'),
    ('6100', 'Serviços dentro do estado', 'Prestação de serviços dentro do estado'),
    ('6101', 'Serviço de transporte', 'Prestação de serviço de transporte dentro do estado'),
    ('6102', 'Serviço de comunicação', 'Serviço de comunicação dentro do estado'),
    ('6200', 'Serviços fora do estado', 'Prestação de serviços fora do estado'),
    ('6201', 'Serviço de transporte fora', 'Serviço de transporte para fora do estado'),
    ('7000', 'Exportação', 'Operações de exportação'),
    ('7101', 'Exportação direta', 'Venda de produção ao exterior'),
    ('7102', 'Exportação indireta', 'Venda de mercadoria para empresa com fim específico de exportação'),
    ('9000', 'Outras operações', 'Outras operações'),
    ('9201', 'Devolução de venda', 'Devolução de venda interestadual'),
    ('9202', 'Devolução de venda mercadoria interest.', 'Devolução de venda interestadual de mercadoria'),
    ('9401', 'Remessa', 'Remessa para industrialização'),
    ('9403', 'Remessa', 'Remessa para comercialização'),
    ('9405', 'Remessa', 'Remessa de mercadoria'),
    ('9901', 'Outras saídas', 'Outras saídas'),
    ('9902', 'Outras entradas', 'Outras entradas'),
]


class Command(BaseCommand):
    help = 'Importa tabelas fiscais (NCM capítulos, CFOPs e Cidades)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cidades',
            action='store_true',
            help='Pula a importação de cidades (mais rápido)',
        )

    def handle(self, *args, **options):
        self._seed_estados()
        self._seed_ncm()
        self._seed_cfop()
        if not options['skip_cidades']:
            self._seed_cidades()
        self.stdout.write(self.style.SUCCESS('Tabelas fiscais importadas com sucesso!'))

    def _seed_ncm(self):
        for ncm, nome, desc in NCMS:
            NCM.objects.get_or_create(
                ncm=ncm,
                defaults={'nome': nome, 'descricao': desc}
            )
        self.stdout.write(f'  OK {len(NCMS)} NCMs (capítulos) criados')

    def _seed_estados(self):
        for uf, nome, codigo_ibge in ESTADOS:
            Estado.objects.get_or_create(
                uf=uf,
                defaults={'nome': nome, 'codigo_ibge': codigo_ibge}
            )
        self.stdout.write(f'  OK {len(ESTADOS)} estados criados')

    def _seed_cidades(self):
        if not os.path.exists(MUNICIPIOS_FILE):
            self.stdout.write(self.style.WARNING(
                f'Arquivo {MUNICIPIOS_FILE} não encontrado. Pulando cidades.'
            ))
            return
        with open(MUNICIPIOS_FILE, 'r', encoding='utf-8') as f:
            municipios = json.load(f)
        criadas = 0
        for mun in municipios:
            estado = Estado.objects.filter(uf=mun['uf']).first()
            if not estado:
                continue
            _, created = Cidade.objects.get_or_create(
                codigo_ibge=mun['codigo_ibge'],
                defaults={'nome': mun['nome'], 'estado': estado}
            )
            if created:
                criadas += 1
        self.stdout.write(f'  OK {criadas}/{len(municipios)} cidades criadas')

    def _seed_cfop(self):
        for cfop, nome, desc in CFOPS:
            CFOP.objects.get_or_create(
                cfop=cfop,
                defaults={'nome': nome, 'descricao': desc}
            )
        self.stdout.write(f'  OK {len(CFOPS)} CFOPs criados')
