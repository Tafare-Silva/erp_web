"""
DANFE – Documento Auxiliar da NF-e (modelo SEFAZ padrão)
Gerado com ReportLab; fiel ao layout do modelo oficial.
"""

import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdfcanvas

import os, reportlab

# ── Fontes ──────────────────────────────────────────────────────────────────
RL_DIR  = os.path.dirname(reportlab.__file__)
FONT_DIR = os.path.join(RL_DIR, 'fonts')
for name, fname in [('Vera', 'Vera.ttf'), ('VeraBd', 'VeraBd.ttf'),
                    ('VeraIt', 'VeraIt.ttf')]:
    path = os.path.join(FONT_DIR, fname)
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont(name, path))
addMapping('Vera', 0, 0, 'Vera')
addMapping('Vera', 1, 0, 'VeraBd')
addMapping('Vera', 0, 1, 'VeraIt')

# ── Constantes de layout ─────────────────────────────────────────────────────
PW, PH   = A4                      # 595.27 x 841.89 pt
MARG     = 5 * mm
LARG     = PW - 2 * MARG           # largura útil

FONT     = 'Vera'
FB       = 'VeraBd'
FS_TIT   = 6.5                     # rótulo de campo (maiúsculo)
FS_VAL   = 7.5                     # valor do campo
FS_SEC   = 6.5                     # título de seção
FS_PROD  = 6.0                     # linhas da tabela de produtos
LPAD     = 2

CINZA    = HexColor('#f0f0f0')
CINZA2   = HexColor('#e0e0e0')
BORDA    = HexColor('#888888')
AZUL     = HexColor('#1a3a6e')


