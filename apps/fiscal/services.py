import hashlib
import base64
import logging
import re
import tempfile
import os
import warnings
from decimal import Decimal
from datetime import datetime, date, timedelta
from lxml import etree

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID

from signxml import XMLSigner, methods
from signxml.algorithms import SignatureMethod, DigestAlgorithm
from signxml.util import namespaces as sg_namespaces

from requests import Session
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from django.db import transaction
from django.utils import timezone

from apps.cadastros.models import (
    Empresa, Pessoa, Produto, MovimentacaoEstoque,
    ItemMovimentacaoEstoque, TipoPagamento, EnderecoPessoa
)
from .models import (
    CertificadoDigital, NFe, NFeItem, NFePagamento,
    NFeEvento, LoteNFe
)

SOAP_NS = {
    'nfeAutorizacaoLote': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4',
    'nfeRetAutorizacaoLote': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeRetAutorizacao4',
    'nfeConsultaNF': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4',
    'nfeStatusServicoNF': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4',
    'nfeRecepcaoEvento': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4',
}

logger = logging.getLogger(__name__)

NS_NFE = 'http://www.portalfiscal.inf.br/nfe'
NS_DS = 'http://www.w3.org/2000/09/xmldsig#'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
AMBIENTE_NFE = {'H': '2', 'P': '1'}



UF_PARA_CODIGO = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16',
    'TO': '17', 'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25',
    'PE': '26', 'AL': '27', 'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32',
    'RJ': '33', 'SP': '35', 'PR': '41', 'SC': '42', 'RS': '43', 'MS': '50',
    'MT': '51', 'GO': '52', 'DF': '53',
}

# Endpoints SEFAZ por UF (SVRS como fallback)
# Fonte: https://dfe-portal.svrs.rs.gov.br/Nfe/Servicos e portais estaduais
SEFAZ_POR_UF = {
    # SVRS (fallback) — usado por AC, AL, AP, DF, ES, MA, PA, PB, PI, RJ, RN, RO, RR, SC, SE, TO
    'DEFAULT': {
        'H': {
            'autorizacao': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx?wsdl',
            'evento': 'https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx?wsdl',
            'status': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://nfe.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://nfe.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx?wsdl',
            'evento': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx?wsdl',
            'status': 'https://nfe.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx?wsdl',
        },
    },
    'SP': {
        'H': {
            'autorizacao': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx?wsdl',
            'retorno': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx?wsdl',
            'consulta': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx?wsdl',
            'evento': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx?wsdl',
            'status': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx?wsdl',
            'retorno': 'https://nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx?wsdl',
            'consulta': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx?wsdl',
            'evento': 'https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx?wsdl',
            'status': 'https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx?wsdl',
        },
    },
    'RS': {
        'H': {
            'autorizacao': 'https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx?wsdl',
            'evento': 'https://nfe-homologacao.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx?wsdl',
            'status': 'https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://nfe.sefazrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://nfe.sefazrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx?wsdl',
            'evento': 'https://nfe.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx?wsdl',
            'status': 'https://nfe.sefazrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx?wsdl',
        },
    },
    'PR': {
        'H': {
            'autorizacao': 'https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4?wsdl',
            'retorno': 'https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4?wsdl',
            'status': 'https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4?wsdl',
            'retorno': 'https://nfe.sefa.pr.gov.br/nfe/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4?wsdl',
            'status': 'https://nfe.sefa.pr.gov.br/nfe/NFeStatusServico4?wsdl',
        },
    },
    'PR_ASMX': {
        'H': {
            'autorizacao': 'https://homologacao.nfe.sefa.pr.gov.br/ws/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://homologacao.nfe.sefa.pr.gov.br/ws/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://homologacao.nfe.sefa.pr.gov.br/ws/NFeConsultaProtocolo4.asmx?wsdl',
            'evento': 'https://homologacao.nfe.sefa.pr.gov.br/ws/NFeRecepcaoEvento4.asmx?wsdl',
            'status': 'https://homologacao.nfe.sefa.pr.gov.br/ws/NFeStatusServico4.asmx?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefa.pr.gov.br/ws/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://nfe.sefa.pr.gov.br/ws/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://nfe.sefa.pr.gov.br/ws/NFeConsultaProtocolo4.asmx?wsdl',
            'evento': 'https://nfe.sefa.pr.gov.br/ws/NFeRecepcaoEvento4.asmx?wsdl',
            'status': 'https://nfe.sefa.pr.gov.br/ws/NFeStatusServico4.asmx?wsdl',
        },
    },
    'MG': {
        'H': {
            'autorizacao': 'https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4?wsdl',
            'retorno': 'https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeRecepcaoEvento4?wsdl',
            'status': 'https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4?wsdl',
            'retorno': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeRecepcaoEvento4?wsdl',
            'status': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeStatusServico4?wsdl',
        },
    },
    'BA': {
        'H': {
            'autorizacao': 'https://hnfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://hnfe.sefaz.ba.gov.br/webservices/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://hnfe.sefaz.ba.gov.br/webservices/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx?wsdl',
            'evento': 'https://hnfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx?wsdl',
            'status': 'https://hnfe.sefaz.ba.gov.br/webservices/NFeStatusServico4/NFeStatusServico4.asmx?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx?wsdl',
            'retorno': 'https://nfe.sefaz.ba.gov.br/webservices/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx?wsdl',
            'consulta': 'https://nfe.sefaz.ba.gov.br/webservices/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx?wsdl',
            'evento': 'https://nfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx?wsdl',
            'status': 'https://nfe.sefaz.ba.gov.br/webservices/NFeStatusServico4/NFeStatusServico4.asmx?wsdl',
        },
    },
    'AM': {
        'H': {
            'autorizacao': 'https://homnfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4?wsdl',
            'retorno': 'https://homnfe.sefaz.am.gov.br/services2/services/NfeRetAutorizacao4?wsdl',
            'consulta': 'https://homnfe.sefaz.am.gov.br/services2/services/NfeConsulta4?wsdl',
            'evento': 'https://homnfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4?wsdl',
            'status': 'https://homnfe.sefaz.am.gov.br/services2/services/NfeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4?wsdl',
            'retorno': 'https://nfe.sefaz.am.gov.br/services2/services/NfeRetAutorizacao4?wsdl',
            'consulta': 'https://nfe.sefaz.am.gov.br/services2/services/NfeConsulta4?wsdl',
            'evento': 'https://nfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4?wsdl',
            'status': 'https://nfe.sefaz.am.gov.br/services2/services/NfeStatusServico4?wsdl',
        },
    },
    'GO': {
        'H': {
            'autorizacao': 'https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4?wsdl',
            'retorno': 'https://homolog.sefaz.go.gov.br/nfe/services/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://homolog.sefaz.go.gov.br/nfe/services/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://homolog.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4?wsdl',
            'status': 'https://homolog.sefaz.go.gov.br/nfe/services/NFeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4?wsdl',
            'retorno': 'https://nfe.sefaz.go.gov.br/nfe/services/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://nfe.sefaz.go.gov.br/nfe/services/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://nfe.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4?wsdl',
            'status': 'https://nfe.sefaz.go.gov.br/nfe/services/NFeStatusServico4?wsdl',
        },
    },
    'PE': {
        'H': {
            'autorizacao': 'https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4?wsdl',
            'retorno': 'https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeRecepcaoEvento4?wsdl',
            'status': 'https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4?wsdl',
            'retorno': 'https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeRecepcaoEvento4?wsdl',
            'status': 'https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeStatusServico4?wsdl',
        },
    },
    'MT': {
        'H': {
            'autorizacao': 'https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4?wsdl',
            'retorno': 'https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeRetAutorizacao4?wsdl',
            'consulta': 'https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4?wsdl',
            'evento': 'https://homologacao.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4?wsdl',
            'status': 'https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4?wsdl',
            'retorno': 'https://sefaz.mt.gov.br/nfews/v2/services/NfeRetAutorizacao4?wsdl',
            'consulta': 'https://sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4?wsdl',
            'evento': 'https://sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4?wsdl',
            'status': 'https://sefaz.mt.gov.br/nfews/v2/services/NfeStatusServico4?wsdl',
        },
    },
    'MS': {
        'H': {
            'autorizacao': 'https://hom.nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4?wsdl',
            'retorno': 'https://hom.nfe.sefaz.ms.gov.br/ws/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://hom.nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://hom.nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4?wsdl',
            'status': 'https://hom.nfe.sefaz.ms.gov.br/ws/NFeStatusServico4?wsdl',
        },
        'P': {
            'autorizacao': 'https://nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4?wsdl',
            'retorno': 'https://nfe.sefaz.ms.gov.br/ws/NFeRetAutorizacao4?wsdl',
            'consulta': 'https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4?wsdl',
            'evento': 'https://nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4?wsdl',
            'status': 'https://nfe.sefaz.ms.gov.br/ws/NFeStatusServico4?wsdl',
        },
    },
}


