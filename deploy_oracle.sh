#!/bin/bash
# ============================================================
#   POLARIS IA — Script de instalación en Oracle Cloud Ubuntu
#   Ejecutar como: bash deploy_oracle.sh
# ============================================================

set -e  # Parar si hay error

echo "============================================"
echo "   POLARIS IA — Deploy en Oracle Cloud"
echo "============================================"
echo ""

# ── 1. Actualizar sistema ────────────────────
echo "[1/8] Actualizando sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ── 2. Instalar Python 3.11 ──────────────────
echo "[2/8] Instalando Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo apt-get install -y git curl wget build-essential

# ── 3. Instalar Git y clonar repo ───────────
echo "[3/8] Clonando repositorio..."
cd /home/ubuntu
if [ -d "Polaris-IA" ]; then
    cd Polaris-IA && git pull && cd ..
else
    git clone https://github.com/TU_USUARIO/Polaris-IA.git
fi
cd Polaris-IA/server

# ── 4. Crear entorno virtual ─────────────────
echo "[4/8] Creando entorno virtual Python..."
python3.11 -m venv venv
source venv/bin/activate

# ── 5. Instalar dependencias ─────────────────
echo "[5/8] Instalando dependencias (puede tardar ~10 min)..."
pip install --upgrade pip
pip install -r requirements.txt

# ── 6. Crear archivo .env ────────────────────
echo "[6/8] Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
AI_API_KEY=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
AI_PROVIDER=groq
NEXT_PUBLIC_SUPABASE_URL=https://jpjvkhxittvvvacivdqn.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpwanZraHhpdHR2dnZhY2l2ZHFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxNjgyMTMsImV4cCI6MjA5MDc0NDIxM30.rebktkMdPmmX54aNn9g0d_G9CKMJWvsZQJWzK2735SU
SERPER_API_KEY=c3c93313eafd63b8eff3804a7b06b1b9bffff964
TAVILY_API_KEY=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
ELEVENLABS_API_KEY=sk_24d1e60f95bb8b10a1bbd3d187d558a979010b643f1c6a4c
LEARNING_INTERVAL_MINUTES=30
EOF
    echo "   .env creado"
else
    echo "   .env ya existe"
fi

# ── 7. Crear servicio systemd (auto-arranque) ─
echo "[7/8] Configurando servicio systemd..."
sudo tee /etc/systemd/system/polaris-ia.service > /dev/null << EOF
[Unit]
Description=Polaris IA — Red neuronal autonoma
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Polaris-IA/server
Environment=PATH=/home/ubuntu/Polaris-IA/server/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=/home/ubuntu/Polaris-IA/server/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable polaris-ia
sudo systemctl start polaris-ia

# ── 8. Abrir puerto 8000 en el firewall ──────
echo "[8/8] Configurando firewall..."
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
# Guardar reglas para que persistan tras reboot
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

echo ""
echo "============================================"
echo "   POLARIS IA CORRIENDO EN:"
echo "   http://$(curl -s ifconfig.me):8000"
echo "   http://$(curl -s ifconfig.me):8000/docs"
echo "============================================"
echo ""
echo "Comandos utiles:"
echo "  Ver logs en tiempo real:  sudo journalctl -u polaris-ia -f"
echo "  Reiniciar servicio:       sudo systemctl restart polaris-ia"
echo "  Ver estado:               sudo systemctl status polaris-ia"
