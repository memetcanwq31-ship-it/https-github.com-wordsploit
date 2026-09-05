#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MarkosxTermux_v26.0.py

Safe, plugin-based launcher for Markos X Termux (simulation only).
This file is a user-requested copy/name for the safe launcher. It loads
plugins from tools/ and runs them via a localhost simulation backend.

DO NOT add real attack code to plugins. This file intentionally only
loads plugins and delegates behavior to them; it's safe by design.
"""

import os
import sys
import time
import logging
import json
from pathlib import Path
import importlib.util

# colorama optional
try:
    from colorama import Fore, init as colorama_init
    colorama_init(autoreset=True)
except Exception:
    class _F:
        GREEN = BLUE = YELLOW = RED = MAGENTA = RESET = ""
    Fore = _F()

YESIL = Fore.GREEN
MAVI = Fore.BLUE
SARI = Fore.YELLOW
KIRMIZI = Fore.RED
MOR = Fore.MAGENTA
NORMAL = Fore.RESET

BASE = Path(__file__).parent.resolve()
TOOLS_DIR = BASE / "tools"
LOG_DIR = BASE / "logs"
DATA_FILE = BASE / "data_sources.json"
LOG_DIR.mkdir(exist_ok=True)
TOOLS_DIR.mkdir(exist_ok=True)

logging.basicConfig(filename=LOG_DIR / "MarkosxTermux.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("MarkosxTermux")

def load_data_sources():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except Exception:
            logger.exception("Failed to read data_sources.json")
            return {}
    return {}

DATA_SOURCES = load_data_sources()

def banner_kartal():
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
    print("                       MARKOS SÜRÜMÜ 26.0                             ")
    print("                       YAPIMCISI : markospm19_                         ")
    print(" ======================================================================\n" + NORMAL)

def find_plugins():
    plugins = []
    for py in sorted(TOOLS_DIR.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(py.stem, py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            name = getattr(mod, "TOOL_NAME", None)
            desc = getattr(mod, "TOOL_DESC", None)
            run = getattr(mod, "run", None)
            if not (isinstance(name, str) and isinstance(desc, str) and callable(run)):
                logger.warning("Skipping plugin %s: missing TOOL_NAME/TOOL_DESC/run", py.name)
                continue
            plugins.append({"file": py.name, "name": name, "desc": desc, "run": run})
        except Exception:
            logger.exception("Error loading plugin: %s", py.name)
    return plugins

def show_menu(plugins):
    print(f"{YESIL}\n ========= Markos X Termux ========================={NORMAL}")
    for i, p in enumerate(plugins, start=1):
        print(f"{YESIL} {i:2d}. {p['name']:<40} {SARI}{p['desc']}{NORMAL}")
    print(f"{YESIL}  0. Exit / Güvenli Çıkış{NORMAL}")
    print(f"{YESIL} ==================================================={NORMAL}")

def run_plugin(plugin):
    print(f"\n{SARI}[*] Başlatılıyor: {plugin['name']}{NORMAL}")
    try:
        ctx = {"data_sources": DATA_SOURCES, "logger": logger}
        plugin['run'](ctx)
    except Exception:
        logger.exception("Plugin %s failed", plugin['name'])
        print(f"{KIRMIZI}[!] Eklenti çalışırken hata oluştu. Logları kontrol edin.{NORMAL}")

def main_loop():
    banner_kartal()
    plugins = find_plugins()
    if not plugins:
        print(f"{KIRMIZI}[!] tools/ dizininde eklenti bulunamadı. Örnek eklenti ekleyin.{NORMAL}")
    while True:
        show_menu(plugins)
        try:
            choice = input(f"\n{SARI}MarkOs >> Seçiminiz (numara): {NORMAL}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{KIRMIZI}Çıkış yapılıyor.{NORMAL}")
            sys.exit(0)
        if choice in ("0", "exit", "quit"):
            print(f"\n{KIRMIZI}Güvenli çıkış.{NORMAL}")
            sys.exit(0)
        if not choice.isdigit():
            print(f"{KIRMIZI}Lütfen geçerli bir sayı girin.{NORMAL}")
            time.sleep(0.5)
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(plugins):
            run_plugin(plugins[idx])
            input(f"{MAVI}Ana menüye dönmek için Enter'a basın...{NORMAL}")
        else:
            print(f"{KIRMIZI}Geçersiz seçim.{NORMAL}")
            time.sleep(0.5)

if __name__ == '__main__':
    main_loop()
