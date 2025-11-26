#!/bin/bash
# Class-SNA v2.0 SSL Certificate Setup Script
# Uses Let's Encrypt with Certbot for free SSL certificates
# Usage: ./scripts/ssl-setup.sh your-domain.com your@email.com

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo -e "${RED}Usage: ./scripts/ssl-setup.sh <domain> <email>${NC}"
    echo "Example: ./scripts/ssl-setup.sh class-sna.example.com admin@example.com"
    exit 1
fi

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  SSL Certificate Setup${NC}"
echo -e "${GREEN}  Domain: ${YELLOW}$DOMAIN${NC}"
echo -e "${GREEN}======================================${NC}"

# Install Certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Create SSL directory
SSL_DIR="./docker/nginx/ssl"
mkdir -p $SSL_DIR

# Stop nginx temporarily to free port 80
echo "Stopping Nginx container..."
cd docker
docker-compose stop nginx 2>/dev/null || true
cd ..

# Obtain certificate
echo -e "${GREEN}Obtaining SSL certificate...${NC}"
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    -d $DOMAIN

# Copy certificates to Docker volume location
echo "Copying certificates..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $SSL_DIR/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $SSL_DIR/
sudo chown $(whoami):$(whoami) $SSL_DIR/*.pem
chmod 644 $SSL_DIR/*.pem

# Update .env with domain
if grep -q "DOMAIN=" .env; then
    sed -i "s/DOMAIN=.*/DOMAIN=$DOMAIN/" .env
else
    echo "DOMAIN=$DOMAIN" >> .env
fi

# Restart nginx
echo "Restarting Nginx..."
cd docker
docker-compose up -d nginx
cd ..

# Setup auto-renewal cron job
echo "Setting up auto-renewal..."
CRON_CMD="0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/*.pem $SSL_DIR/ && docker-compose -f $(pwd)/docker/docker-compose.yml restart nginx"
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_CMD") | crontab -

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  SSL Setup Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Your site is now accessible at:"
echo "  https://$DOMAIN"
echo ""
echo "Certificate auto-renewal is configured to run daily at 3 AM."
echo ""
echo "Manual renewal command:"
echo "  sudo certbot renew"
echo ""
