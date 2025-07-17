#!/bin/bash
set -e  # Exit immediately on error

# ------------------- CONFIGURATION -------------------
APP_NAME="servesync"
APP_DIR="/var/www/$APP_NAME"
GIT_REPO="https://github.com/Zman327/Servesync"
DOMAIN="Servesync.burnside.school.nz"  # Replace with your domain or public IP
EMAIL="Happes327@gmail.com" 

# ------------------- 1. SYSTEM SETUP -------------------
echo "[+] Updating system and installing dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx

# ------------------- 2. CLONE PROJECT -------------------
echo "[+] Cloning Git repo..."
sudo rm -rf $APP_DIR  # Remove if re-running
sudo git clone $GIT_REPO $APP_DIR

# ------------------- 3. SETUP VENV & DEPENDENCIES -------------------
echo "[+] Setting up Python virtual environment..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ------------------- 4. SETUP GUNICORN SERVICE -------------------
echo "[+] Creating Gunicorn systemd service..."
sudo tee /etc/systemd/system/$APP_NAME.service > /dev/null <<EOF
[Unit]
Description=Gunicorn for $APP_NAME
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn -b localhost:8000 run:app

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start $APP_NAME
sudo systemctl enable $APP_NAME

# ------------------- 5. CONFIGURE NGINX -------------------
echo "[+] Configuring NGINX..."
sudo tee /etc/nginx/sites-available/$APP_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# ------------------- 6. SETUP SSL -------------------
echo "[+] Requesting SSL certificate from Let's Encrypt..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL

echo "[✓] Deployment successful!"
echo "Your Flask app is now live at: https://$DOMAIN"