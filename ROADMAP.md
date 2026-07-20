# 🗺️ Roadmap - ERP Web

## ✅ Fase 1 - Estrutura Base (Concluída)

- [x] Setup inicial do projeto Django
- [x] Configuração do banco de dados PostgreSQL
- [x] Models das tabelas principais (schema cadastros)
- [x] Interface base com Tailwind CSS
- [x] Navegação e menu
- [x] Dashboard básico
- [x] Listagem de Pessoas, Clientes, Fornecedores, Produtos
- [x] Views de detalhes

## 🚧 Fase 2 - CRUD Completo de Cadastros (Em Andamento)

### Prioridade Alta

- [ ] **Formulários de Cadastro/Edição**
  - [ ] Pessoa (com validação CPF/CNPJ)
  - [ ] Cliente (incluindo dados de Pessoa)
  - [ ] Fornecedor (incluindo dados de Pessoa)
  - [ ] Produto
  - [ ] Grupo de Produto

- [ ] **Validações e Máscaras**
  - [ ] CPF/CNPJ (validação e formatação)
  - [ ] Telefone/Celular (máscara)
  - [ ] CEP (busca automática via API)
  - [ ] Valores monetários

- [ ] **Busca de CEP**
  - [ ] Integração com API ViaCEP
  - [ ] Preenchimento automático de endereço

### Prioridade Média

- [ ] **Upload de Arquivos**
  - [ ] Logo de empresas
  - [ ] Fotos de produtos

- [ ] **Paginação**
  - [ ] Implementar paginação nas listagens
  - [ ] Configurar número de itens por página

- [ ] **Filtros Avançados**
  - [ ] Filtros por data de cadastro
  - [ ] Filtros por status (ativo/inativo)
  - [ ] Filtros por cidade/estado

- [ ] **Exportação**
  - [ ] Exportar lista para Excel
  - [ ] Exportar lista para PDF
  - [ ] Impressão de fichas cadastrais

### Prioridade Baixa

- [ ] **Histórico de Alterações**
  - [ ] Log de modificações em cadastros
  - [ ] Auditoria de ações

- [ ] **Importação em Massa**
  - [ ] Importar clientes via Excel
  - [ ] Importar produtos via Excel

## 🎯 Fase 3 - Módulo de Vendas

### A Implementar

- [ ] **Pedidos de Venda**
  - [ ] Criar novo pedido
  - [ ] Adicionar itens ao pedido
  - [ ] Calcular totais e descontos
  - [ ] Listagem de pedidos
  - [ ] Detalhes do pedido
  - [ ] Editar/Cancelar pedido

- [ ] **Orçamentos**
  - [ ] Criar orçamento
  - [ ] Converter orçamento em pedido
  - [ ] Enviar orçamento por e-mail

- [ ] **Comissões**
  - [ ] Cálculo de comissões de vendedores
  - [ ] Relatório de comissões

## 💰 Fase 4 - Módulo Financeiro

### A Implementar

- [ ] **Contas a Receber**
  - [ ] Cadastro de títulos a receber
  - [ ] Baixa de títulos
  - [ ] Renegociação de dívidas
  - [ ] Relatórios de inadimplência

- [ ] **Contas a Pagar**
  - [ ] Cadastro de títulos a pagar
  - [ ] Baixa de títulos
  - [ ] Programação de pagamentos
  - [ ] Relatório de contas a pagar

- [ ] **Fluxo de Caixa**
  - [ ] Dashboard de fluxo de caixa
  - [ ] Projeções futuras
  - [ ] Gráficos de entrada/saída

- [ ] **Conciliação Bancária**
  - [ ] Importação de extratos OFX
  - [ ] Conciliação manual
  - [ ] Relatórios de conciliação

- [ ] **Boletos Bancários**
  - [ ] Geração de boletos
  - [ ] Remessa bancária
  - [ ] Retorno bancário

## 📦 Fase 5 - Módulo de Estoque

### A Implementar

- [ ] **Movimentações**
  - [ ] Entrada de produtos
  - [ ] Saída de produtos
  - [ ] Transferência entre locais
  - [ ] Ajuste de estoque

