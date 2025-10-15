#!/bin/bash
# SSL Certificate Setup Script for Expense Analyzer
# This script generates a self-signed SSL certificate for development/personal use

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Expense Analyzer - SSL Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Create SSL directory if it doesn't exist
if [ ! -d "ssl" ]; then
    echo -e "${YELLOW}Creating ssl directory...${NC}"
    mkdir -p ssl
fi

# Check if certificates already exist
if [ -f "ssl/certificate.crt" ] && [ -f "ssl/private.key" ]; then
    echo -e "${YELLOW}SSL certificates already exist!${NC}"
    read -p "Do you want to regenerate them? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Using existing certificates.${NC}"
        exit 0
    fi
    echo -e "${YELLOW}Regenerating certificates...${NC}"
fi

# Get configuration from user
echo -e "${YELLOW}SSL Certificate Configuration${NC}"
echo "Press Enter to use default values shown in [brackets]"
echo

read -p "Country Code [IL]: " COUNTRY
COUNTRY=${COUNTRY:-IL}

read -p "State/Province [Israel]: " STATE
STATE=${STATE:-Israel}

read -p "City [TelAviv]: " CITY
CITY=${CITY:-TelAviv}

read -p "Organization [Personal]: " ORG
ORG=${ORG:-Personal}

read -p "Common Name/Domain [localhost]: " CN
CN=${CN:-localhost}

read -p "Certificate validity in days [365]: " DAYS
DAYS=${DAYS:-365}

echo
echo -e "${YELLOW}Generating SSL certificate...${NC}"

# Generate self-signed certificate
openssl req -x509 -nodes -days "$DAYS" -newkey rsa:2048 \
    -keyout ssl/private.key \
    -out ssl/certificate.crt \
    -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=ExpenseAnalyzer/CN=$CN" \
    -addext "subjectAltName=DNS:$CN,DNS:*.$CN,IP:127.0.0.1" \
    2>/dev/null

# Set appropriate permissions
chmod 600 ssl/private.key
chmod 644 ssl/certificate.crt

echo
echo -e "${GREEN}✓ SSL certificate generated successfully!${NC}"
echo
echo -e "${GREEN}Certificate details:${NC}"
echo "  Location: $(pwd)/ssl/"
echo "  Certificate: ssl/certificate.crt"
echo "  Private Key: ssl/private.key"
echo "  Valid for: $DAYS days"
echo "  Common Name: $CN"
echo

# Display certificate info
echo -e "${YELLOW}Certificate Information:${NC}"
openssl x509 -in ssl/certificate.crt -noout -subject -issuer -dates

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "1. Start the application with HTTPS:"
echo -e "   ${YELLOW}docker-compose down && docker-compose up -d${NC}"
echo
echo "2. Access the application:"
echo -e "   ${YELLOW}https://localhost${NC}"
echo
echo "3. Your browser will show a security warning (self-signed cert)"
echo "   - Chrome: Click 'Advanced' → 'Proceed to localhost'"
echo "   - Firefox: Click 'Advanced' → 'Accept the Risk'"
echo "   - Safari: Click 'Show Details' → 'visit this website'"
echo
echo -e "${YELLOW}Note: For production, use a certificate from a trusted CA like Let's Encrypt${NC}"
echo

# Update .gitignore to exclude private key
if [ -f ".gitignore" ]; then
    if ! grep -q "ssl/private.key" .gitignore; then
        echo "ssl/private.key" >> .gitignore
        echo -e "${GREEN}✓ Added ssl/private.key to .gitignore${NC}"
    fi
else
    echo "ssl/private.key" > .gitignore
    echo -e "${GREEN}✓ Created .gitignore with ssl/private.key${NC}"
fi

echo -e "${GREEN}Setup complete!${NC}"
