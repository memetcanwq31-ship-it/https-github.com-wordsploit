# =====================================================================
# ★ ZANØX ENGINE v2026.3.0 ★ - NEXT-GEN BEHAVIORAL NETWORK MAPPER
# GELİŞTİRİCİ: ZANØX77K (PROFESÖR MEHMET) | SÜRÜM: v3.0.0
# [ 1. PARÇA: TÜM İMPORTLAR VEYA ASENKRON PORT MOTORU ]
# =====================================================================

import os
import sys
import socket
import asyncio
from datetime import datetime

# Üçüncü Parti Yeni Nesil Ağ ve Terminal Kütüphaneleri
import httpx
from colorama import Fore, Style, init
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.table import Table

# Çekirdek Terminal Yapılandırması
init(autoreset=True)
console = Console()
SISTEM_SAATI = datetime.now().strftime("%H:%M:%S")

# Küresel Renk Tanımlamaları
KIRMIZI = "[bold red]"
YESIL = "[bold green]"
MAVI = "[bold blue]"
SARI = "[bold yellow]"
MOR = "[bold magenta]"
CYAN = "[bold cyan]"
BEYAZ = "[bold white]"
RENK_BITIR = "[/]"

# =====================================================================
# 1. ASENKRON PORT VEYA SERVİS VERSİYON TARAYICI (NMAP TARZI MOTOR)
# =====================================================================