- [ ] **Inventário**
  - [ ] Contagem de estoque
  - [ ] Relatórios de divergência
  - [ ] Ajustes de inventário

- [ ] **Controle de Lotes**
  - [ ] Rastreabilidade por lote
  - [ ] Validade de produtos

- [ ] **Locais de Estoque**
  - [ ] Cadastro de depósitos
  - [ ] Controle por local

## 📄 Fase 6 - Módulo Fiscal

### A Implementar

- [ ] **NFe (Nota Fiscal Eletrônica)**
  - [ ] Emissão de NFe
  - [ ] Cancelamento de NFe
  - [ ] Carta de Correção
  - [ ] Download de XML
  - [ ] Envio de e-mail com NFe

- [ ] **NFCe (Nota Fiscal Consumidor)**
  - [ ] Emissão de NFCe
  - [ ] Cancelamento de NFCe
  - [ ] Contingência offline

- [ ] **SPED Fiscal**
  - [ ] Geração de arquivos SPED
  - [ ] Validação de registros

## 📊 Fase 7 - Relatórios e Dashboards

### A Implementar

- [ ] **Dashboard Principal**
  - [ ] Gráficos de vendas
  - [ ] Indicadores financeiros
  - [ ] Alertas de estoque
  - [ ] Top produtos/clientes

- [ ] **Relatórios Gerenciais**
  - [ ] Vendas por período
  - [ ] Vendas por vendedor
  - [ ] Vendas por produto
  - [ ] Lucratividade
  - [ ] Curva ABC

- [ ] **Relatórios Fiscais**
  - [ ] Livro registro de entradas
  - [ ] Livro registro de saídas
  - [ ] Apuração de ICMS

## 🔐 Fase 8 - Segurança e Permissões

### A Implementar

- [ ] **Sistema de Permissões**
  - [ ] Grupos de usuários
  - [ ] Permissões por módulo
  - [ ] Permissões por ação (criar, editar, excluir)

- [ ] **Auditoria**
  - [ ] Log completo de ações
  - [ ] Histórico de alterações por registro
  - [ ] Relatório de auditoria

- [ ] **Segurança**
  - [ ] Autenticação de dois fatores
  - [ ] Política de senhas
  - [ ] Timeout de sessão

## 📱 Fase 9 - Integração com App Mobile

### A Implementar

- [ ] **API REST**
  - [ ] Endpoints para vendas
  - [ ] Endpoints para consultas
  - [ ] Autenticação JWT

- [ ] **Sincronização**
  - [ ] Sincronização de dados offline
  - [ ] Resolução de conflitos

## 🚀 Fase 10 - Otimizações e Deploy

### A Implementar

- [ ] **Performance**
  - [ ] Cache de queries frequentes
  - [ ] Otimização de consultas SQL
  - [ ] Lazy loading de dados

- [ ] **Infraestrutura**
  - [ ] Configuração de servidor de produção
  - [ ] CI/CD
  - [ ] Monitoramento e logs
  - [ ] Backup automatizado

- [ ] **Documentação**
  - [ ] Manual do usuário
  - [ ] Documentação técnica
  - [ ] Vídeos tutoriais

## 💡 Melhorias Futuras

- [ ] Multi-empresa (uma instalação, várias empresas)
- [ ] Notificações em tempo real
- [ ] Chat interno para equipe
- [ ] Integração com e-commerce
- [ ] Integração com marketplaces
- [ ] BI (Business Intelligence) integrado
- [ ] App mobile nativo (iOS/Android)

## 📝 Notas Técnicas

### Tecnologias a Considerar

- **HTMX:** Já incluído, usar mais extensivamente
- **Alpine.js:** Para interatividade sem React
- **Chart.js:** Para gráficos no dashboard
- **DataTables:** Para tabelas avançadas
- **Select2:** Para selects mais amigáveis
- **Celery:** Para tarefas assíncronas (e-mails, relatórios)
- **Redis:** Para cache e filas
- **Docker:** Para containerização

### Padrões de Código

- Seguir PEP 8
- Usar type hints
- Documentar funções complexas
- Testes unitários para regras de negócio críticas
- Code review antes de merge

---

**Última atualização:** 03/01/2026
