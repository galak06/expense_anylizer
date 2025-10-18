#!/bin/bash

# Environment Configuration Script
# This script helps you switch between different database environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 [local|production|sqlite]"
    echo ""
    echo "Environment options:"
    echo "  local      - Use local PostgreSQL database (Docker)"
    echo "  production - Use external PostgreSQL database (Supabase, etc.)"
    echo "  sqlite     - Use SQLite database (fallback)"
    echo ""
    echo "Examples:"
    echo "  $0 local      # Switch to local PostgreSQL"
    echo "  $0 production # Switch to production PostgreSQL"
    echo "  $0 sqlite     # Switch to SQLite"
}

# Function to set environment
set_environment() {
    local env=$1
    local config_file="config.${env}.env"
    
    if [ ! -f "$config_file" ]; then
        echo -e "${RED}❌ Configuration file not found: $config_file${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}🔄 Switching to $env environment...${NC}"
    
    # Copy the environment-specific config to .env
    cp "$config_file" .env
    
    echo -e "${GREEN}✅ Environment switched to: $env${NC}"
    echo ""
    echo -e "${YELLOW}📋 Current configuration:${NC}"
    
    # Display relevant settings
    echo "Database Type: $(grep '^DATABASE_TYPE=' .env | cut -d'=' -f2)"
    echo "Database URL: $(grep '^DATABASE_URL=' .env | cut -d'=' -f2 | head -c 50)..."
    echo "Environment: $(grep '^ENVIRONMENT=' .env | cut -d'=' -f2)"
    echo "Debug Mode: $(grep '^DEBUG=' .env | cut -d'=' -f2)"
    echo ""
    
    # Provide next steps based on environment
    case $env in
        "local")
            echo -e "${YELLOW}🚀 Next steps for local environment:${NC}"
            echo "1. Start PostgreSQL: docker-compose up -d postgres"
            echo "2. Start pgAdmin: docker-compose up -d pgadmin"
            echo "3. Run your application"
            echo ""
            echo "🌐 Access pgAdmin at: http://localhost:8080"
            echo "   Email: admin@expense-analyzer.com"
            echo "   Password: admin123"
            ;;
        "production")
            echo -e "${YELLOW}🚀 Next steps for production environment:${NC}"
            echo "1. Update DATABASE_URL in .env with your production database"
            echo "2. Set your OPENAI_API_KEY in .env"
            echo "3. Set your SECRET_KEY in .env"
            echo "4. Deploy to your hosting platform"
            ;;
        "sqlite")
            echo -e "${YELLOW}🚀 Next steps for SQLite environment:${NC}"
            echo "1. Ensure data/ directory exists"
            echo "2. Run your application (no database setup needed)"
            echo ""
            echo "ℹ️  SQLite database will be created automatically"
            ;;
    esac
}

# Function to show current environment
show_current() {
    if [ -f ".env" ]; then
        echo -e "${BLUE}📋 Current environment configuration:${NC}"
        echo "Database Type: $(grep '^DATABASE_TYPE=' .env | cut -d'=' -f2 2>/dev/null || echo 'Not set')"
        echo "Environment: $(grep '^ENVIRONMENT=' .env | cut -d'=' -f2 2>/dev/null || echo 'Not set')"
        echo "Debug Mode: $(grep '^DEBUG=' .env | cut -d'=' -f2 2>/dev/null || echo 'Not set')"
    else
        echo -e "${RED}❌ No .env file found${NC}"
    fi
}

# Main script logic
case "${1:-}" in
    "local"|"production"|"sqlite")
        set_environment "$1"
        ;;
    "status"|"current")
        show_current
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    "")
        echo -e "${YELLOW}🔍 Current environment status:${NC}"
        show_current
        echo ""
        usage
        ;;
    *)
        echo -e "${RED}❌ Invalid environment: $1${NC}"
        echo ""
        usage
        exit 1
        ;;
esac
