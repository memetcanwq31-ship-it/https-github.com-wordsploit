#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MarkOS - Safe, plugin-based refactor of the original script.
This script loads safe plugins from the `tools/` directory. Plugins must define:
 - TOOL_NAME (str)
 - TOOL_DESC (str)
 - run(args: dict) -> None

Do NOT implement or install malicious tools. This framework is for legal, ethical use only.
"""

import os
import sys
import time
import importlib.util
import logging
import json
from pathlib import Path

# Safe color handling (colorama optional)
try:
    from colorama import Fore, init as colorama_init
    colorama_init(autoreset=True)
except Exception:
    class _F:
        GREEN = BLUE = YELLOW = RED = MAGENTA = RESET = ""
    Fore = _F()

YESIL   = Fore.GREEN
MAVI    = Fore.BLUE
SARI    = Fore.YELLOW
KIRMIZI = Fore.RED
MOR     = Fore.MAGENTA
NORMAL  = Fore.RESET

BASE_DIR = Path(__file__).parent.resolve()
TOOLS_DIR = BASE_DIR / "tools"
LOG_DIR = BASE_DIR / "logs"
DATA_SOURCES_FILE = BASE_DIR / "data_sources.json"

# Ensure directories
LOG_DIR.mkdir(exist_ok=True)
TOOLS_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(
    filename=LOG_DIR / "markos_safe.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def load_data_sources():
    if DATA_SOURCES_FILE.exists():
        try:
            with open(DATA_SOURCES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.exception("Failed to load data sources")
            return {}
    else:
        # default placeholder sources (no sensitive endpoints)
        return {
            "osint_sources": [],
            "passive_scanners": []
        }

DATA_SOURCES = load_data_sources()

def banner_yap():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{MOR}")
    print("         ,gPPRg,                              ,gPPRg,     ")
    print("        dP'   `Y8                             8Y'   `Yb    ")
    print("        8)     (8  _                       _  8)     (8    ")
    print("        Yb,   ,dP ( )                     ( ) Yb,   , dP   ")
    print("         `YooP'   /_\\       .---.       /_\\   `YooP'     ")
    print("                 /   \\     /     \\     /   \\               ")
    print("                |  v v|   /   @   \\   |v v  |              ")
    print("                 \\___/   |  MARKOS |   \\___/               ")
    print("                          \\_______/                        ")
    print(f"{MOR} ======================================================================")
    print("                       MARKOS (SAFE)                                ")
    print("                       SÜRÜM : 1.0                                   ")
    print(" ======================================================================\n" + NORMAL)

def find_plugins():
    """Load plugins from tools/ directory following the plugin interface."""
    plugins = []
    for py in TOOLS_DIR.glob("*.py"):
        try:
            spec = importlib.util.spec_from_file_location(py.stem, py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Validate interface
            name = getattr(mod, "TOOL_NAME", None)
            desc = getattr(mod, "TOOL_DESC", None)
            run = getattr(mod, "run", None)
            if not (isinstance(name, str) and isinstance(desc, str) and callable(run)):
                logging.warning("Plugin %s missing required attributes, skipping", py.name)
                continue
            plugins.append({
                "module": mod,
                "file": py.name,
                "name": name,
                "desc": desc,
                "run": run
            })
        except Exception:
            logging.exception("Failed to load plugin %s", py.name)
    # sort by name for stable menu
    plugins.sort(key=lambda p: p["name"].lower())
    return plugins

def menu_yap(plugins):
    print(f"{YESIL} ========= Markos X Termux (SAFE) ========================={NORMAL}")
    for idx, p in enumerate(plugins, start=1):
        print(f"{YESIL} {idx:2d}. {p['name']:<40} {SARI}{p['desc']}{NORMAL}")
    print(f"{YESIL}  0. Exit / Güvenli Çıkış{NORMAL}")
    print(f"{YESIL} ==================================================={NORMAL}")

def run_plugin(plugin):
    print(f"\n{SARI}[*] Başlatılıyor: {plugin['name']}{NORMAL}")
    try:
        # Provide only safe context: data sources and logger
        ctx = {
            "data_sources": DATA_SOURCES,
            "logger": logging.getLogger(plugin['name'])
        }
        plugin['run'](ctx)
    except Exception:
        logging.exception("Plugin %s raised an exception", plugin['name'])
        print(f"{KIRMIZI}[!] Eklenti çalışırken hata oluştu. Detaylar loglarda.{NORMAL}")
    input(f"\n{MAVI}Ana menüye dönmek için Enter'a basın...{NORMAL}")

def main_loop():
    banner_yap()
    plugins = find_plugins()
    if not plugins:
        print(f"{KIRMIZI}[!] Hiç eklenti bulunamadı. tools/ dizinine örnek eklentiler koyun.{NORMAL}")
    while True:
        menu_yap(plugins)
        try:
            secim = input(f"\n{SARI}MarkOs >> Seçiminiz (numara): {NORMAL}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{KIRMIZI}[!] Çıkış yapılıyor.{NORMAL}")
            sys.exit(0)

        if secim in ("0", "00", "exit", "quit"):
            print(f"\n{KIRMIZI}[!] MarkOs Çekirdek Sisteminden Güvenli Çıkış Yapıldı. Hoşça kalın!{NORMAL}\n")
            sys.exit(0)
        if not secim.isdigit():
            print(f"{KIRMIZI}[!] Lütfen sayı girin.{NORMAL}")
            time.sleep(0.8)
            continue
        idx = int(secim) - 1
        if 0 <= idx < len(plugins):
            run_plugin(plugins[idx])
        else:
            print(f"{KIRMIZI}[!] Geçersiz seçim.{NORMAL}")
            time.sleep(0.8)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print(f"\n\n{KIRMIZI}[!] İşlem kullanıcı tarafından iptal edildi.{NORMAL}\n")
        sys.exit(0)
