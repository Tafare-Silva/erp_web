"""Parser de XML de Nota Fiscal Eletrônica (NFe)."""
from lxml import etree
from decimal import Decimal
from datetime import datetime


class NFEParser:
    """Classe para fazer parse de XML de NFe."""
    
    def __init__(self, xml_string):
        """Inicializar parser com string XML."""
        self.xml_string = xml_string
        self.root = None
        self.namespace = None
        self._parse_xml()
    
    def _parse_xml(self):
        """Parse do XML e identificação do namespace."""
        try:
            # Limpar o XML (remover BOM, espaços, etc)
            xml_clean = self.xml_string.strip()
            
            # Remover BOM se existir
            if xml_clean.startswith('\ufeff'):
                xml_clean = xml_clean[1:]
            
            # Verificar se tem conteúdo
            if not xml_clean:
                raise ValueError("XML vazio após limpeza")
            
            # Parse do XML
            self.root = etree.fromstring(xml_clean.encode('utf-8'))
            
            # NFe usa namespace, precisamos identificar
            self.namespace = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Verificar se tem namespace diferente
            if self.root.tag.startswith('{'):
                ns = self.root.tag[1:self.root.tag.index('}')]
                self.namespace = {'nfe': ns}
        except etree.XMLSyntaxError as e:
            raise ValueError(f"XML inválido: {str(e)}")
        except Exception as e:
            raise ValueError(f"Erro ao fazer parse do XML: {str(e)}")
    
    def _get_text(self, element, xpath, default=''):
        """Obter texto de um elemento pelo xpath."""
        try:
            result = element.xpath(xpath, namespaces=self.namespace)
            if result:
                return result[0].text or default
            return default
        except:
            return default
    
    def _get_decimal(self, element, xpath, default=0):
        """Obter valor decimal de um elemento."""
        try:
            text = self._get_text(element, xpath, '0')
            return Decimal(text.replace(',', '.'))
        except:
            return Decimal(default)
    
    def extrair_dados_nfe(self):
        """Extrair todos os dados da NFe."""
        try:
            # Encontrar tag NFe
            nfe = self.root.xpath('//nfe:NFe', namespaces=self.namespace)
            if not nfe:
                # Tentar sem namespace
                nfe = self.root.xpath('//NFe')
            
            if not nfe:
                raise ValueError("Tag NFe não encontrada no XML")
            
            nfe = nfe[0]
            inf_nfe = nfe.xpath('.//nfe:infNFe', namespaces=self.namespace)
            if not inf_nfe:
                inf_nfe = nfe.xpath('.//infNFe')
            
            if not inf_nfe:
                raise ValueError("Tag infNFe não encontrada")
            
            inf_nfe = inf_nfe[0]
            
            # Dados da NF
            dados = {
                'chave_nfe': inf_nfe.get('Id', '').replace('NFe', ''),
                'numero_nf': self._get_text(inf_nfe, './/nfe:ide/nfe:nNF'),
                'serie_nf': self._get_text(inf_nfe, './/nfe:ide/nfe:serie', '1'),
                'data_emissao': self._parse_data(self._get_text(inf_nfe, './/nfe:ide/nfe:dhEmi')),
                'tipo_documento': 'NFE',
                
                # Fornecedor
                'fornecedor': {
                    'cnpj': self._get_text(inf_nfe, './/nfe:emit/nfe:CNPJ'),
                    'nome': self._get_text(inf_nfe, './/nfe:emit/nfe:xNome'),
                    'fantasia': self._get_text(inf_nfe, './/nfe:emit/nfe:xFant'),
                    'ie': self._get_text(inf_nfe, './/nfe:emit/nfe:IE'),
                    # Endereço
                    'logradouro': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:xLgr'),
                    'numero': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:nro'),
                    'complemento': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:xCpl'),
                    'bairro': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:xBairro'),
                    'cidade': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:xMun'),
                    'uf': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:UF'),
                    'cep': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:CEP'),
                    'telefone': self._get_text(inf_nfe, './/nfe:emit/nfe:enderEmit/nfe:fone'),
                    'email': self._get_text(inf_nfe, './/nfe:emit/nfe:email'),
                },
                
                # Totais
                'totais': {
                    'total_produtos': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vProd'),
                    'total_desconto': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vDesc'),
                    'total_frete': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vFrete'),
                    'total_seguro': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vSeg'),
                    'total_outras': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vOutro'),
                    'total_ipi': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vIPI'),
                    'total_icms_st': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vST'),
                    'total_nf': self._get_decimal(inf_nfe, './/nfe:total/nfe:ICMSTot/nfe:vNF'),
                },
                
                # Pagamentos / Duplicatas
                'pagamentos': self._extrair_pagamentos(inf_nfe),
                
                # Itens
                'itens': self._extrair_itens(inf_nfe)
            }
            
            return dados
        
        except Exception as e:
            raise ValueError(f"Erro ao extrair dados da NFe: {str(e)}")
    
    def _extrair_pagamentos(self, inf_nfe):
        """Extrair dados de pagamento e parcelas."""
        pagamentos = []
        
        # Tentar extrair duplicatas (cobr/dup)
        dups = inf_nfe.xpath('.//nfe:cobr/nfe:dup', namespaces=self.namespace)
        if dups:
            for dup in dups:
                pagamentos.append({
                    'numero': self._get_text(dup, './/nfe:nDup'),
                    'vencimento': self._parse_data(self._get_text(dup, './/nfe:vVenc')),
                    'valor': self._get_decimal(dup, './/nfe:vDup'),
                })
        
        # Se não houver duplicatas, tentar extrair pagamentos (pag/detPag)
        if not pagamentos:
            det_pags = inf_nfe.xpath('.//nfe:pag/nfe:detPag', namespaces=self.namespace)
            for det in det_pags:
                t_pag = self._get_text(det, './/nfe:tPag')
                v_pag = self._get_decimal(det, './/nfe:vPag')
                if v_pag > 0:
                    pagamentos.append({
                        'tPag': t_pag,
                        'valor': v_pag,
                        'vencimento': self._parse_data(self._get_text(det, './/nfe:vVenc')), # Nem sempre presente
                    })
        
        return pagamentos
    
    def _extrair_itens(self, inf_nfe):
        """Extrair todos os itens da NFe."""
        itens = []
        
        # Buscar todos os items (det)
        dets = inf_nfe.xpath('.//nfe:det', namespaces=self.namespace)
        if not dets:
            dets = inf_nfe.xpath('.//det')
        
        for det in dets:
            try:
                # Produto
                prod = det.xpath('.//nfe:prod', namespaces=self.namespace)
                if not prod:
                    prod = det.xpath('.//prod')
                if not prod:
                    continue
                prod = prod[0]
                
                # Impostos
                imposto = det.xpath('.//nfe:imposto', namespaces=self.namespace)
                if not imposto:
                    imposto = det.xpath('.//imposto')
                imposto = imposto[0] if imposto else None
                
                item = {
                    'numero_item': det.get('nItem', '1'),
                    'codigo_produto': self._get_text(prod, './/nfe:cProd'),
                    'ean': self._get_text(prod, './/nfe:cEAN'),
                    'ean_trib': self._get_text(prod, './/nfe:cEANTrib'),
                    'nome_produto': self._get_text(prod, './/nfe:xProd'),
                    'ncm': self._get_text(prod, './/nfe:NCM'),
                    'cest': self._get_text(prod, './/nfe:CEST'),
                    'cfop': self._get_text(prod, './/nfe:CFOP'),
                    'unidade': self._get_text(prod, './/nfe:uCom'),
                    'unidade_trib': self._get_text(prod, './/nfe:uTrib'),
                    'quantidade': self._get_decimal(prod, './/nfe:qCom'),
                    'quantidade_trib': self._get_decimal(prod, './/nfe:qTrib'),
                    'valor_unitario': self._get_decimal(prod, './/nfe:vUnCom'),
                    'valor_unitario_trib': self._get_decimal(prod, './/nfe:vUnTrib'),
                    'valor_total': self._get_decimal(prod, './/nfe:vProd'),
                    'valor_desconto': self._get_decimal(prod, './/nfe:vDesc'),
                    'valor_frete': self._get_decimal(prod, './/nfe:vFrete'),
                    'valor_seguro': self._get_decimal(prod, './/nfe:vSeg'),
                    'valor_outras': self._get_decimal(prod, './/nfe:vOutro'),
                    'ind_total': self._get_text(prod, './/nfe:indTot', '1'),
                }
                
                # Impostos do item
                if imposto is not None:
                    item.update(self._extrair_impostos(imposto))
                
                itens.append(item)
            
            except Exception as e:
                print(f"Erro ao processar item: {str(e)}")
                continue
        
        return itens
    
    def _extrair_impostos(self, imposto):
        """Extrair impostos de um item."""
        impostos = {}

        # ICMS — suporta ICMS00, ICMS10, ICMS20, ICMS30, ICMS40, ICMS41, ICMS50,
        #         ICMS51, ICMS60, ICMS70, ICMS90, ICMSSN101, ICMSSN102, etc.
        icms = imposto.xpath('.//nfe:ICMS', namespaces=self.namespace)
        if not icms:
            icms = imposto.xpath('.//ICMS')

        if icms:
            icms = icms[0]
            for child in icms:
                cst_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                impostos['cst_icms'] = self._get_text(child, './/nfe:CST') or self._get_text(child, './/nfe:CSOSN') or cst_tag.replace('ICMS', '').replace('SN', '')
                impostos['orig_icms'] = self._get_text(child, './/nfe:orig', '0')
                impostos['bc_icms'] = self._get_decimal(child, './/nfe:vBC', 0)
                impostos['aliq_icms'] = self._get_decimal(child, './/nfe:pICMS', 0)
                impostos['valor_icms'] = self._get_decimal(child, './/nfe:vICMS', 0)
                impostos['reducao_bc_icms'] = self._get_decimal(child, './/nfe:pRedBC', 0)
                # ICMS-ST
                impostos['bc_icms_st'] = self._get_decimal(child, './/nfe:vBCST', 0)
                impostos['aliq_icms_st'] = self._get_decimal(child, './/nfe:pICMSST', 0)
                impostos['valor_icms_st'] = self._get_decimal(child, './/nfe:vICMSST', 0)
                impostos['aliq_mva'] = self._get_decimal(child, './/nfe:pMVAST', 0)
                impostos['reducao_bc_icms_st'] = self._get_decimal(child, './/nfe:pRedBCST', 0)
                break

        # IPI — tenta IPITrib e IPINTrib
        ipi_node = None
        for tag in ('nfe:IPI/nfe:IPITrib', 'nfe:IPI/nfe:IPINT'):
            nodes = imposto.xpath(f'.//{tag}', namespaces=self.namespace)
            if not nodes:
                nodes = imposto.xpath(f'.//{tag.split(":")[-1]}')
            if nodes:
                ipi_node = nodes[0]
                break

        if ipi_node is not None:
            impostos['cst_ipi'] = self._get_text(ipi_node, './/nfe:CST')
            impostos['bc_ipi'] = self._get_decimal(ipi_node, './/nfe:vBC', 0)
            impostos['aliq_ipi'] = self._get_decimal(ipi_node, './/nfe:pIPI', 0)
            impostos['valor_ipi'] = self._get_decimal(ipi_node, './/nfe:vIPI', 0)
        else:
            impostos['cst_ipi'] = ''
            impostos['bc_ipi'] = Decimal(0)
            impostos['aliq_ipi'] = Decimal(0)
            impostos['valor_ipi'] = Decimal(0)

        # PIS — suporta PISAliq, PISQtde, PISNT, PISOutr
        impostos.update(self._extrair_pis_cofins(imposto, 'PIS', 'pis'))

        # COFINS — suporta COFINSAliq, COFINSQtde, COFINSNT, COFINSOutr
        impostos.update(self._extrair_pis_cofins(imposto, 'COFINS', 'cofins'))

        return impostos

    def _extrair_pis_cofins(self, imposto, grupo, prefixo):
        """Extrai PIS ou COFINS suportando todas as variantes da NF-e."""
        result = {
            f'cst_{prefixo}': '',
            f'bc_{prefixo}': Decimal(0),
            f'aliq_{prefixo}': Decimal(0),
            f'valor_{prefixo}': Decimal(0),
        }

        # Variantes possíveis de cada grupo
        variantes = [f'{grupo}Aliq', f'{grupo}Qtde', f'{grupo}NT', f'{grupo}Outr']
        node = None
        for variante in variantes:
            nodes = imposto.xpath(f'.//nfe:{grupo}/nfe:{variante}', namespaces=self.namespace)
            if not nodes:
                nodes = imposto.xpath(f'.//{variante}')
            if nodes:
                node = nodes[0]
                break

        if node is not None:
            result[f'cst_{prefixo}'] = self._get_text(node, './/nfe:CST')
            result[f'bc_{prefixo}'] = self._get_decimal(node, './/nfe:vBC', 0)
            result[f'aliq_{prefixo}'] = self._get_decimal(node, f'.//nfe:p{grupo}', 0)
            result[f'valor_{prefixo}'] = self._get_decimal(node, f'.//nfe:v{grupo}', 0)

        return result
    
    def _parse_data(self, data_str):
        """Converter data do formato ISO para date."""
        if not data_str:
            return datetime.now().date()
        
        try:
            # Formato: 2024-01-10T10:30:00-03:00
            if 'T' in data_str:
                data_str = data_str.split('T')[0]
            
            # Formato: 2024-01-10
            return datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            return datetime.now().date()


def validar_chave_nfe(chave):
    """Validar chave de acesso da NFe (44 dígitos)."""
    if not chave:
        return False
    
    # Remover espaços e caracteres especiais
    chave = ''.join(filter(str.isdigit, chave))
    
    # Deve ter 44 dígitos
    if len(chave) != 44:
        return False
    
    return True


def formatar_cnpj(cnpj):
    """Formatar CNPJ."""
    if not cnpj:
        return ''
    
    cnpj = ''.join(filter(str.isdigit, cnpj))
    
    if len(cnpj) == 14:
        return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'
    
    return cnpj
