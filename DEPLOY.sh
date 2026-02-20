#!/bin/bash
# NAV Scoring Deployment Script (SQLite)
# Usage: bash DEPLOY.sh

set -e

echo "🚀 NAV Scoring Deployment Script"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing..."
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo usermod -aG docker $USER
    echo "✅ Docker installed. Please run: newgrp docker"
    exit 0
fi

echo "✅ Docker found"

# Prompt for configuration
echo ""
echo "📋 Configuration Setup"
echo "====================="
read -p "Enter Zoho SMTP email (or skip with blank): " ZOHO_EMAIL
read -sp "Enter Zoho SMTP password (or skip with blank): " ZOHO_PASS
echo ""

# Create .env file if provided
if [ -n "$ZOHO_EMAIL" ]; then
    cat > .env << EOF
ZOHO_SMTP_USER=$ZOHO_EMAIL
ZOHO_SMTP_PASSWORD=$ZOHO_PASS
ZOHO_SMTP_HOST=smtp.zoho.com
ZOHO_SMTP_PORT=587
EOF
    echo "✅ .env file created"
else
    echo "⚠️  Skipping .env file (email notifications disabled)"
fi

# Create docker-compose.yml for SQLite
echo ""
echo "📦 Creating docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  nav-scoring:
    build: .
    container_name: nav-scoring
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    environment:
      - DATABASE_URL=sqlite:///app/data/nav_scoring.db

volumes:
  nav_data:
EOF

echo "✅ docker-compose.yml created"

# Create data directory
echo ""
echo "📁 Creating data directory..."
mkdir -p data
echo "✅ Data directory ready"

# Build image
echo ""
echo "🔨 Building Docker image..."
docker-compose build

# Start containers
echo ""
echo "🚀 Starting NAV Scoring..."
docker-compose up -d

# Wait for health check
echo ""
echo "⏳ Waiting for app to be ready..."
sleep 5

# Check status
if docker-compose ps | grep -q "nav-scoring.*running"; then
    echo "✅ NAV Scoring is running!"
    echo ""
    echo "📍 Access at: http://localhost:8000"
    echo "🔐 Default login: admin@siu.edu / admin123"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Change default password immediately"
    echo "   2. Test flight creation and scoring"
    echo "   3. Configure Zoho SMTP in System Config if you skipped it"
    echo ""
    docker-compose logs -f nav-scoring
else
    echo "❌ Failed to start NAV Scoring"
    docker-compose logs nav-scoring
    exit 1
fi
