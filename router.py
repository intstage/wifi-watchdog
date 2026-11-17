#!/opt/wifi-watchdog/venv/bin/python
"""Команды роутеру TP-Link Archer C5 v4 по кабелю (веб-интерфейс, библиотека tplinkrouterc6u).
Проверено на прошивке 3.23.11 0.9.1 v6020.0 Build 200408.

router.py check         — войти, показать прошивку и число клиентов Wi-Fi
router.py wifi-restart  — выключить и включить вещание 2,4 и 5 ГГц
router.py reboot        — перезагрузить роутер
Пароль администратора — /etc/wifi-watchdog/router-password (root, 600).
"""
import os
import re
import sys
import time

from tplinkrouterc6u import Connection
from tplinkrouterc6u.client.mr200 import TPLinkMR200Client
from tplinkrouterc6u.common.exception import ClientException

HOST = os.environ.get("ROUTER_URL", "http://192.168.0.1")
PASS_FILE = os.environ.get("ROUTER_PASSWORD_FILE", "/etc/wifi-watchdog/router-password")
CLIENT_FILE = os.environ.get("ROUTER_CLIENT_FILE", "/etc/wifi-watchdog/router-client")


class ArcherC5v4Client(TPLinkMR200Client):
    """Archer C5 v4 (прошивка 2020 г.) входит как MR200: POST /cgi/login с RSA, дальше запросы /cgi с TokenID.
    Отличие: /cgi/getParm отвечает только на POST и первой строкой отдаёт userSetting, а не ключ."""

    def _get_params(self, retry=False) -> None:
        self.req.headers = {"referer": f"{self.host}/", "origin": self.host}
        try:
            text = self.req.post(f"{self.host}/cgi/getParm", timeout=8).text
            self._nn = int(re.search(r'var nn="([0-9A-Fa-f]+)"', text).group(1), 16)
            self._ee = int(re.search(r'var ee="([0-9A-Fa-f]+)"', text).group(1), 16)
        except Exception as e:
            raise ClientException(f"не получен ключ входа: {e}")


CLIENTS = {"ArcherC5v4Client": ArcherC5v4Client}


def connect():
    with open(PASS_FILE, encoding="utf-8") as f:
        password = f.read().rstrip("\r\n")
    names = list(CLIENTS)
    try:
        with open(CLIENT_FILE, encoding="utf-8") as f:
            saved = f.read().strip()
        if saved in CLIENTS:
            names = [saved]
    except FileNotFoundError:
        pass
    last = None
    for name in names:
        client = CLIENTS[name](HOST, password, timeout=20)
        try:
            client.authorize()
            return name, client
        except Exception as e:  # пробуем следующий вариант входа
            last = f"{name}: {type(e).__name__}: {e}"
    raise SystemExit(f"вход в роутер не удался — {last}")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    name, client = connect()
    try:
        if action == "check":
            fw = client.get_firmware()
            st = client.get_status()
            print(f"клиент={name}")
            print(f"модель={fw.model} прошивка={fw.firmware_version}")
            print(f"wifi_клиентов={st.wifi_clients_total} проводных={st.wired_total}")
            print(f"2.4ГГц={st.wifi_2g_enable} 5ГГц={st.wifi_5g_enable}")
        elif action == "wifi-restart":
            for band in (Connection.HOST_2G, Connection.HOST_5G):
                client.set_wifi(band, False)
            time.sleep(8)
            for band in (Connection.HOST_2G, Connection.HOST_5G):
                client.set_wifi(band, True)
            print("вещание Wi-Fi перезапущено")
        elif action == "reboot":
            client.reboot()
            print("команда перезагрузки отправлена")
            return
        else:
            raise SystemExit(f"неизвестное действие: {action}")
    finally:
        if action != "reboot":
            try:
                client.logout()
            except Exception:
                pass


if __name__ == "__main__":
    main()