class _NFeSigner(XMLSigner):
    def check_deprecated_methods(self):
        pass


class NFeService:

    @staticmethod
    def gerar_cnf():
        import random
        return ''.join(random.choices('0123456789', k=8))

    @staticmethod
    def gerar_chave_acesso(empresa, ano, mes, cnpj, modelo, serie, numero, tp_emissao, cnf):
        uf = UF_PARA_CODIGO.get(empresa.uf_web_service_nfe, empresa.uf_web_service_nfe)
        cnpj_digits = ''.join(filter(str.isdigit, cnpj or ''))[-14:].zfill(14)
        num = str(numero).zfill(9)
        serie_str = str(serie).zfill(3)
        tipo_emissao = str(tp_emissao).zfill(1)
        cnf_str = str(cnf).zfill(8)
        ano_mes = f'{str(ano)[-2:]}{str(mes).zfill(2)}'

        chave = f'{uf}{ano_mes}{cnpj_digits}{modelo}{serie_str}{num}{tipo_emissao}{cnf_str}'

        dv = NFeService._calcular_dv_mod11(chave)
        return f'{chave}{dv}'

    @staticmethod
    def _calcular_dv_mod11(numero):
        soma = 0
        peso = 2
        for i in range(len(numero) - 1, -1, -1):
            soma += int(numero[i]) * peso
            peso += 1
            if peso > 9:
                peso = 2
        resto = soma % 11
        if resto < 2:
            return 0
        return 11 - resto

    @staticmethod
    def _formatar_cnpj(cnpj):
        return ''.join(filter(str.isdigit, cnpj or ''))[-14:].zfill(14)

    @staticmethod
    def _formatar_cpf(cpf):
        return ''.join(filter(str.isdigit, cpf or ''))[-11:].zfill(11)

    @staticmethod
    def _formatar_telefone(fone):
        digits = ''.join(filter(str.isdigit, fone or ''))
        return digits[:11] if len(digits) > 10 else digits

    @staticmethod
    def _to_decimal(valor):
        return Decimal(str(valor or 0))

    @staticmethod
    def _fmt_decimal(valor):
        d = Decimal(str(valor or 0))
        return f'{d:.2f}'

    @staticmethod
    def _tag(tag, texto=None, attrs=None):
        elem = etree.Element(f'{{{NS_NFE}}}{tag}', nsmap={None: NS_NFE})
        if texto is not None:
            elem.text = str(texto)
        if attrs:
            for k, v in attrs.items():
                elem.set(k, v)
        return elem

    @staticmethod
    def _add_tag(parent, tag, texto=None, attrs=None):
        elem = NFeService._tag(tag, texto, attrs)
        parent.append(elem)
        return elem

    @staticmethod
    def _get_endereco(pessoa):
        try:
            endereco = pessoa.endereco_principal_rel.endereco
        except (EnderecoPessoa.DoesNotExist, AttributeError):
            endereco = pessoa.enderecos.first()
        return endereco

    @staticmethod
    def _add_endereco(parent, endereco, nome_tag='ender'):
        if endereco is None:
            return
        ender = NFeService._tag(nome_tag)
        parent.append(ender)
        cidade = endereco.cidade
        NFeService._add_tag(ender, 'xLgr', str(endereco.logradouro)[:60])
        NFeService._add_tag(ender, 'nro', str(endereco.numero)[:10])
        if endereco.complemento:
            NFeService._add_tag(ender, 'xCpl', str(endereco.complemento)[:60])
        NFeService._add_tag(ender, 'xBairro', str(endereco.bairro)[:60])
        NFeService._add_tag(ender, 'cMun', str(cidade.codigo_ibge).zfill(7))
        NFeService._add_tag(ender, 'xMun', str(cidade.nome)[:60])
        NFeService._add_tag(ender, 'UF', cidade.estado.uf)
        if endereco.cep:
            NFeService._add_tag(ender, 'CEP', ''.join(filter(str.isdigit, endereco.cep)).zfill(8))
        NFeService._add_tag(ender, 'cPais', '1058')
        NFeService._add_tag(ender, 'xPais', 'BRASIL')
        fone = NFeService._formatar_telefone(endereco.pessoa.telefone_fixo or endereco.pessoa.celular_principal)
        if fone:
            NFeService._add_tag(ender, 'fone', fone)

    @staticmethod
    def _build_nfe_content(nfe, nfe_root):
        """Popula os elementos NFe dentro de nfe_root (herda namespace do parent)"""
        infNFe = NFeService._tag('infNFe', attrs={'Id': f'NFe{nfe.chave_acesso}', 'versao': '4.00'})
        nfe_root.append(infNFe)

        empresa = nfe.empresa
        emit_pessoa = empresa.pessoa
        dest_pessoa = nfe.destinatario

        # ---- ide ----
        ide = NFeService._tag('ide')
        infNFe.append(ide)
        c_mun_fg = str(empresa.cidade_sede.codigo_ibge).zfill(7) if empresa.cidade_sede else '4106902'
        NFeService._add_tag(ide, 'cUF', UF_PARA_CODIGO.get(empresa.uf_web_service_nfe, empresa.uf_web_service_nfe))
        cnf_field = nfe.chave_acesso[35:43] if len(nfe.chave_acesso) >= 43 else nfe.chave_acesso[-9:-1]
        NFeService._add_tag(ide, 'cNF', cnf_field)
        NFeService._add_tag(ide, 'natOp', nfe.natureza_operacao[:60])
        NFeService._add_tag(ide, 'mod', nfe.modelo)
        NFeService._add_tag(ide, 'serie', str(nfe.serie))
        NFeService._add_tag(ide, 'nNF', str(nfe.numero))
        local_dt = timezone.localtime(nfe.data_emissao)
        NFeService._add_tag(ide, 'dhEmi', local_dt.isoformat(timespec='seconds'))
        NFeService._add_tag(ide, 'tpNF', '1')
        NFeService._add_tag(ide, 'idDest', '1')
        NFeService._add_tag(ide, 'cMunFG', c_mun_fg)
        NFeService._add_tag(ide, 'tpImp', '1')
        NFeService._add_tag(ide, 'tpEmis', str(nfe.tipo_emissao))
        NFeService._add_tag(ide, 'cDV', nfe.chave_acesso[-1])
        NFeService._add_tag(ide, 'tpAmb', AMBIENTE_NFE.get(empresa.ambiente_destino, '2'))
        NFeService._add_tag(ide, 'finNFe', str(nfe.finalidade))
        NFeService._add_tag(ide, 'indFinal', '1' if nfe.consumo_final else '0')
        NFeService._add_tag(ide, 'indPres', str(nfe.presenca_comprador))
        NFeService._add_tag(ide, 'procEmi', '0')
        NFeService._add_tag(ide, 'verProc', 'ERP Blanjos 1.0')

        # ---- emit ----
        emit = NFeService._tag('emit')
        infNFe.append(emit)
        NFeService._add_tag(emit, 'CNPJ', NFeService._formatar_cnpj(emit_pessoa.cpf_cnpj))
        NFeService._add_tag(emit, 'xNome', (emit_pessoa.nome_fantasia or emit_pessoa.nome)[:60])
        fantasia = (emit_pessoa.nome_fantasia or emit_pessoa.nome)[:60]
        NFeService._add_tag(emit, 'xFant', fantasia)

        ender_emit = NFeService._get_endereco(emit_pessoa)
        if not ender_emit:
            raise ValueError(
                f'Empresa "{empresa.pessoa.nome}" não possui endereço cadastrado. '
                'Cadastre um endereço principal antes de emitir NF-e.'
            )
        NFeService._add_endereco(emit, ender_emit, 'enderEmit')

        NFeService._add_tag(emit, 'IE', emit_pessoa.rg_ie or '')
        if emit_pessoa.ins_municipal:
            NFeService._add_tag(emit, 'IEST', emit_pessoa.ins_municipal)
        NFeService._add_tag(emit, 'CRT', str(empresa.crt_nfe or 3))

        # ---- dest ----
        dest = NFeService._tag('dest')
        infNFe.append(dest)
        is_homolog = empresa.ambiente_destino == 'H'
        if is_homolog:
            NFeService._add_tag(dest, 'CNPJ', '99999999000191')
            NFeService._add_tag(dest, 'xNome', 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL')
            ender_homolog = NFeService._get_endereco(emit_pessoa)
            if ender_homolog:
                NFeService._add_endereco(dest, ender_homolog, 'enderDest')
            NFeService._add_tag(dest, 'indIEDest', '9')
        else:
            cpf_cnpj_dest = dest_pessoa.cpf_cnpj or ''
            if len(NFeService._formatar_cpf(cpf_cnpj_dest)) == 11:
                NFeService._add_tag(dest, 'CPF', NFeService._formatar_cpf(cpf_cnpj_dest))
            else:
                NFeService._add_tag(dest, 'CNPJ', NFeService._formatar_cnpj(cpf_cnpj_dest))
            NFeService._add_tag(dest, 'xNome', dest_pessoa.nome[:60])

            ender_dest = NFeService._get_endereco(dest_pessoa)
            if ender_dest:
                NFeService._add_endereco(dest, ender_dest, 'enderDest')
            elif nfe.modelo == '55':
                if len(NFeService._formatar_cpf(cpf_cnpj_dest)) == 11 and not dest_pessoa.rg_ie:
                    pass
                else:
                    raise ValueError(
                        f'Destinatário "{dest_pessoa.nome}" não possui endereço cadastrado. '
                        'Cadastre um endereço antes de emitir NF-e.'
                    )

            if dest_pessoa.rg_ie:
                NFeService._add_tag(dest, 'indIEDest', '1')
                NFeService._add_tag(dest, 'IE', dest_pessoa.rg_ie)
            else:
                NFeService._add_tag(dest, 'indIEDest', '9')
            if dest_pessoa.email:
                NFeService._add_tag(dest, 'email', dest_pessoa.email[:60])

        # ---- det (itens) ----
        for item in nfe.itens.all():
            det = NFeService._tag('det', attrs={'nItem': str(item.numero_item)})
            infNFe.append(det)

            prod = NFeService._tag('prod')
            det.append(prod)
            NFeService._add_tag(prod, 'cProd', str(item.codigo_produto)[:60])
            NFeService._add_tag(prod, 'cEAN', item.ean if item.ean else 'SEM GTIN')
            NFeService._add_tag(prod, 'xProd', item.nome[:120])
            NFeService._add_tag(prod, 'NCM', item.ncm or '00000000')
            if item.cest and item.cest != '0000000':
                NFeService._add_tag(prod, 'CEST', item.cest)
            NFeService._add_tag(prod, 'CFOP', item.cfop)
            NFeService._add_tag(prod, 'uCom', item.unidade or 'UN')
            NFeService._add_tag(prod, 'qCom', str(item.quantidade))
            NFeService._add_tag(prod, 'vUnCom', f'{item.valor_unitario:.6f}')
            NFeService._add_tag(prod, 'vProd', NFeService._fmt_decimal(item.valor_total))
            NFeService._add_tag(prod, 'cEANTrib', item.ean if item.ean else 'SEM GTIN')
            NFeService._add_tag(prod, 'uTrib', item.unidade or 'UN')
            NFeService._add_tag(prod, 'qTrib', str(item.quantidade))
            NFeService._add_tag(prod, 'vUnTrib', f'{item.valor_unitario:.6f}')
            NFeService._add_tag(prod, 'indTot', '1')

            imposto = NFeService._tag('imposto')
            det.append(imposto)

            icms = NFeService._tag('ICMS')
            imposto.append(icms)
            if empresa.crt_nfe in (1, 2):
                csosn = item.csosn or '102'
                icms_tag = NFeService._tag(f'ICMSSN{csosn}')
                icms.append(icms_tag)
                NFeService._add_tag(icms_tag, 'orig', item.origem or '0')
                NFeService._add_tag(icms_tag, 'CSOSN', csosn)
                if csosn in ('101', '201', '202', '203'):
                    NFeService._add_tag(icms_tag, 'pCredSN', '0.00')
                    NFeService._add_tag(icms_tag, 'vCredICMSSN', NFeService._fmt_decimal(item.valor_icms))
            else:
                cst = item.cst_icms or '00'
                icms_tag = NFeService._tag(f'ICMS{cst}')
                icms.append(icms_tag)
                NFeService._add_tag(icms_tag, 'orig', item.origem or '0')
                NFeService._add_tag(icms_tag, 'CST', cst)
                if cst in ('00', '10', '20', '70', '90'):
                    NFeService._add_tag(icms_tag, 'modBC', '3')
                    NFeService._add_tag(icms_tag, 'vBC', str(item.base_calculo_icms))
                    NFeService._add_tag(icms_tag, 'pICMS', f'{item.aliquota_icms:.2f}')
                    NFeService._add_tag(icms_tag, 'vICMS', NFeService._fmt_decimal(item.valor_icms))

            for imp_tipo, prefix in [('PIS', 'pis'), ('COFINS', 'cofins')]:
                cst_val = getattr(item, f'cst_{prefix}', '')
                aliq = getattr(item, f'aliquota_{prefix}', Decimal('0'))
                bc = getattr(item, f'base_calculo_{prefix}', Decimal('0'))
                valor = getattr(item, f'valor_{prefix}', Decimal('0'))
                imp_elem = NFeService._tag(imp_tipo)
                imposto.append(imp_elem)
                if cst_val in ('01', '02'):
                    sub = NFeService._tag(f'{imp_tipo}Aliq')
                    imp_elem.append(sub)
                    NFeService._add_tag(sub, 'CST', cst_val)
                    NFeService._add_tag(sub, 'vBC', NFeService._fmt_decimal(bc))
                    NFeService._add_tag(sub, f'p{imp_tipo}', NFeService._fmt_decimal(aliq))
                    NFeService._add_tag(sub, f'v{imp_tipo}', NFeService._fmt_decimal(valor))
                else:
                    sub = NFeService._tag(f'{imp_tipo}NT')
                    imp_elem.append(sub)
                    NFeService._add_tag(sub, 'CST', cst_val or '07')

        # ---- total ----
        total = NFeService._tag('total')
        infNFe.append(total)
        icms_tot = NFeService._tag('ICMSTot')
        total.append(icms_tot)
        itens = list(nfe.itens.all())
        v_prod = nfe.valor_total_produtos or sum(i.valor_total for i in itens)
        v_bc = Decimal('0')
        v_icms = Decimal('0')
        for i in itens:
            csosn = i.csosn or ''
            cst = i.cst_icms or ''
            if empresa.crt_nfe in (1, 2):
                if csosn in ('101', '201', '202', '900'):
                    v_bc += i.base_calculo_icms or Decimal('0')
                    v_icms += i.valor_icms or Decimal('0')
            else:
                if cst not in ('40', '41', '60', '51'):
                    v_bc += i.base_calculo_icms or Decimal('0')
                    v_icms += i.valor_icms or Decimal('0')
        NFeService._add_tag(icms_tot, 'vBC', NFeService._fmt_decimal(v_bc))
        NFeService._add_tag(icms_tot, 'vICMS', NFeService._fmt_decimal(v_icms))
        NFeService._add_tag(icms_tot, 'vICMSDeson', '0.00')
        NFeService._add_tag(icms_tot, 'vFCP', '0.00')
        NFeService._add_tag(icms_tot, 'vBCST', NFeService._fmt_decimal(nfe.valor_base_calculo_icms_st))
        NFeService._add_tag(icms_tot, 'vST', NFeService._fmt_decimal(nfe.valor_icms_st))
        NFeService._add_tag(icms_tot, 'vFCPST', '0.00')
        NFeService._add_tag(icms_tot, 'vFCPSTRet', '0.00')
        NFeService._add_tag(icms_tot, 'vProd', NFeService._fmt_decimal(v_prod))
        NFeService._add_tag(icms_tot, 'vFrete', NFeService._fmt_decimal(nfe.valor_frete))
        NFeService._add_tag(icms_tot, 'vSeg', NFeService._fmt_decimal(nfe.valor_seguro))
        NFeService._add_tag(icms_tot, 'vDesc', NFeService._fmt_decimal(nfe.valor_desconto))
        NFeService._add_tag(icms_tot, 'vII', '0.00')
        NFeService._add_tag(icms_tot, 'vIPI', NFeService._fmt_decimal(nfe.valor_ipi))
        NFeService._add_tag(icms_tot, 'vIPIDevol', '0.00')
        v_pis = sum(i.valor_pis or Decimal('0') for i in itens)
        v_cofins = sum(i.valor_cofins or Decimal('0') for i in itens)
        NFeService._add_tag(icms_tot, 'vPIS', NFeService._fmt_decimal(v_pis))
        NFeService._add_tag(icms_tot, 'vCOFINS', NFeService._fmt_decimal(v_cofins))
        NFeService._add_tag(icms_tot, 'vOutro', NFeService._fmt_decimal(nfe.valor_outras_despesas))
        NFeService._add_tag(icms_tot, 'vNF', NFeService._fmt_decimal(nfe.valor_total))

        # ---- transp ----
        transp = NFeService._tag('transp')
        infNFe.append(transp)
        NFeService._add_tag(transp, 'modFrete', str(nfe.modalidade_frete))

        if nfe.transportadora_id:
            transporta = NFeService._tag('transporta')
            transp.append(transporta)
            NFeService._add_tag(transporta, 'CNPJ', nfe.transportadora.cpf_cnpj or '')
            NFeService._add_tag(transporta, 'xNome', nfe.transportadora.nome[:60])
            ie = nfe.transportadora.rg_ie or ''
            if ie:
                NFeService._add_tag(transporta, 'IE', ie)
            end_transp = (
                nfe.transportadora.endereco_principal_rel.endereco if hasattr(nfe.transportadora, 'endereco_principal_rel')
                and nfe.transportadora.endereco_principal_rel
                else None
            )
            if end_transp:
                NFeService._add_tag(transporta, 'xEnder', f'{end_transp.logradouro}, {end_transp.numero} - {end_transp.bairro}')
                NFeService._add_tag(transporta, 'xMun', end_transp.cidade.nome)
                NFeService._add_tag(transporta, 'UF', end_transp.cidade.estado.uf)

        if nfe.volumes or nfe.peso_bruto or nfe.peso_liquido:
            vol = NFeService._tag('vol')
            transp.append(vol)
            if nfe.volumes:
                NFeService._add_tag(vol, 'qVol', str(nfe.volumes))
            if nfe.especie:
                NFeService._add_tag(vol, 'esp', nfe.especie)
            if nfe.peso_bruto:
                NFeService._add_tag(vol, 'pesoB', str(nfe.peso_bruto))
            if nfe.peso_liquido:
                NFeService._add_tag(vol, 'pesoL', str(nfe.peso_liquido))

        # ---- pag ----
        pag = NFeService._tag('pag')
        infNFe.append(pag)
        pagamentos = nfe.pagamentos.all()
        if not pagamentos:
            det_pag = NFeService._tag('detPag')
            pag.append(det_pag)
            NFeService._add_tag(det_pag, 'tPag', '90')
            NFeService._add_tag(det_pag, 'vPag', NFeService._fmt_decimal(Decimal('0.00')))
        else:
            for pgto in pagamentos:
                det_pag = NFeService._tag('detPag')
                pag.append(det_pag)
                NFeService._add_tag(det_pag, 'indPag', '0')
                NFeService._add_tag(det_pag, 'tPag', str(pgto.forma_pagamento).zfill(2))
                NFeService._add_tag(det_pag, 'vPag', NFeService._fmt_decimal(pgto.valor))

        # ---- infAdic ----
        if nfe.informacoes_adicionais:
            inf_adc = NFeService._tag('infAdic')
            infNFe.append(inf_adc)
            NFeService._add_tag(inf_adc, 'infCpl', nfe.informacoes_adicionais[:5000])

        # ---- infRespTec ----
        if empresa.resp_tec_cnpj:
            resp_tec = NFeService._tag('infRespTec')
            infNFe.append(resp_tec)
            NFeService._add_tag(resp_tec, 'CNPJ', NFeService._formatar_cnpj(empresa.resp_tec_cnpj))
            NFeService._add_tag(resp_tec, 'xContato', empresa.resp_tec_contato[:60])
            NFeService._add_tag(resp_tec, 'email', empresa.resp_tec_email[:60])
            NFeService._add_tag(resp_tec, 'fone', NFeService._formatar_telefone(empresa.resp_tec_fone))
            if empresa.resp_tec_csrt_id and empresa.resp_tec_csrt:
                csrt_data = (empresa.resp_tec_csrt + NFeService._formatar_cnpj(empresa.resp_tec_cnpj) + nfe.chave_acesso).encode('utf-8')
                hash_csrt = hashlib.sha1(csrt_data).hexdigest().upper()
                NFeService._add_tag(resp_tec, 'idCSRT', empresa.resp_tec_csrt_id)
                NFeService._add_tag(resp_tec, 'hashCSRT', hash_csrt)

    @staticmethod
    def gerar_xml_nfe(nfe):
        root = etree.Element(f'{{{NS_NFE}}}NFe', nsmap={None: NS_NFE})
        NFeService._build_nfe_content(nfe, root)
        return etree.tostring(root, pretty_print=False, xml_declaration=True, encoding='UTF-8')

    @staticmethod
    def criar_nfe_da_venda(movimentacao_id, usuario=None, modelo='55', serie=None,
                            modalidade_frete=9, volumes=0, especie='',
                            peso_bruto=0, peso_liquido=0):
        mov = MovimentacaoEstoque.objects.select_related(
            'pessoa', 'vendedor'
        ).prefetch_related('itens__produto').get(pk=movimentacao_id)

        empresa = Empresa.objects.first()
        if not empresa:
            raise ValueError('Nenhuma empresa cadastrada')

        if serie is None:
            serie = empresa.serie_nfe if modelo == '55' else empresa.serie_nfce

        ultima_nfe = NFe.objects.filter(empresa=empresa, modelo=modelo).order_by('-numero').first()
        novo_numero = (ultima_nfe.numero or 0) + 1 if ultima_nfe else 1

        cnf_value = NFeService.gerar_cnf()
        chave = NFeService.gerar_chave_acesso(
            empresa, datetime.now().year, datetime.now().month,
            empresa.pessoa.cpf_cnpj, modelo, serie, novo_numero, 1, cnf_value
        )

        itens_mov = mov.itens.all()
        v_prod = sum(abs(i.vr_total_bruto or 0) for i in itens_mov)

        with transaction.atomic():
            nfe = NFe.objects.create(
                movimentacao=mov,
                empresa=empresa,
                destinatario=mov.pessoa,
                modelo=modelo,
                serie=serie,
                numero=novo_numero,
                chave_acesso=chave,
                natureza_operacao='VENDA',
                finalidade=1,
                consumo_final=True,
                presenca_comprador=1,
                status='DIGITACAO',
                valor_total=v_prod,
                valor_total_produtos=v_prod,
                data_emissao=timezone.now(),
                modalidade_frete=modalidade_frete,
                volumes=volumes,
                especie=especie[:60],
                peso_bruto=peso_bruto,
                peso_liquido=peso_liquido,
            )

            for i, item_mov in enumerate(itens_mov, 1):
                prod = item_mov.produto
                NFeItem.objects.create(
                    nfe=nfe,
                    item_movimentacao=item_mov,
                    produto=prod,
                    numero_item=i,
                    codigo_produto=str(prod.pk_chave),
                    ean='SEM GTIN',
                    nome=prod.nome[:120],
                    ncm=prod.ncm.ncm if prod.ncm else '00000000',
                    cest=prod.cest or '0000000',
                    cfop=prod.cfop_venda_estadual or '5102',
                    unidade=prod.unidade_venda.simbolo if prod.unidade_venda else 'UN',
                    quantidade=abs(item_mov.quantidade or 0),
                    valor_unitario=abs(item_mov.vr_unitario_bruto or 0),
                    valor_total=abs(item_mov.vr_total_bruto or 0),
                    origem=prod.origem or '0',
                    cst_icms=prod.cst_icms or '',
                    csosn='102',
                    aliquota_icms=prod.aliquota_icms or 0,
                    base_calculo_icms=abs(item_mov.vr_total_bruto or 0),
                    valor_icms=abs(item_mov.vr_total_bruto or 0) * (prod.aliquota_icms or 0) / 100,
                )

            xml_bytes = NFeService.gerar_xml_nfe(nfe)
            nfe.xml_enviado = xml_bytes.decode('utf-8')
            nfe.status = 'VALIDADO'
            nfe.save(update_fields=['xml_enviado', 'status', 'modalidade_frete',
                                     'volumes', 'especie', 'peso_bruto', 'peso_liquido'])

        return nfe

    # ===================== CERTIFICADO =====================

    @staticmethod
    def _carregar_certificado(empresa):
        cert_obj = empresa.certificado_digital
        if not cert_obj:
            raise ValueError('Nenhum certificado digital vinculado à empresa')
        if not cert_obj.arquivo:
            raise ValueError('Certificado digital sem arquivo')
        if not cert_obj.ativo:
            raise ValueError('Certificado digital está inativo')
        if cert_obj.validade_fim < date.today():
            raise ValueError('Certificado digital vencido')

        cert_obj.arquivo.seek(0)
        pfx_bytes = cert_obj.arquivo.read()
        try:
            private_key, certificate, extra_certs = pkcs12.load_key_and_certificates(
                pfx_bytes, cert_obj.senha.encode('utf-8')
            )
        except Exception as e:
            raise ValueError(f'Erro ao ler certificado: {str(e)}')

        if certificate is None or private_key is None:
            raise ValueError('Certificado ou chave privada não encontrados no PFX')

        return private_key, certificate

    @staticmethod
    def assinar_xml(xml_bytes, empresa):
        private_key, certificate = NFeService._carregar_certificado(empresa)
        root = etree.fromstring(xml_bytes)
        infnfe = root.find(f'{{{NS_NFE}}}infNFe')
        if infnfe is None:
            raise ValueError('Elemento infNFe não encontrado no XML')
        ref_id = infnfe.get('Id')
        if not ref_id:
            raise ValueError('atributo Id não encontrado em infNFe')
        infnfe.set('Id', ref_id)

        signer = _NFeSigner(
            method=methods.enveloped,
            signature_algorithm='rsa-sha1',
            digest_algorithm='sha1',
            c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
        )
        signer.namespaces = {None: sg_namespaces.ds}
        signed_root = signer.sign(root, key=private_key, cert=[certificate], reference_uri=f'#{ref_id}')

        signature = signed_root.find(f'{{{sg_namespaces.ds}}}Signature')
        if signature is not None:
            signed_root.remove(signature)
            infnfe.append(signature)

        return etree.tostring(signed_root, xml_declaration=True, encoding='UTF-8')

    @staticmethod
    def _limpar_xml(xml_str):
        xml_str = xml_str.lstrip('\ufeff')
        xml_str = re.sub(r'>\s+<', '><', xml_str)
        return xml_str.strip()

    @staticmethod
    def montar_lote_nfe(nfe):
        nfe_bytes = NFeService.assinar_xml(NFeService.gerar_xml_nfe(nfe), nfe.empresa)
        nfe_root = etree.fromstring(nfe_bytes)

        envi = etree.Element(f'{{{NS_NFE}}}enviNFe', nsmap={None: NS_NFE}, versao='4.00')
        id_lote = etree.SubElement(envi, f'{{{NS_NFE}}}idLote')
        id_lote.text = str(nfe.pk)
        ind_sinc = etree.SubElement(envi, f'{{{NS_NFE}}}indSinc')
        ind_sinc.text = '1'
        envi.append(nfe_root)

        return etree.tostring(envi, xml_declaration=True, encoding='UTF-8')

    @staticmethod
    def _criar_session_cert(empresa):
        private_key, certificate = NFeService._carregar_certificado(empresa)

        tmp_key = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
        tmp_cert = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
        try:
            tmp_key.write(private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption(),
            ))
            tmp_key.close()
            tmp_cert.write(certificate.public_bytes(Encoding.PEM))
            tmp_cert.close()
            session = Session()
            session.cert = (tmp_cert.name, tmp_key.name)
            session.verify = False
            return session, tmp_key.name, tmp_cert.name
        except Exception:
            os.unlink(tmp_key.name)
            os.unlink(tmp_cert.name)
            raise

    # ===================== SEFAZ SOAP =====================

    @staticmethod
    def _get_sefaz_urls(empresa):
        ambiente = empresa.ambiente_destino
        uf = empresa.uf_web_service_nfe
        urls_por_uf = SEFAZ_POR_UF.get(uf) or SEFAZ_POR_UF['DEFAULT']
        return urls_por_uf.get(ambiente, urls_por_uf['H'])

    @staticmethod
    def _enviar_soap(wsdl_url, soap_action, xml_bytes, empresa):
        session, tmp_key_path, tmp_cert_path = NFeService._criar_session_cert(empresa)
        try:
            soap_url = wsdl_url.replace('?wsdl', '').replace('?WSDL', '')
            xml_str = xml_bytes.decode() if isinstance(xml_bytes, bytes) else xml_bytes
            xml_str = xml_str.split('?>', 1)[-1].strip()
            xml_str = NFeService._limpar_xml(xml_str)
            soap_ns = SOAP_NS.get(soap_action, f'http://www.portalfiscal.inf.br/nfe/wsdl/{soap_action}')
            body = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
                '<soap:Body>'
                f'<nfeDadosMsg xmlns="{soap_ns}">{xml_str}</nfeDadosMsg>'
                '</soap:Body>'
                '</soap:Envelope>'
            )
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': soap_action,
            }
            logger.warning('--- SOAP REQUEST URL: %s', soap_url)
            logger.warning('--- SOAP REQUEST BODY ---\n%s', body)
            resp = session.post(soap_url, data=body.encode('utf-8'), headers=headers, timeout=60)
            logger.warning('--- SOAP RESPONSE STATUS: %s', resp.status_code)
            logger.warning('--- SOAP RESPONSE BODY ---\n%s', resp.text[:2000])
            resp.raise_for_status()
            return resp.text
        finally:
            session.close()
            try:
                os.unlink(tmp_key_path)
                os.unlink(tmp_cert_path)
            except OSError:
                pass

    @staticmethod
    @transaction.atomic
    def autorizar_nfe(nfe_id):
        nfe = NFe.objects.select_related(
            'empresa__pessoa', 'empresa__certificado_digital',
            'empresa__cidade_sede__estado'
        ).prefetch_related('itens', 'pagamentos').get(pk=nfe_id)

        empresa = nfe.empresa
        if not empresa.certificado_digital:
            raise ValueError('Vincule um certificado digital à empresa em Cadastros > Empresa')

        nfe.xml_enviado = NFeService.gerar_xml_nfe(nfe).decode('utf-8')
        lote_xml = NFeService.montar_lote_nfe(nfe)

        urls = NFeService._get_sefaz_urls(empresa)
        lote, _ = LoteNFe.objects.get_or_create(
            empresa=empresa,
            numero_lote=nfe.pk,
            defaults={'status': 'ENVIADO'}
        )
        nfe.lote = lote
        nfe.status = 'ENVIADO'
        nfe.data_envio = timezone.now()
        nfe.save(update_fields=['xml_enviado', 'lote', 'status', 'data_envio'])

        try:
            response = NFeService._enviar_soap(
                urls['autorizacao'],
                'nfeAutorizacaoLote',
                lote_xml,
                empresa,
            )
            lote.xml_retorno = str(response)
            lote.save(update_fields=['xml_retorno'])

            return NFeService._processar_retorno_autorizacao(nfe, response)
        except Exception as e:
            nfe.status = 'REJEITADO'
            nfe.mensagem_retorno = f'Erro comunicação SEFAZ: {str(e)}'
            nfe.save(update_fields=['status', 'mensagem_retorno'])
            raise

    @staticmethod
    def _processar_retorno_autorizacao(nfe, response):
        try:
            ret_xml = response if isinstance(response, str) else str(response)
            if not ret_xml:
                nfe.status = 'REJEITADO'
                nfe.mensagem_retorno = 'Resposta vazia da SEFAZ'
                nfe.save(update_fields=['status', 'mensagem_retorno'])
                return nfe

            root = etree.fromstring(ret_xml.encode('utf-8'))
            ns_soap = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
            ns_nfe = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

            body = root.find('.//soap:Body', ns_soap)
            if body is not None:
                body_text = etree.tostring(body, encoding='unicode')
                root = etree.fromstring(body_text.encode('utf-8'))

            prot = root.find('.//ns:protNFe', ns_nfe)
            if prot is not None:
                inf_prot = prot.find('ns:infProt', ns_nfe)
                if inf_prot is not None:
                    nfe.protocolo = inf_prot.findtext('ns:nProt', '', ns_nfe)
                    nfe.mensagem_retorno = inf_prot.findtext('ns:xMotivo', '', ns_nfe)
                    c_stat = inf_prot.findtext('ns:cStat', '', ns_nfe)
                    if c_stat == '100':
                        nfe.status = 'AUTORIZADO'
                        nfe.data_autorizacao = timezone.now()
                    elif c_stat == '150':
                        nfe.status = 'DENEGADO'
                    else:
                        nfe.status = 'REJEITADO'
                    nfe.xml_retorno = ret_xml
                    nfe.save(update_fields=[
                        'status', 'protocolo', 'mensagem_retorno',
                        'data_autorizacao', 'xml_retorno'
                    ])
                    return nfe

            ret = root.find('.//ns:retEnviNFe', ns_nfe)
            if ret is not None:
                nfe.mensagem_retorno = ret.findtext('ns:xMotivo', 'Retorno não reconhecido', ns_nfe)
                nfe.protocolo = ret.findtext('ns:nRec', '', ns_nfe)
                c_stat = ret.findtext('ns:cStat', '', ns_nfe)
                nfe.status = 'AUTORIZADO' if c_stat == '100' else 'REJEITADO' if c_stat not in ('103', '104') else 'ENVIADO'
                nfe.xml_retorno = ret_xml
                nfe.save(update_fields=[
                    'status', 'protocolo', 'mensagem_retorno',
                    'data_autorizacao', 'xml_retorno'
                ])
                if c_stat in ('103', '104'):
                    logger.warning('--- LOTE RECEBIDO (ASSINCRONO), nRec=%s', ret.findtext('ns:nRec', '', ns_nfe))
                return nfe

            nfe.status = 'REJEITADO'
            nfe.mensagem_retorno = f'Retorno SEFAZ não reconhecido: {ret_xml[:500]}'
            nfe.save(update_fields=['status', 'mensagem_retorno'])
            return nfe
        except Exception as e:
            nfe.status = 'REJEITADO'
            nfe.mensagem_retorno = f'Erro ao processar retorno: {str(e)}'
            nfe.save(update_fields=['status', 'mensagem_retorno'])
            return nfe

    @staticmethod
    @transaction.atomic
    def cancelar_nfe(nfe_id, justificativa):
        nfe = NFe.objects.select_related(
            'empresa__pessoa', 'empresa__certificado_digital'
        ).get(pk=nfe_id)
        empresa = nfe.empresa

        if nfe.status not in ('AUTORIZADO',):
            raise ValueError('Apenas NF-e autorizadas podem ser canceladas')

        if len(justificativa) < 15:
            raise ValueError('Justificativa deve ter no mínimo 15 caracteres')

        evento_xml = NFeService._gerar_xml_cancelamento(nfe, justificativa)
        evento_assinado = NFeService.assinar_xml(evento_xml, empresa)
        lote_evento = NFeService._montar_lote_evento(evento_assinado, nfe)

        urls = NFeService._get_sefaz_urls(empresa)
        try:
            response = NFeService._enviar_soap(
                urls['evento'],
                'nfeRecepcaoEvento',
                lote_evento,
                empresa,
            )
            NFeService._processar_retorno_evento(nfe, response, 'CANCELAMENTO', justificativa)
        except Exception as e:
            nfe.mensagem_retorno = f'Erro cancelamento SEFAZ: {str(e)}'
            nfe.save(update_fields=['mensagem_retorno'])
            raise

        return nfe

    @staticmethod
    def _gerar_xml_cancelamento(nfe, justificativa):
        evento = etree.Element(f'{{{NS_NFE}}}evento', attrib={'versao': '1.00'}, nsmap={None: NS_NFE})
        inf_evento = etree.SubElement(evento, f'{{{NS_NFE}}}infEvento', attrib={'Id': f'ID110111{nfe.chave_acesso}'})
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}cOrgao').text = UF_PARA_CODIGO.get(nfe.empresa.uf_web_service_nfe, nfe.empresa.uf_web_service_nfe)
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}tpAmb').text = AMBIENTE_NFE.get(nfe.empresa.ambiente_destino, '2')
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}CNPJ').text = NFeService._formatar_cnpj(nfe.empresa.pessoa.cpf_cnpj)
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}chNFe').text = nfe.chave_acesso
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}dhEvento').text = timezone.localtime(timezone.now()).isoformat(timespec='seconds')
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}tpEvento').text = '110111'
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}nSeqEvento').text = '1'
        etree.SubElement(inf_evento, f'{{{NS_NFE}}}verEvento').text = '1.00'

        det_evento = etree.SubElement(inf_evento, f'{{{NS_NFE}}}detEvento')
        etree.SubElement(det_evento, f'{{{NS_NFE}}}descEvento').text = 'Cancelamento'
        etree.SubElement(det_evento, f'{{{NS_NFE}}}nProt').text = nfe.protocolo
        etree.SubElement(det_evento, f'{{{NS_NFE}}}xJust').text = justificativa[:255]

        return etree.tostring(evento, xml_declaration=True, encoding='UTF-8')

    @staticmethod
    def _montar_lote_evento(xml_evento, nfe):
        env = etree.Element(f'{{{NS_NFE}}}envEvento', attrib={'versao': '1.00'}, nsmap={None: NS_NFE})
        id_lote = etree.SubElement(env, f'{{{NS_NFE}}}idLote')
        id_lote.text = str(nfe.pk)
        evento_parsed = etree.fromstring(xml_evento)
        env.append(evento_parsed)
        return etree.tostring(env, xml_declaration=True, encoding='UTF-8')

    @staticmethod
    def _processar_retorno_evento(nfe, response, tipo, justificativa):
        try:
            ret_xml = None
            if hasattr(response, 'nfeResultMsg'):
                ret_xml = response.nfeResultMsg
            elif isinstance(response, str):
                ret_xml = response
            elif hasattr(response, 'content'):
                ret_xml = response.content

            if ret_xml:
                root = etree.fromstring(ret_xml.encode() if isinstance(ret_xml, str) else ret_xml)
                ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                inf_evento = root.find('.//ns:infEvento', ns)
                if inf_evento is not None:
                    c_stat = inf_evento.findtext('ns:cStat', '', ns)
                    nfe.protocolo = inf_evento.findtext('ns:nProt', '', ns)
                    nfe.mensagem_retorno = inf_evento.findtext('ns:xMotivo', '', ns)

                    if c_stat == '135':
                        nfe.status = 'CANCELADO'
                        nfe.data_cancelamento = timezone.now()
                        nfe.justificativa_cancelamento = justificativa
                    nfe.xml_retorno = ret_xml if isinstance(ret_xml, str) else ret_xml.decode()
                    nfe.save(update_fields=[
                        'status', 'protocolo', 'mensagem_retorno',
                        'data_cancelamento', 'justificativa_cancelamento', 'xml_retorno'
                    ])
                    NFeEvento.objects.create(
                        nfe=nfe, tipo=tipo, justificativa=justificativa,
                        protocolo=nfe.protocolo,
                        xml_retorno=nfe.xml_retorno,
                    )
                    return
            raise ValueError('Retorno do evento não reconhecido')
        except Exception as e:
            nfe.mensagem_retorno = f'Erro ao processar retorno: {str(e)}'
            nfe.save(update_fields=['mensagem_retorno'])
            raise

    @staticmethod
    def consultar_status_sefaz(nfe_id):
        nfe = NFe.objects.select_related(
            'empresa__pessoa', 'empresa__certificado_digital'
        ).get(pk=nfe_id)
        empresa = nfe.empresa

        cons = etree.Element(f'{{{NS_NFE}}}consSitNFe', attrib={'versao': '4.00'}, nsmap={None: NS_NFE})
        etree.SubElement(cons, f'{{{NS_NFE}}}tpAmb').text = AMBIENTE_NFE.get(empresa.ambiente_destino, '2')
        etree.SubElement(cons, f'{{{NS_NFE}}}xServ').text = 'CONSULTAR'
        etree.SubElement(cons, f'{{{NS_NFE}}}chNFe').text = nfe.chave_acesso
        xml_consulta = etree.tostring(cons, xml_declaration=True, encoding='UTF-8')

        urls = NFeService._get_sefaz_urls(empresa)
        try:
            response = NFeService._enviar_soap(
                urls['consulta'],
                'nfeConsultaNF',
                xml_consulta,
                empresa,
            )
            ret_xml = None
            if hasattr(response, 'nfeResultMsg'):
                ret_xml = response.nfeResultMsg
            elif isinstance(response, str):
                ret_xml = response

            if ret_xml:
                root = etree.fromstring(ret_xml.encode() if isinstance(ret_xml, str) else ret_xml)
                ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                prot = root.find('.//ns:protNFe', ns)
                if prot is not None:
                    inf_prot = prot.find('ns:infProt', ns)
                    if inf_prot is not None:
                        return {
                            'cStat': inf_prot.findtext('ns:cStat', '', ns),
                            'xMotivo': inf_prot.findtext('ns:xMotivo', '', ns),
                            'nProt': inf_prot.findtext('ns:nProt', '', ns),
                        }
            return {'cStat': '999', 'xMotivo': 'Retorno não reconhecido'}
        except Exception as e:
            return {'cStat': '999', 'xMotivo': f'Erro comunicação: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def enviar_lote():
        notas = NFe.objects.filter(status='VALIDADO', lote__isnull=True)
        if not notas:
            raise ValueError('Nenhuma NF-e pendente de envio')

        empresa = notas.first().empresa
        lote = LoteNFe.objects.create(
            empresa=empresa,
            numero_lote=int(datetime.now().timestamp()),
            status='DIGITACAO',
        )

        envi = etree.Element(f'{{{NS_NFE}}}enviNFe', nsmap={None: NS_NFE})
        envi.set('versao', '4.00')
        envi.append(NFeService._tag('idLote', str(lote.numero_lote)))
        envi.append(NFeService._tag('indSinc', '1'))

        for nfe in notas:
            nfe.lote = lote
            nfe.status = 'ENVIADO'
            nfe.data_envio = timezone.now()
            if not nfe.xml_enviado:
                nfe.xml_enviado = NFeService.gerar_xml_nfe(nfe).decode('utf-8')
            nfe.save(update_fields=['lote', 'status', 'data_envio', 'xml_enviado'])

            try:
                signed = NFeService.assinar_xml(nfe.xml_enviado.encode(), empresa)
                envi.append(etree.fromstring(signed))
            except Exception as e:
                nfe.status = 'REJEITADO'
                nfe.mensagem_retorno = f'Erro assinatura: {str(e)}'
                nfe.save(update_fields=['status', 'mensagem_retorno'])

        lote.status = 'ENVIADO'
        lote.save(update_fields=['status'])

        lote_xml = etree.tostring(envi, xml_declaration=True, encoding='UTF-8')
        urls = NFeService._get_sefaz_urls(empresa)
        try:
            response = NFeService._enviar_soap(
                urls['autorizacao'], 'nfeAutorizacaoLote', lote_xml, empresa
            )
            lote.xml_retorno = str(response)
            lote.save(update_fields=['xml_retorno'])
        except Exception as e:
            lote.status = 'REJEITADO'
            lote.mensagem_retorno = str(e)
            lote.save(update_fields=['status', 'mensagem_retorno'])

        return lote

    # ===================== CSC / NFC-e =====================

    @staticmethod
    def gerar_csc_nfce(nfe):
        empresa = nfe.empresa
        if not empresa.csc or not empresa.csc_id:
            raise ValueError('CSC não configurado para NFC-e')

        csc = empresa.csc
        chave = nfe.chave_acesso
        valor = f'{csc}{chave}'
        hash_sha1 = hashlib.sha1(valor.encode('utf-8')).hexdigest().upper()
        return base64.b64encode(hash_sha1.encode('utf-8')).decode('utf-8')

    # ===================== PARSE CERTIFICADO =====================

    @staticmethod
    def testar_conexao_sefaz(empresa):
        urls = NFeService._get_sefaz_urls(empresa)
        cons = etree.Element(f'{{{NS_NFE}}}consStatServ', attrib={'versao': '4.00'}, nsmap={None: NS_NFE})
        etree.SubElement(cons, f'{{{NS_NFE}}}tpAmb').text = AMBIENTE_NFE.get(empresa.ambiente_destino, '2')
        etree.SubElement(cons, f'{{{NS_NFE}}}cUF').text = str(empresa.cidade_sede.estado.codigo_ibge)
        etree.SubElement(cons, f'{{{NS_NFE}}}xServ').text = 'STATUS'
        xml_consulta = etree.tostring(cons, xml_declaration=True, encoding='UTF-8')
        try:
            response = NFeService._enviar_soap(
                urls['status'], 'nfeStatusServicoNF', xml_consulta, empresa
            )
            ret_xml = None
            if hasattr(response, 'nfeResultMsg'):
                ret_xml = response.nfeResultMsg
            elif isinstance(response, str):
                ret_xml = response
            if ret_xml:
                root = etree.fromstring(ret_xml.encode() if isinstance(ret_xml, str) else ret_xml)
                ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                cstat = root.findtext('.//ns:cStat', '', ns)
                xmotivo = root.findtext('.//ns:xMotivo', '', ns)
                if cstat != '107':
                    logger.warning('--- RESPOSTA SEFAZ (XML) ---\n%s', ret_xml[:3000])
                return {
                    'cStat': cstat,
                    'xMotivo': xmotivo if 'Erro nao' not in xmotivo.lower() else f'{xmotivo} | XML recebido: {ret_xml[:500]}',
                    'dhRecbto': root.findtext('.//ns:dhRecbto', '', ns),
                    'tMed': root.findtext('.//ns:tMed', '', ns),
                }
            return {'cStat': '999', 'xMotivo': 'Retorno não reconhecido'}
        except Exception as e:
            return {'cStat': 'ERRO', 'xMotivo': str(e)[:200]}

    @staticmethod
    def parse_certificado_pfx(arquivo_bytes, senha):
        try:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                arquivo_bytes, senha.encode('utf-8')
            )
        except Exception as e:
            raise ValueError(f'Erro ao ler certificado: {str(e)}')

        if certificate is None:
            raise ValueError('Certificado não encontrado no arquivo PFX/P12')

        not_valid_before = certificate.not_valid_before_utc
        not_valid_after = certificate.not_valid_after_utc

        cert_subject = certificate.subject
        org_name = cert_subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
        common_name = cert_subject.get_attributes_for_oid(NameOID.COMMON_NAME)

        cnpj = ''
        if org_name:
            cnpj = org_name[0].value
        elif common_name:
            import re
            match = re.search(r'\d{14}', common_name[0].value)
            if match:
                cnpj = match.group(0)

        issuer = certificate.issuer
        issuer_org = issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
        emissor = issuer_org[0].value if issuer_org else str(issuer)

        return {
            'cnpj': cnpj,
            'validade_inicio': not_valid_before.date().isoformat(),
            'validade_fim': not_valid_after.date().isoformat(),
            'emissor': emissor,
        }
