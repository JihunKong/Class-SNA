#!/bin/bash
# Class-SNA v2.0 Deployment Script for AWS EC2
# Usage: ./scripts/deploy.sh [dev|prod]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="class-sna"
ENV=${1:-prod}

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Class-SNA v2.0 Deployment Script${NC}"
echo -e "${GREEN}  Environment: ${YELLOW}$ENV${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    echo -e "${GREEN}Docker installed successfully${NC}"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file with your configuration${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p data logs docker/nginx/ssl

# Development mode
if [ "$ENV" == "dev" ]; then
    echo -e "${GREEN}Starting development server...${NC}"

    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    # Run Flask development server
    export FLASK_ENV=development
    python wsgi.py
    exit 0
fi

# Production mode with Docker
echo -e "${GREEN}Building Docker images...${NC}"
cd docker
docker-compose build --no-cache

echo -e "${GREEN}Stopping existing containers...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true

echo -e "${GREEN}Starting containers...${NC}"
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Health check
echo -e "${GREEN}Running health checks...${NC}"
if curl -s http://localhost:5000/health > /dev/null; then
    echo -e "${GREEN}Flask app is healthy${NC}"
else
    echo -e "${RED}Flask app health check failed${NC}"
    docker-compose logs web
fi

# Check Redis
if docker exec ${APP_NAME}-redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}Redis is healthy${NC}"
else
    echo -e "${RED}Redis health check failed${NC}"
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Access your application:"
echo "  - HTTP:  http://localhost:8080"
echo "  - HTTPS: https://localhost (requires SSL setup)"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop:      docker-compose down"
echo "  - Restart:   docker-compose restart"
echo ""
