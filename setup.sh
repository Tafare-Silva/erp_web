#!/bin/bash

# Script de setup inicial do ERP Web
echo "🚀 Configurando ERP Web..."

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado. Por favor, instale Python 3.10 ou superior.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python encontrado: $(python3 --version)${NC}"

# Criar ambiente virtual
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Criando ambiente virtual...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Ambiente virtual criado${NC}"
else
    echo -e "${YELLOW}⚠️  Ambiente virtual já existe${NC}"
fi

# Ativar ambiente virtual
echo -e "${YELLOW}🔄 Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Instalar dependências
echo -e "${YELLOW}📥 Instalando dependências...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependências instaladas${NC}"

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Criando arquivo .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Arquivo .env criado${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANTE: Configure o arquivo .env com suas credenciais do banco de dados!${NC}"
else
    echo -e "${YELLOW}⚠️  Arquivo .env já existe${NC}"
fi

# Executar migrações
echo -e "${YELLOW}🗃️  Executando migrações do Django...${NC}"
python manage.py migrate
echo -e "${GREEN}✅ Migrações concluídas${NC}"

# Criar superusuário
echo -e "${YELLOW}👤 Deseja criar um superusuário? (s/n)${NC}"
read -r response
if [[ "$response" =~ ^([sS][iI][mM]|[sS])$ ]]; then
    python manage.py createsuperuser
fi

echo ""
echo -e "${GREEN}🎉 Setup concluído!${NC}"
echo ""
echo -e "${YELLOW}Para iniciar o servidor:${NC}"
echo "  1. Ative o ambiente virtual: source venv/bin/activate"
echo "  2. Execute: python manage.py runserver"
echo "  3. Acesse: http://localhost:8000"
echo ""
echo -e "${YELLOW}📝 Não esqueça de configurar o arquivo .env com suas credenciais!${NC}"
