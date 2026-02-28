#!/bin/bash
set -e

echo "=== Установка VC SEO Bot ==="

# Системные зависимости
echo "[1/7] Установка зависимостей системы..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3.12-venv git curl

# Директория
echo "[2/7] Подготовка директории..."
mkdir -p /home/user
cd /home/user

# Клонировать или обновить код
echo "[3/7] Получение кода с GitHub..."
BRANCH="claude/refactor-01BvSYfTp7bVATRKbHtUH2ad"
REPO_TOKEN="${GH_TOKEN:-}"
if [ -n "$REPO_TOKEN" ]; then
  REPO="https://${REPO_TOKEN}@github.com/alexshanaevv-creator/vc-seo-bot.git"
else
  REPO="https://github.com/alexshanaevv-creator/vc-seo-bot.git"
fi

if [ -d "vc_seo_bot/.git" ]; then
  echo "  Обновление существующего проекта..."
  cd vc_seo_bot
  git fetch origin
  git checkout "$BRANCH" 2>/dev/null || true
  git pull origin "$BRANCH" 2>/dev/null || true
else
  git clone -b "$BRANCH" "$REPO" vc_seo_bot
  cd vc_seo_bot
fi

# .env файл с API-ключами
echo "[4/7] Создание .env файла..."
cat > .env << ENVEOF
ANTHROPIC_API_KEY=${ANTHROPIC_KEY:-}
VC_TOKEN=${VC_TOKEN_VAL:-}
GEMINI_API_KEY=${GEMINI_KEY:-}
PEXELS_API_KEY=${PEXELS_KEY:-}
ENVEOF

# Виртуальное окружение и зависимости
echo "[5/7] Создание venv и установка Python-библиотек..."
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install flask anthropic requests beautifulsoup4 lxml python-dotenv google-generativeai -q

# Systemd-сервис
echo "[6/7] Создание автозапуска (systemd)..."
cat > /etc/systemd/system/vc-seo-bot.service << SVCEOF
[Unit]
Description=VC SEO Bot Flask App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/user/vc_seo_bot
EnvironmentFile=/home/user/vc_seo_bot/.env
ExecStart=/home/user/vc_seo_bot/venv/bin/python /home/user/vc_seo_bot/app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/vc-seo-bot.log
StandardError=append:/var/log/vc-seo-bot.log

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable vc-seo-bot
systemctl restart vc-seo-bot

# Файрвол
echo "[7/7] Открытие порта 5000..."
ufw allow 5000/tcp 2>/dev/null && echo "  Порт 5000 открыт" || echo "  ufw не активен, пропускаем"

echo ""
echo "============================================"
echo "  ГОТОВО! Бот установлен и запущен."
echo "  Откройте в браузере: http://168.222.193.20:5000"
echo "============================================"
echo ""
echo "Статус сервиса:"
systemctl status vc-seo-bot --no-pager -l
