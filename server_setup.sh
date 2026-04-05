#!/bin/bash
# Run this on the Oracle Cloud VM after SSH-ing in
set -e

echo "=== Updating system ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== Installing Docker ==="
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "=== Cloning repo ==="
cd ~
git clone https://github.com/Avazbek-A/tez-news-bot.git
cd tez-news-bot

echo "=== Create .env file ==="
read -p "Paste your BOT_TOKEN: " token
echo "BOT_TOKEN=$token" > .env

echo "=== Building and starting bot ==="
sudo docker-compose up -d --build

echo ""
echo "=== DONE! Bot is running ==="
echo "Check logs: sudo docker-compose logs -f"
echo "Restart: sudo docker-compose restart"
echo "Stop: sudo docker-compose down"
