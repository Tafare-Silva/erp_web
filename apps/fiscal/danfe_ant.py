"""DANFE no padrao SEFAZ conforme modelo anexado."""

import io
from datetime import datetime
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

from apps.cadastros.models import EnderecoPessoa

import os, reportlab
RL_DIR = os.path.dirname(reportlab.__file__)
FONT_DIR = os.path.join(RL_DIR, 'fonts')
for name, fname in [('Vera', 'Vera.ttf'), ('VeraBd', 'VeraBd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fname)))
addMapping('Vera', 0, 0, 'Vera')
addMapping('Vera', 1, 0, 'VeraBd')

FONT = 'Vera'
FB = 'VeraBd'
FS = 6.2
FSS = 5.2
MARGEM = 5 * mm
LARG = A4[0] - 2 * MARGEM
LPAD = 3
CINZA = HexColor('#f0f0f0')
BORDA = HexColor('#aaaaaa')
AZUL = HexColor('#1e3a8a')

def _p(text, sz=FS, bold=False, align='left', color=black):
    return Paragraph(
        f'<para align={align}>{text}</para>',
        ParagraphStyle('x', fontName=FB if bold else FONT, fontSize=sz,
                       leading=sz*1.2, textColor=color, spaceAfter=0, spaceBefore=0))

def _fmt(v):
    if v is None: return '0,00'
    try: return f'{Decimal(str(v)):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    except: return '0,00'

def _fmt_q(v):
    if v is None: return '0,000'
    try: return f'{Decimal(str(v)):,.3f}'.replace(',','X').replace('.',',').replace('X','.')
    except: return '0,000'

def _d(dt, f='%d/%m/%Y'):
    if not dt: return ''
    return dt.strftime(f) if isinstance(dt, datetime) else str(dt)

def _end(p):
    try: e = p.endereco_principal_rel.endereco
    except: e = p.enderecos.first()
    if not e: return ['']*7
    c = e.cidade
    return [e.logradouro, e.numero, e.complemento or '', e.bairro, c.nome, c.estado.uf, e.cep]

def _ie(p):
    return p.rg_ie or 'ISENTO'

def _tel(p):
    return p.telefone_fixo or p.celular_principal or ''

def _desc(fp):
    m = {1:'Dinheiro',2:'Cheque',3:'Cartão Crédito',4:'Cartão Débito',5:'Cartão Loja',
         10:'Vale Alimentação',11:'Vale Refeição',12:'Vale Presente',13:'Vale Combustível',
         14:'Duplicata',15:'Boleto',16:'Depósito',17:'PIX',18:'Transferência',
         19:'Fidelidade',90:'Sem Pagamento',99:'Outros'}
    return m.get(int(fp), str(fp))

def _chave(fmt, c):
    return '.'.join(c[i:i+4] for i in range(0,44,4))

def _tbl(rows, cw, styles=None):
    width = sum(LARG * w if isinstance(w, float) else w for w in cw)
    t = Table(rows, colWidths=[LARG * w if isinstance(w, float) else w for w in cw], repeatRows=1)
    s = [('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1),
         ('LEFTPADDING',(0,0),(-1,-1),LPAD),('RIGHTPADDING',(0,0),(-1,-1),LPAD)]
    if styles: s.extend(styles)
    t.setStyle(TableStyle(s))
    return t

def _s(text, style):
    return Paragraph(text, style)


def gerar_danfe(nfe):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=5*mm, bottomMargin=5*mm,
                            leftMargin=MARGEM, rightMargin=MARGEM)

    emit = nfe.empresa.pessoa
    dest = nfe.destinatario
    emp = nfe.empresa
    itens = list(nfe.itens.all().order_by('numero_item'))
    ch = nfe.chave_acesso
    ch_f = _chave(None, ch)
    el, en, ec, eb, ecid, euf, ecep = _end(emit)
    dl, dn, dc, db, dcid, duf, dcep = _end(dest)
    elts = []
    prot = nfe.protocolo or ''
    dp = _d(nfe.data_emissao)
    da = _d(nfe.data_autorizacao) or dp

    # ─── TOPO: RECEBIMENTO + NF-e Nº / DANFE ───
    r1 = [[
        _p(f'RECEBEMOS DE {emit.nome.upper()} OS PRODUTOS/SERVIÇOS CONSTANTES DA NOTA FISCAL INDICADO AO LADO', FSS),
        _p(f'<b>NF-e</b><br/>Nº <b>{str(nfe.numero).zfill(9)}</b><br/>SÉRIE {str(nfe.serie).zfill(3)}', FSS, align='right')
    ]]
    elts.append(_tbl(r1, [0.60, 0.25], [('BOX',(0,0),(-1,-1),0.5,BORDA),('TOPPADDING',(0,0),(-1,-1),2),
                                          ('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(0,0),4),
                                          ('RIGHTPADDING',(0,0),(1,1),4),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))

    # Linha assinatura
    r2 = [[
        _p('DATA DE RECEBIMENTO', FSS),
        _p('IDENTIFICAÇÃO E ASSINATURA DO RECEBEDOR', FSS),
    ]]
    elts.append(_tbl(r2, [0.20, 0.65], [('BOX',(0,0),(-1,-1),0.5,BORDA),('TOPPADDING',(0,0),(-1,-1),4),
                                          ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),4),
                                          ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))

    # ─── RESUMO DANFE ───
    saida = '1'
    r3 = [[
        _p('RESUMO', 7, align='center'),
    ],[
        _p('DANFE', 14, bold=True, align='center'),
        _p(f'<b>0</b> - ENTRADA &nbsp;&nbsp;&nbsp; <b><font color="blue">1</font></b> - SAÍDA', 9, align='right'),
    ],[
        _p('DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA', 7, align='center'),
        _p(f'Nº <b>{str(nfe.numero).zfill(9)}</b> &nbsp; SÉRIE <b>{str(nfe.serie).zfill(3)}</b>', 7, align='right'),
    ]]
    elts.append(_tbl(r3, [0.60, 0.25],
                       [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,-1),CINZA),
                        ('SPAN',(0,0),(0,2)),('SPAN',(1,0),(1,0)),
                        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1),
                        ('LEFTPADDING',(0,0),(0,0),10),('RIGHTPADDING',(0,0),(1,1),10),
                        ('ALIGN',(0,0),(0,2),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))

    # ─── CHAVE DE ACESSO + EMITENTE + PROTOCOLO ───
    r4 = [[
        _p(f'CHAVE DE ACESSO<br/><b>{ch_f}</b>', FSS),
        _p(f'Consulta de autenticidade no portal nacional da NF-e<br/>www.nfe.fazenda.gov.br/portal ou no site da Sefaz Autorizadora',
           FSS, align='right'),
    ],[
        _p(f'<b>IDENTIFICAÇÃO DO EMITENTE</b><br/>{emit.nome.upper()}<br/>'
           f'{el}, {en}{" - "+ec if ec else ""} &nbsp; {eb} - {ecid}/{euf} &nbsp; CEP: {ecep}',
           FSS),
        _p(f'<b>PROTOCOLO DE AUTORIZAÇÃO DE USO</b><br/>{prot}', FSS, align='right'),
    ],[
        _p(f'CNPJ: {emit.cpf_cnpj or "---"} &nbsp; IE: {_ie(emit)} &nbsp; TEL: {_tel(emit)}', FSS),
        _p(f'NATUREZA DA OPERAÇÃO<br/>{nfe.natureza_operacao or "---"}', FSS, align='right'),
    ]]
    elts.append(_tbl(r4, [0.55, 0.30],
                       [('BOX',(0,0),(-1,-1),0.5,BORDA),
                        ('SPAN',(0,0),(0,0)),('SPAN',(1,0),(1,0)),
                        ('SPAN',(0,1),(0,1)),('SPAN',(1,1),(1,1)),
                        ('SPAN',(0,2),(0,2)),('SPAN',(1,2),(1,2)),
                        ('GRID',(0,1),(1,2),0.3,BORDA),
                        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1),
                        ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))

    # ─── DESTINATÁRIO ───
    r5 = [[
        _p('<b>DESTINATÁRIO / REMETENTE</b>', FS),
    ],[
        _p(f'<b>NOME / RAZÃO SOCIAL</b><br/>{dest.nome}', FSS),
        _p(f'<b>CNPJ / CPF</b><br/>{dest.cpf_cnpj or "---"}', FSS),
        _p(f'<b>DATA DA EMISSÃO</b><br/>{dp}', FSS, align='center'),
        _p(f'<b>DATA SAÍDA / ENTRADA</b><br/>{dp}', FSS, align='center'),
        _p(f'<b>HORA DA SAÍDA</b><br/>{_d(nfe.data_emissao,"%H:%M:%S")}', FSS, align='center'),
    ],[
        _p(f'<b>ENDEREÇO</b><br/>{dl}, {dn}', FSS),
        _p(f'<b>MUNICÍPIO</b><br/>{dcid}', FSS),
        _p(f'<b>FONE / FAX</b><br/>{_tel(dest)}', FSS),
        _p(f'<b>BAIRRO / DISTRITO</b><br/>{db}', FSS),
        _p(f'<b>UF</b><br/>{duf}', FSS, align='center'),
    ],[
        _p(f'<b>INSCRIÇÃO ESTADUAL</b><br/>{_ie(dest)}', FSS),
        _p(f'<b>CEP</b><br/>{dcep}', FSS),
        _p('', FSS), _p('', FSS), _p('', FSS),
    ]]
    elts.append(_tbl(r5, [0.25, 0.18, 0.18, 0.18, 0.10],
                       [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,0),CINZA),
                        ('SPAN',(0,0),(-1,0)),('GRID',(0,1),(-1,-1),0.3,BORDA),
                        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOPPADDING',(0,0),(-1,-1),1)]))

    # ─── CÁLCULO DO IMPOSTO (2 colunas lado a lado) ───
    v_bc=_fmt(nfe.valor_base_calculo_icms); v_icms=_fmt(nfe.valor_icms)
    v_bc_st=_fmt(nfe.valor_base_calculo_icms_st); v_icms_st=_fmt(nfe.valor_icms_st)
    v_prod=_fmt(nfe.valor_total_produtos); v_frete=_fmt(nfe.valor_frete)
    v_seg=_fmt(nfe.valor_seguro); v_desc=_fmt(nfe.valor_desconto)
    v_outras=_fmt(nfe.valor_outras_despesas); v_ipi=_fmt(nfe.valor_ipi)
    v_total=_fmt(nfe.valor_total)

    cl = [
        _p('<b>CÁLCULO DO IMPOSTO</b>', FS),
        _p(f'BASE DE CÁLCULO DO ICMS', FSS), _p(v_bc, FSS, align='right'),
        _p(f'VALOR DO FRETE', FSS),  _p(v_frete, FSS, align='right'),
        _p(f'VALOR DO ICMS', FSS),   _p(v_icms, FSS, align='right'),
        _p(f'VALOR DO SEGURO', FSS), _p(v_seg, FSS, align='right'),
        _p(f'DESCONTO', FSS),        _p(v_desc, FSS, align='right'),
        _p(f'BASE CÁLC. ICMS SUBST.', FSS), _p(v_bc_st, FSS, align='right'),
        _p(f'OUTRAS DESP. ACESS.', FSS),    _p(v_outras, FSS, align='right'),
        _p(f'VALOR DO ICMS SUBST.', FSS),   _p(v_icms_st, FSS, align='right'),
        _p(f'VALOR DO IPI', FSS),           _p(v_ipi, FSS, align='right'),
        _p(f'<b>VALOR TOTAL DOS PRODUTOS</b>', FSS, bold=True), _p(f'<b>{v_prod}</b>', FSS, bold=True, align='right'),
        _p(f'<b>VALOR TOTAL DA NOTA</b>', 8, bold=True), _p(f'<b>R$ {v_total}</b>', 8, bold=True, align='right'),
    ]
    # Layout: 2 grupos de label+valor lado a lado por linha
    r6 = [[cl[0]]]
    for i in range(1, len(cl), 4):
        if i+3 < len(cl):
            r6.append([cl[i], cl[i+1], cl[i+2], cl[i+3]])
        else:
            r6.append([cl[i], cl[i+1], _p('',FSS), _p('',FSS)])
    elts.append(_tbl(r6, [0.22, 0.15, 0.22, 0.15],
                       [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,0),CINZA),
                        ('SPAN',(0,0),(-1,0)),('GRID',(0,1),(-1,-2),0.3,BORDA),
                        ('LINEBELOW',(0,-1),(-1,-1),1.5,black),
                        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)]))

    # ─── TRANSPORTADOR ───
    transp = nfe.transportadora
    mod_opts = dict(nfe._meta.get_field('modalidade_frete').choices)
    mod_txt = mod_opts.get(nfe.modalidade_frete, '9 - Sem Frete')
    r7 = [[
        _p('<b>TRANSPORTADOR / VOLUMES TRANSPORTADOS</b>', FS),
    ],[
        _p(f'<b>RAZÃO SOCIAL</b><br/>{transp.nome if transp else "---"}', FSS),
        _p(f'<b>FRETE POR CONTA</b><br/>{mod_txt}', FSS),
        _p(f'<b>QUANTIDADE</b><br/>{str(nfe.volumes)}', FSS, align='center'),
        _p(f'<b>ESPÉCIE</b><br/>{nfe.especie or "---"}', FSS),
        _p(f'<b>PESO BRUTO</b><br/>{_fmt_q(nfe.peso_bruto)}', FSS, align='right'),
        _p(f'<b>PESO LÍQUIDO</b><br/>{_fmt_q(nfe.peso_liquido)}', FSS, align='right'),
    ],[
        _p(f'<b>ENDEREÇO</b><br/>{_end(transp)[0] if transp else "---"}', FSS),
        _p(f'<b>MUNICÍPIO</b><br/>{_end(transp)[4] if transp else "---"}', FSS),
        _p(f'<b>UF</b><br/>{_end(transp)[5] if transp else ""}', FSS, align='center'),
        _p(f'<b>CNPJ / CPF</b><br/>{transp.cpf_cnpj if transp else "---"}', FSS),
        _p(f'<b>INSCRIÇÃO ESTADUAL</b><br/>{_ie(transp) if transp else "---"}', FSS),
        _p('', FSS),
    ]]
    elts.append(_tbl(r7, [0.22, 0.18, 0.10, 0.18, 0.12, 0.10],
                       [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,0),CINZA),
                        ('SPAN',(0,0),(-1,0)),('GRID',(0,1),(-1,-1),0.3,BORDA),
                        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)]))

    # ─── TABELA DE PRODUTOS ───
    cab = ['CÓDIGO', 'DESCRIÇÃO DO PRODUTO / SERVIÇO', 'NCM', 'CFOP', 'CST', 'UN',
           'QUANT.', 'VALOR UNIT.', 'VALOR TOTAL']
    cw = [0.07, 0.28, 0.06, 0.05, 0.04, 0.04, 0.08, 0.10, 0.10]
    d2 = [[_p(f'<b>{h}</b>', FSS) for h in cab]]
    for it in itens:
        d2.append([
            _p(it.codigo_produto[:12], FSS),
            _p(it.nome[:55], FSS),
            _p(it.ncm, FSS),
            _p(it.cfop, FSS, align='center'),
            _p(it.cst_icms or it.csosn or '', FSS, align='center'),
            _p(it.unidade, FSS, align='center'),
            _p(_fmt_q(it.quantidade), FSS, align='right'),
            _p(_fmt(it.valor_unitario), FSS, align='right'),
            _p(_fmt(it.valor_total), FSS, bold=True, align='right'),
        ])
    elts.append(_tbl(d2, cw,
                       [('BACKGROUND',(0,0),(-1,0),AZUL),('TEXTCOLOR',(0,0),(-1,0),white),
                        ('GRID',(0,0),(-1,-1),0.3,BORDA),
                        ('ROWBACKGROUNDS',(0,1),(-1,-1),[white,CINZA]),
                        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)]))

    # ─── PAGAMENTO ───
    pgs = list(nfe.pagamentos.all())
    if pgs:
        r9 = [[_p('<b>PAGAMENTO</b>', FS)]]
        for pg in pgs:
            r9.append([_p(f'{_desc(pg.forma_pagamento)}: R$ {_fmt(pg.valor)}', FSS)])
        elts.append(_tbl(r9, [LARG - 2*LPAD], [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,0),CINZA),
                                    ('SPAN',(0,0),(-1,0))]))

    # ─── DADOS ADICIONAIS ───
    if nfe.informacoes_adicionais:
        r10 = [[_p('<b>DADOS ADICIONAIS</b>', FS)],
               [_p(f'<b>INFORMAÇÕES COMPLEMENTARES</b><br/>{nfe.informacoes_adicionais[:3000]}', FSS)]]
        elts.append(_tbl(r10, [LARG - 2*LPAD], [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,0),CINZA),
                                     ('SPAN',(0,0),(-1,0)),('MINHEIGHT',(0,1),(-1,1),15)]))

    # ─── RODAPÉ ───
    r11 = [[
        _p(f'fl. 1/1 &nbsp;&nbsp;&nbsp; Chave: {ch_f} &nbsp;&nbsp;&nbsp; '
           f'Protocolo: {prot} &nbsp;&nbsp;&nbsp; {da}', FSS, align='center')
    ]]
    elts.append(_tbl(r11, [LARG - 2*LPAD], [('BOX',(0,0),(-1,-1),0.5,BORDA),('BACKGROUND',(0,0),(-1,-1),CINZA),
                                 ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))

    doc.build(elts)
    pdf = buf.getvalue()
    buf.close()
    return pdf
