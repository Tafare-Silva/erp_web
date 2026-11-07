"""Importa/seeds as tabelas fiscais de referência.

Fontes:
- Estados: IBGE
- Cidades: IBGE (municipios_ibge.json)
- NCM: tabelasfiscais.com.br (dados públicos da Receita Federal/Siscomex)
- CFOP: tabelasfiscais.com.br (CONFAZ)
- CST: tabelas oficiais de ICMS, PIS, COFINS e IPI

Os arquivos ficam em apps/cadastros/management/data/ e podem ser atualizados
substituindo-os. O comando é idempotente.
"""
import csv
import json
import os

from django.core.management.base import BaseCommand
from apps.cadastros.models import NCM, CFOP, CST, Cidade, Estado


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
MUNICIPIOS_FILE = os.path.join(DATA_DIR, 'municipios_ibge.json')
NCM_FILE = os.path.join(DATA_DIR, 'ncm.csv')
CFOP_FILE = os.path.join(DATA_DIR, 'cfop.csv')


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


CSTS = [
    # ICMS - CST
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
    # ICMS - CSOSN (Simples Nacional)
    ('101', 'ICMS', 'CSOSN 101 - Tributada pelo Simples Nacional com permissão de crédito'),
    ('102', 'ICMS', 'CSOSN 102 - Tributada pelo Simples Nacional sem permissão de crédito'),
    ('103', 'ICMS', 'CSOSN 103 - Isenção do ICMS no Simples Nacional para faixa de receita bruta'),
    ('201', 'ICMS', 'CSOSN 201 - Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por ST'),
    ('202', 'ICMS', 'CSOSN 202 - Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por ST'),
    ('203', 'ICMS', 'CSOSN 203 - Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por ST'),
    ('300', 'ICMS', 'CSOSN 300 - Imune'),
    ('400', 'ICMS', 'CSOSN 400 - Não tributada pelo Simples Nacional'),
    ('500', 'ICMS', 'CSOSN 500 - ICMS cobrado anteriormente por substituição tributária ou por antecipação'),
    ('900', 'ICMS', 'CSOSN 900 - Outros'),
    # PIS / COFINS (saída)
    ('01', 'PIS', 'Operação tributável com alíquota básica'),
    ('02', 'PIS', 'Operação tributável com alíquota diferenciada'),
    ('03', 'PIS', 'Operação tributável com alíquota por unidade de medida de produto'),
    ('04', 'PIS', 'Operação tributável monofásica - revenda a alíquota zero'),
    ('05', 'PIS', 'Operação tributável por substituição tributária'),
    ('06', 'PIS', 'Operação tributável a alíquota zero'),
    ('07', 'PIS', 'Operação isenta da contribuição'),
    ('08', 'PIS', 'Operação sem incidência da contribuição'),
    ('09', 'PIS', 'Operação com suspensão da contribuição'),
    ('49', 'PIS', 'Outras operações de saída'),
    ('99', 'PIS', 'Outras operações'),
    ('01', 'COFINS', 'Operação tributável com alíquota básica'),
    ('02', 'COFINS', 'Operação tributável com alíquota diferenciada'),
    ('03', 'COFINS', 'Operação tributável com alíquota por unidade de medida de produto'),
    ('04', 'COFINS', 'Operação tributável monofásica - revenda a alíquota zero'),
    ('05', 'COFINS', 'Operação tributável por substituição tributária'),
    ('06', 'COFINS', 'Operação tributável a alíquota zero'),
    ('07', 'COFINS', 'Operação isenta da contribuição'),
    ('08', 'COFINS', 'Operação sem incidência da contribuição'),
    ('09', 'COFINS', 'Operação com suspensão da contribuição'),
    ('49', 'COFINS', 'Outras operações de saída'),
    ('99', 'COFINS', 'Outras operações'),
    # IPI
    ('00', 'IPI', 'Entrada com recuperação de crédito'),
    ('01', 'IPI', 'Entrada tributada com alíquota zero'),
    ('02', 'IPI', 'Entrada isenta'),
    ('03', 'IPI', 'Entrada não tributada'),
    ('04', 'IPI', 'Entrada imune'),
    ('05', 'IPI', 'Entrada com suspensão'),
    ('49', 'IPI', 'Outras entradas'),
    ('50', 'IPI', 'Saída tributada'),
    ('51', 'IPI', 'Saída tributada com alíquota zero'),
    ('52', 'IPI', 'Saída isenta'),
    ('53', 'IPI', 'Saída não tributada'),
    ('54', 'IPI', 'Saída imune'),
    ('55', 'IPI', 'Saída com suspensão'),
    ('99', 'IPI', 'Outras saídas'),
]