# ── Helpers de texto ─────────────────────────────────────────────────────────
def _ps(size, bold=False, align='LEFT', color=black, leading=None):
    return ParagraphStyle(
        'x',
        fontName=FB if bold else FONT,
        fontSize=size,
        leading=leading or size * 1.3,
        textColor=color,
        spaceAfter=0, spaceBefore=0,
        alignment={'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}.get(align.upper(), 0),
    )


def _p(text, size=FS_VAL, bold=False, align='LEFT', color=black):
    return Paragraph(str(text), _ps(size, bold, align, color))


def _label(text):
    """Rótulo de campo em maiúsculo cinza escuro."""
    return _p(text.upper(), FS_TIT if 'FS_TIT' in dir() else FS_TIT, False, 'LEFT',
               HexColor('#444444'))


def _campo(rotulo, valor, size_v=FS_VAL, bold_v=False, align_v='LEFT'):
    """Célula dupla: rótulo pequeno acima + valor abaixo."""
    return Paragraph(
        f'<font size="{FS_TIT}" color="#555555">{rotulo.upper()}</font><br/>'
        f'<font size="{size_v}"{"" if not bold_v else " face=\"VeraBd\""}'
        f'>{valor}</font>',
        _ps(size_v, False, align_v),
    )


# variável global para FS_TIT (evitar redefinição)
FS_TIT = 5.8


# ── Helpers de formatação ────────────────────────────────────────────────────
def _fmt(v, dec=2):
    if v is None:
        return '0,' + '0' * dec
    try:
        d = Decimal(str(v))
        fmt = f'{{:,.{dec}f}}'.format(d)
        return fmt.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (InvalidOperation, TypeError):
        return '0,' + '0' * dec


def _fmt_q(v):
    return _fmt(v, 4)


def _d(dt, f='%d/%m/%Y'):
    if not dt:
        return ''
    if isinstance(dt, (datetime,)):
        return dt.strftime(f)
    return str(dt)


def _end(p):
    """Retorna (logradouro, numero, complemento, bairro, cidade, uf, cep)."""
    if p is None:
        return ('', '', '', '', '', '', '')
    try:
        e = p.endereco_principal_rel.endereco
    except Exception:
        try:
            e = p.enderecos.first()
        except Exception:
            e = None
    if not e:
        return ('', '', '', '', '', '', '')
    try:
        c = e.cidade
        return (e.logradouro or '', e.numero or '', e.complemento or '',
                e.bairro or '', c.nome or '', c.estado.uf or '', e.cep or '')
    except Exception:
        return ('', '', '', '', '', '', '')


def _ie(p):
    if p is None:
        return 'ISENTO'
    return getattr(p, 'rg_ie', None) or 'ISENTO'


def _tel(p):
    if p is None:
        return ''
    return (getattr(p, 'telefone_fixo', None) or
            getattr(p, 'celular_principal', None) or '')


def _chave_fmt(ch):
    """Formata chave de acesso em grupos de 4."""
    ch = (ch or '').replace(' ', '')
    return ' '.join(ch[i:i+4] for i in range(0, len(ch), 4))


def _desc_pag(tp):
    mapa = {
        '01': 'Dinheiro', '02': 'Cheque', '03': 'Cartão de Crédito',
        '04': 'Cartão de Débito', '05': 'Crédito Loja', '10': 'Vale Alimentação',
        '11': 'Vale Refeição', '12': 'Vale Presente', '13': 'Vale Combustível',
        '14': 'Duplicata Mercantil', '15': 'Boleto Bancário',
        '16': 'Depósito Bancário', '17': 'PIX', '18': 'Transferência',
        '19': 'Fidelidade', '90': 'Sem Pagamento', '99': 'Outros',
    }
    return mapa.get(str(tp).zfill(2), str(tp))


# ── Construtor de tabela genérico ────────────────────────────────────────────
def _tbl(rows, col_widths, extra_styles=None):
    """
    col_widths: lista de floats (fração de LARG) ou valores absolutos em pt.
    """
    cw = [LARG * w if isinstance(w, float) else w for w in col_widths]
    t = Table(rows, colWidths=cw, repeatRows=1)
    base = [
        ('VALIGN',    (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING',   (0, 0), (-1, -1), LPAD),
        ('RIGHTPADDING',  (0, 0), (-1, -1), LPAD),
    ]
    if extra_styles:
        base.extend(extra_styles)
    t.setStyle(TableStyle(base))
    return t


# ── Barcode ──────────────────────────────────────────────────────────────────
def _barcode_drawing(chave, largura, altura=12 * mm):
    """Retorna um Drawing com o code-128 da chave de acesso."""
    bc = code128.Code128(
        chave,
        barWidth=largura / (len(chave) * 11 + 35),
        barHeight=altura,
        humanReadable=False,
        quiet=False,
    )
    d = Drawing(largura, altura)
    d.add(bc)
    return d


# ════════════════════════════════════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════
def gerar_danfe(nfe) -> bytes:
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=5 * mm, bottomMargin=5 * mm,
        leftMargin=MARG, rightMargin=MARG,
    )

    emit  = nfe.empresa.pessoa
    dest  = nfe.destinatario
    itens = list(nfe.itens.all().order_by('numero_item'))
    ch    = nfe.chave_acesso or ''
    ch_f  = _chave_fmt(ch)
    prot  = nfe.protocolo or ''

    el, en, ec, eb, ecid, euf, ecep = _end(emit)
    dl, dn, dc, db, dcid, duf, dcep = _end(dest)

    dp  = _d(nfe.data_emissao)
    dsa = _d(nfe.data_saida or nfe.data_emissao)
    hs  = _d(nfe.data_emissao, '%H:%M:%S')

    transp   = nfe.transportadora
    mod_opts = dict(nfe._meta.get_field('modalidade_frete').choices)
    mod_txt  = mod_opts.get(nfe.modalidade_frete, '9 - Sem Frete')

    elts = []

    # ────────────────────────────────────────────────────────────────────────
    # 1. FAIXA DE RECEBIMENTO (topo)
    # ────────────────────────────────────────────────────────────────────────
    receb_txt = (
        f'RECEBEMOS DE {emit.nome.upper()} OS PRODUTOS / SERVIÇOS '
        f'CONSTANTES DA NOTA FISCAL INDICADO AO LADO'
    )
    nf_ref = (
        f'<b>NF-e</b><br/>'
        f'N° <b>{str(nfe.numero).zfill(9)}</b><br/>'
        f'SÉRIE {str(nfe.serie).zfill(3)}'
    )
    r_receb = [[
        _p(receb_txt, FS_TIT),
        _p('RESUMO', FS_TIT, align='CENTER'),
        _p(nf_ref, FS_VAL, align='RIGHT'),
    ]]
    elts.append(_tbl(r_receb, [0.55, 0.12, 0.33], [
        ('BOX',   (0, 0), (-1, -1), 0.5, BORDA),
        ('LINEAFTER', (0, 0), (0, 0), 0.5, BORDA),
        ('LINEAFTER', (1, 0), (1, 0), 0.5, BORDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    # Linha assinatura
    r_ass = [[
        _p('DATA DE RECEBIMENTO', FS_TIT),
        _p('IDENTIFICAÇÃO E ASSINATURA DO RECEBEDOR', FS_TIT),
    ]]
    elts.append(_tbl(r_ass, [0.22, 0.78], [
        ('BOX',      (0, 0), (-1, -1), 0.5, BORDA),
        ('LINEAFTER',(0, 0), (0, 0),   0.5, BORDA),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 2. BLOCO CENTRAL: emitente | DANFE | barcode
    # ────────────────────────────────────────────────────────────────────────
    end_emit = (
        f'{el}, {en}'
        + (f' – {ec}' if ec else '')
        + f' – {eb} – {ecid}/{euf} – CEP: {ecep}'
    )
    col_emit = [
        _p('<b>IDENTIFICAÇÃO DO EMITENTE</b>', FS_TIT, color=HexColor('#333333')),
        Spacer(1, 2),
        _p(f'<b>{emit.nome.upper()}</b>', 9, bold=True),
        Spacer(1, 2),
        _p(end_emit, FS_TIT),
        _p(f'TEL: {_tel(emit)}', FS_TIT),
    ]

    danfe_central = [
        _p('<b>DANFE</b>', 16, bold=True, align='CENTER'),
        _p('DOCUMENTO AUXILIAR DA', FS_TIT, align='CENTER'),
        _p('NOTA FISCAL ELETRÔNICA', FS_TIT, align='CENTER'),
        Spacer(1, 3),
        _p('0 - ENTRADA', FS_VAL, align='CENTER'),
        _p('<b><font color="#1a3a6e">1</font></b> - SAÍDA', FS_VAL, align='CENTER'),
        Spacer(1, 3),
        _p(f'N° <b>{str(nfe.numero).zfill(9)}</b>', FS_VAL, bold=False, align='CENTER'),
        _p(f'SÉRIE <b>{str(nfe.serie).zfill(3)}</b>', FS_VAL, align='CENTER'),
        _p(f'fl. 1 / 1', FS_TIT, align='CENTER'),
    ]

    # Barcode + chave
    bc_larg = LARG * 0.35
    try:
        bc_draw  = _barcode_drawing(ch, bc_larg)
        col_bc   = [bc_draw,
                    _p(ch_f, FS_TIT, align='CENTER'),
                    Spacer(1, 3),
                    _p('Consulta de autenticidade no portal nacional da NF-e', FS_TIT, align='CENTER'),
                    _p('www.nfe.fazenda.gov.br/portal', FS_TIT, align='CENTER'),
                    _p('ou no site da Sefaz Autorizadora', FS_TIT, align='CENTER'),
                    ]
    except Exception:
        col_bc   = [_p(ch_f, FS_TIT, align='CENTER'),
                    _p('www.nfe.fazenda.gov.br/portal', FS_TIT, align='CENTER')]

    r_header = [[col_emit, danfe_central, col_bc]]
    elts.append(_tbl(r_header, [0.40, 0.24, 0.36], [
        ('BOX',      (0, 0), (-1, -1), 0.5, BORDA),
        ('LINEAFTER',(0, 0), (0, 0),   0.5, BORDA),
        ('LINEAFTER',(1, 0), (1, 0),   0.5, BORDA),
        ('VALIGN',   (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',    (1, 0), (1, 0),   'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 3. NATUREZA / PROTOCOLO / IE / CNPJ
    # ────────────────────────────────────────────────────────────────────────
    r_nat = [[
        _campo('NATUREZA DA OPERAÇÃO', nfe.natureza_operacao or '---', FS_VAL),
        _campo('PROTOCOLO DE AUTORIZAÇÃO DE USO', prot, FS_VAL),
    ],[
        _campo('INSCRIÇÃO ESTADUAL', _ie(emit), FS_VAL),
        _campo('INSCRIÇÃO ESTADUAL DO SUBST. TRIB.', '---', FS_VAL),
        _campo('CNPJ / CPF', emit.cpf_cnpj or '---', FS_VAL),
    ]]
    elts.append(_tbl(r_nat, [0.50, 0.50], [
        ('BOX',      (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID',     (0, 0), (-1, -1), 0.3, BORDA),
        ('SPAN',     (0, 0), (0, 0)),
        ('SPAN',     (1, 0), (1, 0)),
        # linha 1: 3 células → precisamos redefinir o span da linha 1
    ]))

    # linha 1 tem 2 cols, linha 2 tem 3 cols – precisamos de tabelas separadas
    # Reconstruindo como 2 tabelas encadeadas:
    elts.pop()  # remove a última

    r_nat1 = [[
        _campo('NATUREZA DA OPERAÇÃO', nfe.natureza_operacao or '---'),
        _campo('PROTOCOLO DE AUTORIZAÇÃO DE USO', prot),
    ]]
    elts.append(_tbl(r_nat1, [0.55, 0.45], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    r_nat2 = [[
        _campo('INSCRIÇÃO ESTADUAL', _ie(emit)),
        _campo('INSCRIÇÃO ESTADUAL DO SUBST. TRIB.', '---'),
        _campo('CNPJ / CPF', emit.cpf_cnpj or '---'),
    ]]
    elts.append(_tbl(r_nat2, [0.30, 0.35, 0.35], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 4. DESTINATÁRIO
    # ────────────────────────────────────────────────────────────────────────
    r_dest_tit = [[_p('<b>DESTINATÁRIO / REMETENTE</b>', FS_SEC, color=white)]]
    elts.append(_tbl(r_dest_tit, [1.0], [
        ('BACKGROUND', (0, 0), (-1, -1), AZUL),
        ('BOX',        (0, 0), (-1, -1), 0.5, BORDA),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    r_dest1 = [[
        _campo('NOME / RAZÃO SOCIAL', dest.nome or '---', FS_VAL),
        _campo('CNPJ / CPF', dest.cpf_cnpj or '---', FS_VAL),
        _campo('DATA DA EMISSÃO', dp, FS_VAL, align_v='CENTER'),
    ]]
    elts.append(_tbl(r_dest1, [0.50, 0.25, 0.25], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    r_dest2 = [[
        _campo('ENDEREÇO', f'{dl}, {dn}' + (f' – {dc}' if dc else ''), FS_VAL),
        _campo('BAIRRO / DISTRITO', db, FS_VAL),
        _campo('CEP', dcep, FS_VAL),
        _campo('DATA SAÍDA / ENTRADA', dsa, FS_VAL, align_v='CENTER'),
        _campo('HORA DA SAÍDA', hs, FS_VAL, align_v='CENTER'),
    ]]
    elts.append(_tbl(r_dest2, [0.34, 0.18, 0.14, 0.18, 0.16], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    r_dest3 = [[
        _campo('MUNICÍPIO', dcid, FS_VAL),
        _campo('FONE / FAX', _tel(dest), FS_VAL),
        _campo('UF', duf, FS_VAL, align_v='CENTER'),
        _campo('INSCRIÇÃO ESTADUAL', _ie(dest), FS_VAL),
    ]]
    elts.append(_tbl(r_dest3, [0.40, 0.25, 0.10, 0.25], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 5. CÁLCULO DO IMPOSTO
    # ────────────────────────────────────────────────────────────────────────
    r_imp_tit = [[_p('<b>CÁLCULO DO IMPOSTO</b>', FS_SEC, color=white)]]
    elts.append(_tbl(r_imp_tit, [1.0], [
        ('BACKGROUND', (0, 0), (-1, -1), AZUL),
        ('BOX',        (0, 0), (-1, -1), 0.5, BORDA),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    def _ci(rot, val, bold=False, align='RIGHT'):
        return _campo(rot, val, FS_VAL, bold_v=bold, align_v=align)

    r_imp1 = [[
        _ci('BASE DE CÁLCULO DO ICMS',    _fmt(nfe.valor_base_calculo_icms)),
        _ci('VALOR DO ICMS',              _fmt(nfe.valor_icms)),
        _ci('BASE CÁLC. ICMS SUBST.',     _fmt(nfe.valor_base_calculo_icms_st)),
        _ci('VALOR DO ICMS SUBST.',       _fmt(nfe.valor_icms_st)),
        _ci('VALOR TOTAL DOS PRODUTOS',   _fmt(nfe.valor_total_produtos), bold=True),
    ]]
    elts.append(_tbl(r_imp1, [0.20, 0.20, 0.20, 0.20, 0.20], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    r_imp2 = [[
        _ci('VALOR DO FRETE',     _fmt(nfe.valor_frete)),
        _ci('VALOR DO SEGURO',    _fmt(nfe.valor_seguro)),
        _ci('DESCONTO',           _fmt(nfe.valor_desconto)),
        _ci('OUTRAS DESP. ACESS.',_fmt(nfe.valor_outras_despesas)),
        _ci('VALOR DO IPI',       _fmt(nfe.valor_ipi)),
        _ci('VALOR TOTAL DA NOTA',_fmt(nfe.valor_total), bold=True),
    ]]
    elts.append(_tbl(r_imp2, [0.17, 0.17, 0.17, 0.17, 0.15, 0.17], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
        ('BACKGROUND', (5, 0), (5, 0), CINZA2),
        ('LINEAFTER', (4, 0), (4, 0), 1.0, black),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 6. TRANSPORTADOR
    # ────────────────────────────────────────────────────────────────────────
    r_tr_tit = [[_p('<b>TRANSPORTADOR / VOLUMES TRANSPORTADOS</b>', FS_SEC, color=white)]]
    elts.append(_tbl(r_tr_tit, [1.0], [
        ('BACKGROUND', (0, 0), (-1, -1), AZUL),
        ('BOX',        (0, 0), (-1, -1), 0.5, BORDA),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    tl, tn, tc, tb, tcid, tuf, tcep = _end(transp)
    r_tr1 = [[
        _campo('RAZÃO SOCIAL',    transp.nome if transp else '---'),
        _campo('FRETE POR CONTA', mod_txt),
        _campo('CÓDIGO ANTT',     getattr(nfe, 'codigo_antt', '') or '---'),
        _campo('PLACA DO VEÍCULO',getattr(nfe, 'placa_veiculo', '') or '---'),
        _campo('UF',              getattr(nfe, 'uf_veiculo', '') or '---', align_v='CENTER'),
        _campo('CNPJ / CPF',      transp.cpf_cnpj if transp else '---'),
    ]]
    elts.append(_tbl(r_tr1, [0.25, 0.20, 0.13, 0.14, 0.06, 0.22], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    r_tr2 = [[
        _campo('ENDEREÇO',          f'{tl}, {tn}' if tl else '---'),
        _campo('MUNICÍPIO',         tcid),
        _campo('UF',                tuf, align_v='CENTER'),
        _campo('INSCRIÇÃO ESTADUAL',_ie(transp) if transp else '---'),
        _campo('QUANTIDADE',        str(getattr(nfe, 'volumes', '') or '---'), align_v='CENTER'),
        _campo('ESPÉCIE',           getattr(nfe, 'especie', '') or '---'),
        _campo('PESO BRUTO',        _fmt_q(getattr(nfe, 'peso_bruto', None)), align_v='RIGHT'),
        _campo('PESO LÍQUIDO',      _fmt_q(getattr(nfe, 'peso_liquido', None)), align_v='RIGHT'),
    ]]
    elts.append(_tbl(r_tr2, [0.22, 0.18, 0.06, 0.18, 0.09, 0.09, 0.09, 0.09], [
        ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 7. TABELA DE PRODUTOS / SERVIÇOS
    # ────────────────────────────────────────────────────────────────────────
    cab_prod = [
        'CÓDIGO\nPROD./SERV.', 'DESCRIÇÃO DO PRODUTO / SERVIÇO',
        'NCM/SH', 'CSOSN', 'CFOP', 'UNID.',
        'QUANT.', 'VALOR\nUNITÁRIO', 'VALOR\nDESCONTO',
        'VALOR\nLÍQUIDO', 'BASE\nCÁLC. ICMS',
        'VALOR\nI.C.M.S.', 'VALOR\nI.P.I.',
        'ALÍQ.\nICMS', 'ALÍQ.\nIPI',
    ]
    cw_prod = [
        0.060, 0.170, 0.058, 0.042, 0.040, 0.038,
        0.055, 0.068, 0.058,
        0.065, 0.060,
        0.060, 0.048,
        0.040, 0.038,
    ]

    def _ph(txt):
        return _p(txt, FS_PROD, bold=True, align='CENTER', color=white)

    rows_prod = [[_ph(h) for h in cab_prod]]

    for idx, it in enumerate(itens):
        csosn = getattr(it, 'csosn', '') or getattr(it, 'cst_icms', '') or ''
        desc  = getattr(it, 'descricao', None) or getattr(it, 'nome', '') or ''
        vdesc = getattr(it, 'valor_desconto', None) or 0
        vliq  = (Decimal(str(it.valor_total or 0)) -
                 Decimal(str(vdesc))).quantize(Decimal('0.01'))
        vbc   = getattr(it, 'valor_base_icms', None) or 0
        vicms = getattr(it, 'valor_icms', None) or 0
        vipi  = getattr(it, 'valor_ipi', None) or 0
        aliq  = getattr(it, 'aliquota_icms', None) or 0
        aliqi = getattr(it, 'aliquota_ipi', None) or 0

        bg = white if idx % 2 == 0 else CINZA
        row = [
            _p(str(it.codigo_produto or '')[:12], FS_PROD),
            _p(desc[:60], FS_PROD),
            _p(str(it.ncm or ''), FS_PROD, align='CENTER'),
            _p(csosn, FS_PROD, align='CENTER'),
            _p(str(it.cfop or ''), FS_PROD, align='CENTER'),
            _p(str(it.unidade or ''), FS_PROD, align='CENTER'),
            _p(_fmt_q(it.quantidade), FS_PROD, align='RIGHT'),
            _p(_fmt(it.valor_unitario), FS_PROD, align='RIGHT'),
            _p(_fmt(vdesc), FS_PROD, align='RIGHT'),
            _p(_fmt(vliq), FS_PROD, bold=True, align='RIGHT'),
            _p(_fmt(vbc), FS_PROD, align='RIGHT'),
            _p(_fmt(vicms), FS_PROD, align='RIGHT'),
            _p(_fmt(vipi), FS_PROD, align='RIGHT'),
            _p(_fmt(aliq), FS_PROD, align='RIGHT'),
            _p(_fmt(aliqi), FS_PROD, align='RIGHT'),
        ]
        rows_prod.append(row)

    elts.append(_tbl(rows_prod, cw_prod, [
        ('BACKGROUND',   (0, 0), (-1, 0),  AZUL),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  white),
        ('GRID',         (0, 0), (-1, -1), 0.3, BORDA),
        ('BOX',          (0, 0), (-1, -1), 0.5, BORDA),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, CINZA]),
        ('ALIGN',        (0, 0), (-1, 0),  'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 8. PAGAMENTO
    # ────────────────────────────────────────────────────────────────────────
    pgs = list(nfe.pagamentos.all()) if hasattr(nfe, 'pagamentos') else []
    if pgs:
        r_pag_tit = [[_p('<b>PAGAMENTO</b>', FS_SEC, color=white)]]
        elts.append(_tbl(r_pag_tit, [1.0], [
            ('BACKGROUND', (0, 0), (-1, -1), AZUL),
            ('BOX',        (0, 0), (-1, -1), 0.5, BORDA),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        rows_pag = []
        for pg in pgs:
            tp  = getattr(pg, 'tpag', None) or getattr(pg, 'forma_pagamento', '')
            val = getattr(pg, 'vpag', None) or getattr(pg, 'valor', 0)
            rows_pag.append([
                _p(_desc_pag(tp), FS_VAL),
                _p(f'R$ {_fmt(val)}', FS_VAL, align='RIGHT'),
            ])
        elts.append(_tbl(rows_pag, [0.70, 0.30], [
            ('BOX',  (0, 0), (-1, -1), 0.5, BORDA),
            ('GRID', (0, 0), (-1, -1), 0.3, BORDA),
        ]))

    # ────────────────────────────────────────────────────────────────────────
    # 9. DADOS ADICIONAIS
    # ────────────────────────────────────────────────────────────────────────
    info = getattr(nfe, 'informacoes_adicionais', '') or ''
    r_adic_tit = [[_p('<b>DADOS ADICIONAIS</b>', FS_SEC, color=white)]]
    elts.append(_tbl(r_adic_tit, [1.0], [
        ('BACKGROUND', (0, 0), (-1, -1), AZUL),
        ('BOX',        (0, 0), (-1, -1), 0.5, BORDA),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    r_adic = [[
        _campo('INFORMAÇÕES COMPLEMENTARES', info[:2000] or '---'),
        _campo('RESERVADO AO FISCO', ''),
    ]]
    elts.append(_tbl(r_adic, [0.55, 0.45], [
        ('BOX',      (0, 0), (-1, -1), 0.5, BORDA),
        ('GRID',     (0, 0), (-1, -1), 0.3, BORDA),
        ('MINHEIGHT',(0, 0), (-1, -1), 25 * mm),
    ]))

    # ────────────────────────────────────────────────────────────────────────
    # 10. RODAPÉ
    # ────────────────────────────────────────────────────────────────────────
    rodape_txt = (
        f'fl. 1/1   •   Chave: {ch_f}   •   '
        f'Protocolo: {prot}   •   {_d(nfe.data_autorizacao or nfe.data_emissao)}'
    )
    r_rod = [[_p(rodape_txt, FS_TIT, align='CENTER', color=HexColor('#555555'))]]
    elts.append(_tbl(r_rod, [1.0], [
        ('BOX',        (0, 0), (-1, -1), 0.5, BORDA),
        ('BACKGROUND', (0, 0), (-1, -1), CINZA),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    # ── Build ────────────────────────────────────────────────────────────────
    doc.build(elts)
    pdf = buf.getvalue()
    buf.close()
    return pdf