class ZanoxPortScanner:
    def __init__(self, target_host: str):
        self.host = target_host
        self.target_ports = {
            21: "FTP (File Transfer)",
            22: "SSH (Secure Shell)",
            23: "Telnet (Unencrypted)",
            25: "SMTP (Mail Server)",
            53: "DNS (Domain System)",
            80: "HTTP (Web Server)",
            110: "POP3 (Mail)",
            443: "HTTPS (Secure Web)",
            445: "SMB (File Share)",
            3306: "MySQL (Database)",
            8080: "HTTP-Alt (Admin Panel)"
        }
        self.scan_results = []
        self.firewall_active = False

    async def probe_service_version(self, port: int, desc: str):
        try:
            reader, writer = await asyncio.open_connection(self.host, port)
            writer.write(b"HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
                
            raw_data = await asyncio.wait_for(reader.read(512), timeout=3.0)
            banner = raw_data.decode('utf-8', errors='ignore').strip().replace('\n', ' ')
            banner_summary = banner[:60] if banner else "Servis Aktif (Banner Yok)"
            
            self.scan_results.append((port, desc, "[bold green]AÇIK[/bold green]", f"[cyan]{banner_summary}[/]"))
            writer.close()
            await writer.wait_closed()
        except asyncio.TimeoutError:
            self.firewall_active = True
            self.scan_results.append((port, desc, "[bold yellow]FİLTRELİ[/bold yellow]", "[dim white]Timeout[/]"))
        except Exception:
            self.scan_results.append((port, desc, "[bold red]KAPALI[/bold red]", "[dim white]---[/]"))

    async def execute_port_scan(self) -> Table:
        tasks = [self.probe_service_version(port, desc) for port, desc in self.target_ports.items()]
        await asyncio.gather(*tasks)
        
        table = Table(title=f"[ NMAP TARZI PORT VE SERVİS ANALİZİ: {self.host} ]", title_style="bold cyan", expand=True)
        table.add_column("Port", justify="center", style="yellow")
        table.add_column("Standart Servis", style="white")
        table.add_column("Durum", justify="center")
        table.add_column("Banner / Versiyon İzi (RAW)", style="magenta")
        
        for port, desc, status, ver in sorted(self.scan_results):
            table.add_row(str(port), desc, status, ver)
        return table

# =====================================================================
# 1. PARÇANIN SONU - ZİNCİRİN DEVAMINA DOĞRUDAN 2. PARÇA GELECEKTİR
# =====================================================================
# =====================================================================
# ★ ZANØX ENGINE v2026.3.0 ★ - NEXT-GEN BEHAVIORAL NETWORK MAPPER
# GELİŞTİRİCİ: ZANØX77K (PROFESÖR MEHMET) | SÜRÜM: v3.0.0
# [ 2. PARÇA: SUBDOMAIN, HTTP/WAF MOTORLARI VE ARAYÜZ YAPISI ]
# =====================================================================

# =====================================================================
# 2. ASENKRON ALT ALAN ADI KEŞİF MOTORU (SUBDOMAIN SCANNER)
# =====================================================================

class ZanoxSubdomainEngine:
    def __init__(self, domain: str):
        self.domain = domain.replace("http://", "").replace("https://", "").strip()
        self.wordlist = ["admin", "test", "dev", "api", "staging", "vpn", "mail", "db", "cpanel", "secure"]
        self.found_subs = []

    async def check_sub(self, client: httpx.AsyncClient, sub: str):
        url = f"https://{sub}.{self.domain}"
        try:
            response = await client.get(url, timeout=3.5, follow_redirects=False)
            status_color = "[bold green]" if response.status_code == 200 else "[bold yellow]"
            desc = f"{status_color}AKTİF (HTTP {response.status_code})[/]"
            
            if response.status_code == 200 and sub in ["test", "dev", "staging", "db"]:
                desc += " [bold red][!] RİSK: Sızıntı Olabilir![/]"
            self.found_subs.append((url, desc))
        except Exception:
            pass

    async def execute_sub_scan(self) -> Table:
        async with httpx.AsyncClient() as client:
            tasks = [self.check_sub(client, sub) for sub in self.wordlist]
            await asyncio.gather(*tasks)
            
        table = Table(title=f"[ SUBDOMAIN KEŞİF RAPORU: {self.domain} ]", title_style="bold magenta", expand=True)
        table.add_column("Hedef URL", style="cyan")
        table.add_column("Sistem Analiz Durumu", style="white")
        
        if self.found_subs:
            for url, desc in self.found_subs:
                table.add_row(url, desc)
        else:
            table.add_row("---", "Dışa açık hassas alt alan adı bulunamadı.")
        return table

# =====================================================================
# 3. HTTP BAŞLIK VE SUNUCU DAVRANIŞ ANALİZÖRÜ (WAF TESPİTİ)
# =====================================================================

class ZanoxHTTPAnalyzer:
    def __init__(self, target_url: str):
        self.url = target_url if target_url.startswith(("http://", "https://")) else "https://" + target_url
        self.headers_data = []
        self.waf_status = f"{YESIL}[+] TEMİZ: Belirgin Güvenlik Duvarı Koruması Yok{RENK_BITIR}"

    async def analyze_infrastructure(self) -> Table:
        headers = {"User-Agent": "Zanox-Engine-Core/2026.3"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, headers=headers, timeout=5.0, follow_redirects=True)
                for k, v in response.headers.items():
                    self.headers_data.append((k, v))
                    
                server_attr = response.headers.get("Server", "").lower()
                if "cloudflare" in server_attr or "cloudflare" in response.text.lower():
                    self.waf_status = f"{KIRMIZI}[!] TESPİT EDİLDİ: Cloudflare WAF Aktif!{RENK_BITIR}"
                elif "sucuri" in server_attr or "sucuri" in response.text.lower():
                    self.waf_status = f"{KIRMIZI}[!] TESPİT EDİLDİ: Sucuri WAF Aktif!{RENK_BITIR}"
        except Exception as e:
            self.headers_data.append(("Hata", str(e)))
            self.waf_status = f"{KIRMIZI}[─] ANALİZ EDİLEMEDİ: Sunucu İstekleri Düşürüyor{RENK_BITIR}"

        table = Table(title=f"[ ★ ZANØX SUNUCU YANIT PROTOKOLÜ: {self.url} ★ ]", title_style="bold magenta", expand=True)
        table.add_column("HTTP Protokol Başlığı", style="cyan")
        table.add_column("Dönen Değer / İmza", style="white")
        for k, v in self.headers_data:
            table.add_row(k, v)
        table.add_section()
        table.add_row("[bold]GÜVENLİK DUVARI[/bold]", self.waf_status)
        return table

# =====================================================================
# 4. ANA SİSTEM ÇEKİRDEĞİ VE BANNER/MENÜ METOTLARI
# =====================================================================

class ZanoxCore:
    def __init__(self):
        self.version = "2026.3.0"
        self.codename = "ZANØX_ENGINE"
        self.status = "ONLINE"
        self.selected_menu = "MAIN"
        self.target_host = ""

    def show_banner_and_menu(self):
        """Ekrana logoyu, yapımcı imzasını ve seçenekleri basan ana fonksiyon."""
        os.system("clear")
        saat = datetime.now().strftime("%H:%M:%S")
        
        # Devasa Kırmızı Logo ve Yapımcı Bilgisi
        logo = (
            f"{Fore.RED}███████╗ █████╗ ███╗   ██╗██╗  ██╗██╗  ██╗\n"
            f"╚══███╔╝██╔══██╗████╗  ██║██║  ██║╚██╗██╔╝\n"
            f"  ███╔╝ ███████║██╔██╗ ██║███████║ ╚███╔╝ \n"
            f"====== ★ ZANØX ENGINE ★ v{self.version} ======\n"
            f"{Fore.MAGENTA}[ YAPIMCI / SİSTEM MİMARI: ZANØX77K - PROFESÖR MEHMET ]\n"
            f"{Fore.GREEN}STATUS: {self.status} | TIME: {saat} | ENGINE: ACTIVE{Fore.RESET}"
        )
        console.print(Panel(logo, border_style="red"))
        
        # Menü Tablosu
        table = Table(show_header=False, box=None, expand=True)
        table.add_column("Idx", style="bold red")
        table.add_column("Opt", style="bold white")
        table.add_column("Dsc", style="dim cyan")
        table.add_row("1", "NMAP STYLE PORT SCAN", "[ Asenkron Servis & Versiyon Taraması ]")
        table.add_row("2", "SUBDOMAIN DISCOVERY", "[ Güvensiz Alt Alan Adı Keşif Motoru ]")
        table.add_row("3", "HTTP INFRASTRUCTURE", "[ HTTP Başlık & WAF Analizör ]")
        table.add_row("0", "SYSTEM DESTRUCT", "[ Çevrimdışı Ol ve Önbelleği İmha Et ]")
        console.print(Panel(table, border_style="blue", title="[ ENGINE OPTIONS ]"))

# =====================================================================
# 2. PARÇANIN SONU - ZİNCİRİN DEVAMINA DOĞRUDAN 3. PARÇA GELECEKTİR
# =====================================================================
# =====================================================================
# ★ ZANØX ENGINE v2026.3.0 ★ - NEXT-GEN BEHAVIORAL NETWORK MAPPER
# GELİŞTİRİCİ: ZANØX77K (PROFESÖR MEHMET) | SÜRÜM: v3.0.0
# [ 3. PARÇA: INTERAKTİF ARAYÜZ DÖNGÜSÜ VEYA BAŞLATICI ]
# =====================================================================

    async def handle_user_input(self) -> bool:
        """Kullanıcının klavye isteklerini toplar ve asenkron motorları tetikler."""
        try:
            # Her girdi öncesi ekranı ve menüyü tazele
            self.show_banner_and_menu()
            
            print(f"\n{CYAN}Zanøx Panel >> {RENK_BITIR}", end="")
            choice = await asyncio.to_thread(input)
            choice = choice.strip()

            if choice == "1":
                self.selected_menu = "PORT_SCANNER"
                print(f"{SARI}[?] Hedef IP veya Domain Adresi: {RENK_BITIR}", end="")
                self.target_host = await asyncio.to_thread(input)
                
                scanner = ZanoxPortScanner(self.target_host.strip())
                result_table = await scanner.execute_port_scan()
                console.print(Panel(result_table, border_style="cyan"))
                await asyncio.to_thread(input, f"\n{CYAN}Ana Menüye Dönmek İçin Enter'a Basın...{RENK_BITIR}")
                
            elif choice == "2":
                self.selected_menu = "SUBDOMAIN_RECON"
                print(f"{SARI}[?] Tarancak Ana Domain (Örn: google.com): {RENK_BITIR}", end="")
                self.target_host = await asyncio.to_thread(input)
                
                sub_engine = ZanoxSubdomainEngine(self.target_host.strip())
                result_table = await sub_engine.execute_sub_scan()
                console.print(Panel(result_table, border_style="magenta"))
                await asyncio.to_thread(input, f"\n{CYAN}Ana Menüye Dönmek İçin Enter'a Basın...{RENK_BITIR}")
                
            elif choice == "3":
                self.selected_menu = "HTTP_ANALYZER"
                print(f"{SARI}[?] Altyapısı İncelenecek Web URL: {RENK_BITIR}", end="")
                self.target_host = await asyncio.to_thread(input)
                
                analyzer = ZanoxHTTPAnalyzer(self.target_host.strip())
                result_table = await analyzer.analyze_infrastructure()
                console.print(Panel(result_table, border_style="magenta"))
                await asyncio.to_thread(input, f"\n{CYAN}Ana Menüye Dönmek İçin Enter'a Basın...{RENK_BITIR}")
                
            elif choice == "0":
                self.selected_menu = "EXIT"
                return False
            else:
                print(f"{KIRMIZI}[!] Geçersiz Komut Girişi.{RENK_BITIR}")
                await asyncio.sleep(1.0)
                
            self.selected_menu = "MAIN"
            return True
        except (KeyboardInterrupt, EOFError):
            return False

    async def start_interface(self):
        """Kilitlenmeyi önleyen ve ekranı sürekli basan ana döngü motoru."""
        running = True
        while running:
            running = await self.handle_user_input()


# =====================================================================
# SİSTEM KAPANIŞI VE LOG İMHA PROTOKOLÜ
# =====================================================================

def terminate_and_clean_logs():
    console.print("\n" + f"{SARI}[*] Zanøx Framework Güvenli Çıkış Protokolü Devrede...{RENK_BITIR}")
    try:
        if os.path.exists("__pycache__"):
            import shutil
            shutil.rmtree("__pycache__")
            console.print(f"{YESIL}[+] Geçici sistem önbelleği temizlendi.{RENK_BITIR}")
    except Exception:
        pass
    console.print(Panel(Text("SİSTEM ÇEVRİMDIŞI\n\n[ Profesör Zanøx77k - 2026 ]", style="bold red", justify="center"), border_style="red"))


# =====================================================================
# ANA ÇEKİRDEK BAŞLATICISI
# =====================================================================

if __name__ == "__main__":
    core_engine = ZanoxCore()
    try:
        if os.path.exists("__pycache__"):
            import shutil
            shutil.rmtree("__pycache__")
        asyncio.run(core_engine.start_interface())
        terminate_and_clean_logs()
    except KeyboardInterrupt:
        console.print(f"\n\n{KIRMIZI}[!] Acil Durum Kapatma Sinyali Tetiklendi (Ctrl+C).{RENK_BITIR}")
        terminate_and_clean_logs()
        sys.exit(0)
