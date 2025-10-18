#!/bin/bash

# Setup PostgreSQL Database for Expense Analyzer
# This script sets up the local PostgreSQL database and migrates data

set -e  # Exit on any error

echo "🚀 Setting up PostgreSQL database for Expense Analyzer"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo "✅ docker-compose is available"

# Start PostgreSQL database
echo "📡 Starting PostgreSQL database..."
docker-compose up -d postgres

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if database is ready
echo "🔍 Checking database connection..."
until docker-compose exec postgres pg_isready -U postgres -d expense_analyzer; do
    echo "⏳ Waiting for database..."
    sleep 2
done

echo "✅ Database is ready!"

# Install Python dependencies for migration
echo "📦 Installing Python dependencies..."
pip install psycopg2-binary

# Run migration script
echo "🔄 Running data migration..."
python3 scripts/migrate_to_postgres.py

# Start pgAdmin (optional)
echo "🌐 Starting pgAdmin (database management UI)..."
docker-compose up -d pgadmin

echo ""
echo "🎉 Setup completed successfully!"
echo "=================================================="
echo ""
echo "📊 Database Information:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: expense_analyzer"
echo "  User: postgres"
echo "  Password: postgres123"
echo ""
echo "🌐 pgAdmin (Database Management UI):"
echo "  URL: http://localhost:8080"
echo "  Email: admin@expense-analyzer.com"
echo "  Password: admin123"
echo ""
echo "🔧 To connect to database:"
echo "  psql -h localhost -p 5432 -U postgres -d expense_analyzer"
echo ""
echo "🛑 To stop the database:"
echo "  docker-compose down"
echo ""
echo "🔄 To restart the database:"
echo "  docker-compose up -d"
echo ""
echo "✅ Your PostgreSQL database is ready to use!"