class Command(BaseCommand):
    help = 'Importa tabelas fiscais (NCM capítulos, CFOPs e Cidades)'

    def add_arguments(self, parser):
        parser.add_argument('--skip-cidades', action='store_true', help='Pula a importação de cidades')
        parser.add_argument('--skip-ncm', action='store_true', help='Pula a importação de NCM')
        parser.add_argument('--skip-cfop', action='store_true', help='Pula a importação de CFOP')
        parser.add_argument('--skip-cst', action='store_true', help='Pula a importação de CST (PIS/COFINS/IPI/ICMS)')

    def handle(self, *args, **options):
        self._seed_estados()
        if not options['skip_cst']:
            self._seed_cst()
        if not options['skip_cfop']:
            self._seed_cfop()
        if not options['skip_ncm']:
            self._seed_ncm()
        if not options['skip_cidades']:
            self._seed_cidades()
        self.stdout.write(self.style.SUCCESS('Tabelas fiscais importadas/atualizadas com sucesso!'))

    def _seed_estados(self):
        for uf, nome, codigo_ibge in ESTADOS:
            Estado.objects.update_or_create(
                uf=uf,
                defaults={'nome': nome, 'codigo_ibge': codigo_ibge}
            )
        self.stdout.write(f'  OK estados: {Estado.objects.count()} na base')

    def _seed_cst(self):
        for cst, tipo, descricao in CSTS:
            CST.objects.update_or_create(
                cst=cst, tipo_imposto=tipo,
                defaults={'descricao': descricao}
            )
        self.stdout.write(f'  OK CSTs: {CST.objects.count()} na base')

    def _seed_cfop(self):
        if os.path.exists(CFOP_FILE):
            criados = 0
            with open(CFOP_FILE, 'r', encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f, delimiter=';'):
                    codigo = (row.get('cfop') or '').replace('.', '').strip()
                    if not (codigo.isdigit() and len(codigo) == 4):
                        continue
                    descricao = (row.get('descricao') or '').strip() or codigo
                    _, created = CFOP.objects.update_or_create(
                        cfop=codigo,
                        defaults={
                            'nome': descricao[:255],
                            'descricao': descricao,
                            'aplicacao': (row.get('ambito') or '').strip() or None,
                        }
                    )
                    criados += int(created)
            self.stdout.write(f'  OK CFOPs: {CFOP.objects.count()} na base ({criados} novos)')
            return
        for cfop, nome, desc in CFOPS:
            CFOP.objects.update_or_create(cfop=cfop, defaults={'nome': nome, 'descricao': desc})
        self.stdout.write(f'  OK CFOPs: {CFOP.objects.count()} na base (fallback sem CSV)')

    def _seed_ncm(self):
        if os.path.exists(NCM_FILE):
            vistos = set()
            objs = []
            with open(NCM_FILE, 'r', encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f, delimiter=';'):
                    if str(row.get('vigente', '1')).strip() == '0':
                        continue
                    codigo = (row.get('codigo') or '').replace('.', '').strip()
                    if not (codigo.isdigit() and len(codigo) == 8) or codigo in vistos:
                        continue
                    vistos.add(codigo)
                    descricao = (row.get('descricao') or '').strip() or codigo
                    objs.append(NCM(ncm=codigo, nome=descricao[:255], descricao=descricao))
            NCM.objects.bulk_create(objs, ignore_conflicts=True, batch_size=1000)
            self.stdout.write(f'  OK NCMs: {NCM.objects.count()} na base ({len(objs)} lidos)')
            return
        for ncm, nome, desc in NCMS:
            NCM.objects.update_or_create(ncm=ncm, defaults={'nome': nome, 'descricao': desc})
        self.stdout.write(f'  OK NCMs: {NCM.objects.count()} na base (fallback sem CSV)')

    def _seed_cidades(self):
        if not os.path.exists(MUNICIPIOS_FILE):
            self.stdout.write(self.style.WARNING(
                f'Arquivo {MUNICIPIOS_FILE} não encontrado. Pulando cidades.'
            ))
            return
        with open(MUNICIPIOS_FILE, 'r', encoding='utf-8') as f:
            municipios = json.load(f)
        estados = {e.uf: e for e in Estado.objects.all()}
        existentes = set(Cidade.objects.values_list('codigo_ibge', flat=True))
        objs = []
        for mun in municipios:
            codigo = int(mun['codigo_ibge'])
            if codigo in existentes:
                continue
            estado = estados.get(mun.get('uf'))
            if not estado:
                continue
            objs.append(Cidade(codigo_ibge=codigo, nome=mun['nome'], estado=estado))
        Cidade.objects.bulk_create(objs, ignore_conflicts=True, batch_size=1000)
        self.stdout.write(f'  OK cidades: {Cidade.objects.count()} na base ({len(objs)} novas)')
