#!/bin/bash
# Установка wifi-watchdog. Запуск из папки репозитория: sudo ./install.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Запустите через sudo"; exit 1; }
cd "$(dirname "$0")"

for cmd in nmcli systemd-run python3 ping logger; do
  command -v "$cmd" >/dev/null || { echo "Не найдено: $cmd"; exit 1; }
done

# Библиотека для входа в роутер — в отдельном окружении
mkdir -p /opt/wifi-watchdog
if [ ! -x /opt/wifi-watchdog/venv/bin/python ]; then
  if command -v uv >/dev/null; then uv venv -q --python "$(command -v python3)" /opt/wifi-watchdog/venv
  else python3 -m venv /opt/wifi-watchdog/venv   # в Debian/Ubuntu нужен пакет python3-venv
  fi
fi
if command -v uv >/dev/null; then uv pip install -q --python /opt/wifi-watchdog/venv/bin/python -r requirements.txt
else /opt/wifi-watchdog/venv/bin/pip install -q -r requirements.txt
fi

install -d -m 755 /usr/local/lib/wifi-watchdog
install -d -m 700 /etc/wifi-watchdog
install -m 755 router.py /usr/local/lib/wifi-watchdog/router.py
install -m 755 wifi-watchdog wifi-watchdog-setup /usr/local/sbin/
install -m 644 wifi-watchdog.service wifi-watchdog.timer /etc/systemd/system/
[ -e /etc/wifi-watchdog/config ] || install -m 600 config.example /etc/wifi-watchdog/config
systemctl daemon-reload

cat <<'EOF'
Установлено. Дальше:
  1. Проверьте /etc/wifi-watchdog/config (IFACE — ваш Wi-Fi-адаптер, ROUTER_IP — адрес роутера).
  2. sudo wifi-watchdog-setup            — ввести пароль Wi-Fi и пароль администратора роутера
  3. sudo systemctl enable --now wifi-watchdog.timer
EOF
