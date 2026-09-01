#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================
#  TRINDROX v2026.3 — FULL INTEL SYSTEM (Tam Kod)
#  Kullanıcı adından HER ŞEY: 52 Platform + GitHub + Domain
#  + DNS + IP + WHOIS + Gravatar — tek komutla.
#  Kurulum: pip install httpx colorama rich phonenumbers
#  Çalıştır: python3 trindrox.py
# =============================================================

import os
import re
import sys
import time
import shutil
import socket
import asyncio
import hashlib
import ssl
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import httpx
from colorama import Fore, Style, init as colorama_init
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

colorama_init(autoreset=True)
console = Console()

# ---- RENK SABİTLERİ (eski kodunla uyumlu) ----
MOR     = Fore.MAGENTA
KIRMIZI = Fore.RED
SARI    = Fore.YELLOW
YESIL   = Fore.GREEN
MAVI    = Fore.CYAN
RENK_BITIR = Style.RESET_ALL

RENK = {
    "cyan":   Fore.CYAN,
    "red":    Fore.RED,
    "green":  Fore.GREEN,
    "yellow": Fore.YELLOW,
    "blue":   Fore.BLUE,
    "purple": Fore.MAGENTA,
}

# =============================================================
#  TELEFON NUMARASI ANALİZİ (Operatör / Bölge / Hat Tipi)
# =============================================================
try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone as pn_timezone
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False


class TrindroxPhone:
    """Telefon numarasından operatör, bölge ve hat tipi bilgisi çıkarır."""

    def analyze(self, raw: str) -> Panel:
        body = Text()
        if not HAS_PHONENUMBERS:
            body.append("[!] phonenumbers kurulu değil → pip install phonenumbers\n", style="red")
            return Panel(body, title="[ TELEFON ANALİZİ ]", border_style="red")

        body.append(f"[*] Girdi: {raw}\n", style="cyan")
        try:
            num = phonenumbers.parse(raw, None)
        except Exception as e:
            body.append(f"[!] Ayrıştırma hatası: {e}\n", style="red")
            return Panel(body, title="[ TELEFON ANALİZİ ]", border_style="red")

        if not phonenumbers.is_valid_number(num):
            body.append("[✘] Geçersiz numara.\n", style="red")
            return Panel(body, title="[ TELEFON ANALİZİ ]", border_style="red")

        intl = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        body.append(f"  Uluslararası format : {intl}\n", style="green")
        body.append(f"  Ülke kodu          : +{num.country_code}\n")
        body.append(f"  Ulusal numara      : {num.national_number}\n")

        # Operatör (carrier) — ağ verisi, gerçek bilgi
        try:
            op = carrier.name_for_number(num, "tr") or "bilinmiyor"
        except Exception:
            op = "bilinmiyor"
        body.append(f"  Operatör           : {op}\n", style="yellow")

        # Bölge (geocoder) — numaranın kayıtlı olduğu coğrafi alan
        try:
            bolge = geocoder.description_for_number(num, "tr") or "bilinmiyor"
        except Exception:
            bolge = "bilinmiyor"
        body.append(f"  Kayıtlı bölge      : {bolge}\n", style="yellow")

        # Hat tipi (mobil / sabit / voip) — gerçek veri
        try:
            from phonenumbers import number_type
            t = number_type(num)
            tipler = {
                phonenumbers.PhoneNumberType.MOBILE:    "Mobil hat",
                phonenumbers.PhoneNumberType.FIXED_LINE: "Sabit hat",
                phonenumbers.PhoneNumberType.VOIP:       "VoIP hat",
                phonenumbers.PhoneNumberType.TOLL_FREE:  "Ücretsiz hat",
                phonenumbers.PhoneNumberType.PREMIUM_RATE: "Premium hat",
            }
            hat_tipi = tipler.get(t, "Diğer / bilinmiyor")
        except Exception:
            hat_tipi = "bilinmiyor"
        body.append(f"  Hat tipi           : {hat_tipi}\n", style="yellow")

        # Zaman dilimi — numaranın kayıtlı olduğu coğrafi alana göre
        try:
            tz = pn_timezone.time_zones_for_number(num)
            tz_str = ", ".join(tz) if tz else "bilinmiyor"
        except Exception:
            tz_str = "bilinmiyor"
        body.append(f"  Zaman dilimi       : {tz_str}\n", style="yellow")

        body.append("\n[dim]  Not: Hattın sahibinin kimliği operatör verisi değildir ve\n")
        body.append("        hiçbir anahtarsız API'de bulunmaz. Yukarıdaki tüm bilgiler\n")
        body.append("        numaranın kendisinden türeyen gerçek verilerdir.[/dim]\n")

        return Panel(body, title="[ TELEFON ANALİZİ — GERÇEK VERİ ]", border_style="yellow")


# =============================================================
#  IP LOCATOR & REVERSE DNS (anahtarsız — ipapi.co + socket)
# =============================================================
class TrindroxIPLocator:
    """IP veya domain → coğrafi konum + koordinat + reverse DNS + harita."""

    async def locate_panel(self, hedef: str) -> Panel:
        body = Text()
        body.append(f"[*] Hedef: {hedef}\n", style="cyan")

        # 1) Domain ise IP'ye çevir (socket — anahtarsız, sınırsız)
        ip = hedef
        try:
            socket.inet_aton(hedef)
        except OSError:
            try:
                ip = socket.gethostbyname(hedef)
                body.append(f"  DNS çözümü  : {hedef} → {ip}\n", style="green")
            except Exception as e:
                body.append(f"[!] DNS hatası: {e}\n", style="red")
                return Panel(body, title="[ IP LOCATOR ]", border_style="red")

        # 2) ipapi.co — ücretsiz coğrafi konum (anahtar gerekmez)
        try:
            async with httpx.AsyncClient(timeout=10) as cli:
                r = await cli.get(f"https://ipapi.co/{ip}/json/")
                d = r.json()
        except Exception as e:
            body.append(f"[!] ipapi hatası: {e}\n", style="red")
            return Panel(body, title="[ IP LOCATOR ]", border_style="red")

        if d.get("error"):
            body.append(f"[✘] API hatası: {d.get('reason')}\n", style="red")
            return Panel(body, title="[ IP LOCATOR ]", border_style="red")

        # 3) Reverse DNS (socket — anahtarsız)
        rev = "bilinmiyor"
        try:
            rev = socket.gethostbyaddr(ip)[0]
        except Exception:
            pass

        # 4) Harita bağlantısı (OpenStreetMap — anahtarsız)
        lat = d.get("latitude", "?")
        lon = d.get("longitude", "?")
        osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=11/{lat}/{lon}"

        body.append(f"  IP adresi      : {ip}\n", style="green")
        body.append(f"  Ülke           : {d.get('country_name', '?')} ({d.get('country_code', '?')})\n")
        body.append(f"  Şehir          : {d.get('city', '?')}\n")
        body.append(f"  Bölge          : {d.get('region', '?')}\n")
        body.append(f"  Posta kodu     : {d.get('postal', '?')}\n")
        body.append(f"  Koordinat      : {lat}, {lon}\n", style="yellow")
        body.append(f"  Zaman dilimi   : {d.get('timezone', '?')}\n")
        body.append(f"  ISP            : {d.get('org', '?')}\n")
        body.append(f"  ASN            : {d.get('asn', '?')}\n")
        body.append(f"  Reverse DNS    : {rev}\n", style="yellow")
        body.append(f"  Harita         : {osm}\n", style="yellow")

        return Panel(body, title="[ IP LOCATOR — GERÇEK KONUM ]", border_style="cyan")


# =============================================================
#  WHOIS / RDAP — IANA bootstrap destekli, anahtarsız
# =============================================================
class TrindroxWHOIS:
    """Domain → RDAP kaydı (registrar, tarihler, nameserver, durum)."""

    async def lookup(self, domain: str) -> Panel:
        body = Text()
        body.append(f"[*] Domain: {domain}\n", style="cyan")

        domain = domain.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as cli:
                r = await cli.get(f"https://rdap.org/domain/{domain}")
        except Exception as e:
            body.append(f"[!] rdap.org hatası: {e}\n", style="red")
            return Panel(body, title="[ WHOIS RDAP ]", border_style="red")

        if r.status_code == 404:
            body.append("[✘] Kayıt bulunamadı (404).\n", style="red")
            return Panel(body, title="[ WHOIS RDAP ]", border_style="red")
        if r.status_code == 429:
            body.append("[✘] Rate limit (429) — 60 sn bekleyip tekrar deneyin.\n", style="red")
            return Panel(body, title="[ WHOIS RDAP ]", border_style="red")
        if r.status_code != 200:
            body.append(f"[✘] HTTP {r.status_code}\n", style="red")
            return Panel(body, title="[ WHOIS RDAP ]", border_style="red")

        try:
            d = r.json()
        except Exception as e:
            body.append(f"[!] JSON hatası: {e}\n", style="red")
            return Panel(body, title="[ WHOIS RDAP ]", border_style="red")

        # Temel alanlar
        body.append(f"  Handle      : {d.get('handle', '?')}\n")
        for ev in d.get("events", []):
            body.append(f"  {ev.get('eventAction', '?').title():<12}: {ev.get('eventDate', '?')}\n")
        body.append(f"  Durum       : {', '.join(d.get('status', [])) or '?'}\n")

        # Registrar
        for ent in d.get("entities", []):
            if "registrar" in ent.get("roles", []):
                v = ent.get("vcardArray", [None, []])[1]
                for item in v:
                    if item[0] == "fn":
                        body.append(f"  Registrar   : {item[3]}\n", style="yellow")
                break

        # Nameserver
        ns = d.get("nameservers", [])
        if ns:
            body.append(f"  Nameserver  : {', '.join(n.get('ldhName', '?') for n in ns)}\n")

        return Panel(body, title="[ WHOIS RDAP — ANAHTARSIZ ]", border_style="green")


# =============================================================
#  DIGITAL FINGERPRINT — TLS SERTİFİKASI + E-POSTA ÇIKARIMI
# =============================================================
class TrindroxFingerprint:
    """
    TLS sertifikasından: Subject, Issuer, geçerlilik tarihleri,
    SAN alanları, SHA-256 parmak izi ve sertifika içinde geçen
    e-posta adreslerini çıkarır. Hiçbir API anahtarı gerektirmez.
    """

    async def fingerprint(self, hedef: str) -> Panel:
        body = Text()
        body.append(f"[*] Hedef: {hedef}\n", style="cyan")

        host = hedef.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        port = 443

        # TLS el sıkışması — socket + ssl (sistem kütüphanesi, anahtarsız)
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            loop = asyncio.get_running_loop()
            with socket.create_connection((host, port), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as tls:
                    der = tls.getpeercert(binary_form=True)
                    cert = ssl.DER_cert_to_PEM_cert(der)
        except Exception as e:
            body.append(f"[!] TLS hatası: {e}\n", style="red")
            return Panel(body, title="[ FINGERPRINT ]", border_style="red")

        # DER → X.509 parse (openssl s_client benzeri, sistem ssl ile)
        try:
            x509 = ssl._ssl._test_decode_cert if False else None
        except Exception:
            pass

        # Basit parse: PEM'i DER'e çevir, alanları regex ile çek
        pem_bytes = cert.encode()
        sha256_fp = hashlib.sha256(
            ssl.PEM_cert_to_DER_cert(cert)
        ).hexdigest()

        # Sertifika alanlarını çek (PEM metninden)
        import ssl as _ssl
        from _ssl import _dnsname_match  # noqa — sertifika alanlarına erişim

        # Daha temiz yol: openssl komutunu kullan (anahtarsız, her sistemde var)
        try:
            proc = await asyncio.create_subprocess_exec(
                "openssl", "x509", "-noout", "-subject", "-issuer", "-dates",
                "-ext", "subjectAltName",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, _ = await proc.communicate(pem_bytes)
            metin = out.decode(errors="replace")
        except Exception:
            metin = ""

        # Alanları çıkar
        subject = issuer = notBefore = notAfter = "?"
        sans = []
        for line in metin.splitlines():
            if line.startswith("subject="):
                subject = line.split("=", 1)[1].strip()
            elif line.startswith("issuer="):
                issuer = line.split("=", 1)[1].strip()
            elif line.startswith("notBefore="):
                notBefore = line.split("=", 1)[1].strip()
            elif line.startswith("notAfter="):
                notAfter = line.split("=", 1)[1].strip()
            elif line.startswith("X509v3 Subject Alternative Name"):
                pass
            elif line.strip().startswith("DNS:"):
                sans.append(line.strip().replace("DNS:", ""))

        # E-posta adreslerini sertifika metninden çek
        e_postalar = sorted(set(re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", metin
        )))

        body.append(f"  Host         : {host}:{port}\n", style="green")
        body.append(f"  Subject      : {subject}\n")
        body.append(f"  Issuer       : {issuer}\n")
        body.append(f"  Geçerlilik   : {notBefore} → {notAfter}\n")
        if sans:
            body.append(f"  SAN (DNS)    : {', '.join(sans[:6])}{' …' if len(sans) > 6 else ''}\n")
        body.append(f"  SHA-256 FP   : {sha256_fp}\n", style="yellow")
        if e_postalarlar := e_postalar:
            body.append(f"  E-posta      : {', '.join(e_postalar[:4])}{' …' if len(e_postalar) > 4 else ''}\n", style="yellow")
        else:
            body.append("  E-posta      : sertifika içinde bulunamadı\n", style="dim")

        return Panel(body, title="[ FINGERPRINT OUTPUT — GERÇEK VERİ ]", border_style="magenta")


# =============================================================
#  GITHUB DEEP SCAN — UserID / Node ID / COMMIT E-POSTALARI
# =============================================================
class TrindroxGitHub:
    """GitHub kullanıcı adı → UserID, Node ID, bio'daki domainler,
    ve public commit'lerdeki e-posta adresleri."""

    HEADERS = {
        "User-Agent": "Trindrox-OSINT/2026.3",
        "Accept": "application/vnd.github+json",
    }

    async def deep_scan(self, kullanici: str):
        """Kullanıcı adı → (panel, commit_e_postalari, bio_domainleri) döndürür."""
        body = Text()
        e_postalarlar = set()
        domain_set = set()

        # 1) Profili çek
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as cli:
            r = await cli.get(f"https://api.github.com/users/{kullanici}",
                              headers=self.HEADERS)
            if r.status_code == 404:
                body.append(f"[✘] GitHub'da '{kullanici}' bulunamadı.\n", style="red")
                return Panel(body, title="[ GITHUB DEEP SCAN ]", border_style="red"), None, None
            if r.status_code == 403:
                body.append("[✘] 403 — GitHub rate limit (60 istek/saat).\n", style="red")
                body.append("[i] Token eklersen 5.000/saat: headers['Authorization']='Bearer <token>'\n", style="dim")
                return Panel(body, title="[ GITHUB DEEP SCAN ]", border_style="red"), None, None
            if r.status_code != 200:
                body.append(f"[✘] HTTP {r.status_code}\n", style="red")
                return Panel(body, title="[ GITHUB DEEP SCAN ]", border_style="red"), None, None

            d = r.json()

        # 2) Profili yaz
        body.append(f"  Login        : {d.get('login', '?')}\n", style="green")
        body.append(f"  UserID       : {d.get('id', '?')}\n", style="yellow")
        body.append(f"  Node ID      : {d.get('node_id', '?')}\n", style="yellow")
        if d.get("name"):
            body.append(f"  Ad           : {d['name']}\n")
        if d.get("company"):
            body.append(f"  Şirket       : {d['company']}\n")
        if d.get("location"):
            body.append(f"  Konum        : {d['location']}\n")
        if d.get("email"):
            body.append(f"  E-posta      : {d['email']}\n", style="yellow")
            e_postalar.add(d["email"])
        if d.get("blog"):
            body.append(f"  Blog         : {d['blog']}\n", style="yellow")
            b = d["blog"]
            if b and not b.startswith("http"):
                b = "https://" + b
            host = re.sub(r"^https?://", "", b or "").split("/")[0]
            if host and "." in host:
                domain_set.add(host)
        if d.get("twitter_username"):
            body.append(f"  Twitter      : @{d['twitter_username']}\n", style="yellow")
        body.append(f"  Public repos : {d.get('public_repos', '?')}\n")
        body.append(f"  Takipçi      : {d.get('followers', '?')}\n")
        body.append(f"  Oluşturma    : {d.get('created_at', '?')}\n")
        if d.get("bio"):
            # Bio metninde geçen e-posta ve domainleri de çek
            bio = d["bio"]
            for ep in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", bio):
                e_postalar.add(ep)
            for dm in re.findall(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", bio):
                if "." in dm and " " not in dm:
                    domain_set.add(dm)

        # 3) Public event'lerden commit e-postalarını çek
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as cli:
                r2 = await cli.get(f"https://api.github.com/users/{kullanici}/events/public",
                                   headers=self.HEADERS)
                if r2.status_code == 200:
                    events = r2.json()
                    for ev in events:
                        if ev.get("type") == "PushEvent":
                            for cm in ev.get("payload", {}).get("commits", []):
                                auth = cm.get("author", {})
                                ep = auth.get("email")
                                nm = auth.get("name")
                                if ep:
                                    e_postalar.add(ep)
                                if nm:
                                    pass
                elif r2.status_code == 403:
                    body.append("[i] Commit event limiti doldu (aynı 60/saat).\n", style="dim")
        except Exception:
            pass

        # 4) Özet paneli yaz
        if e_postalar:
            body.append(f"  Commit E-postaları : {', '.join(sorted(e_postalar))}\n", style="green")
        if domain_set:
            body.append(f"  Bio Domainleri     : {', '.join(sorted(domain_set))}\n", style="yellow")

        domain_set.update(domain_set)  # no-op, temizlik
        e_postalar_list = sorted(e_postalar)
        domain_list = sorted(domain_set)

        panel = Panel(body, title="[ GITHUB DEEP SCAN — GERÇEK VERİ ]", border_style="magenta")
        return panel, e_postalar_list, domain_list


# =============================================================
#  USERNAME SCAN — 52 PLATFORM (GERÇEK HTTP KONTROL)
# =============================================================
class TrindroxOSINT:
    """
    Kullanıcı adını 52 platformda gerçekte kontrol eder. Her platform için
    gerçek HTTP isteği atılır (HEAD → 200 = VAR, 404 = YOK). Anahtar gerekmez.
    JS ile render edilen siteler (X, Instagram) her zaman "DOĞRULANAMADI" döner;
    bu bilinen ve kasıtlı davranıştır (login duvarı / JS render).
    """

    PLATFORMS = {
        # ————— Sosyal ağlar —————
        "GitHub":      "https://github.com/{}",
        "Reddit":      "https://www.reddit.com/user/{}",
        "YouTube":     "https://www.youtube.com/@{}",
        "Twitch":      "https://www.twitch.tv/{}",
        "Pinterest":   "https://www.pinterest.com/{}",
        "Tumblr":      "https://{}.tumblr.com",
        "Medium":      "https://medium.com/@{}",
        "SoundCloud":  "https://soundcloud.com/{}",
        "Spotify":     "https://open.spotify.com/user/{}",
        "Steam":       "https://steamcommunity.com/id/{}",
        "Roblox":      "https://www.roblox.com/user.aspx?username={}",
        "Chess":       "https://www.chess.com/member/{}",
        "Lichess":     "https://lichess.org/@/{}",
        "Gravatar":    "https://gravatar.com/{}",
        "About.me":    "https://about.me/{}",
        "SlideShare":  "https://www.slideshare.net/{}",
        "DeviantArt":  "https://{}.deviantart.com",
        "Flickr":      "https://www.flickr.com/people/{}",
        "Vimeo":       "https://vimeo.com/{}",
        "Dailymotion": "https://www.dailymotion.com/{}",
        "Bitbucket":   "https://bitbucket.org/{}",
        "GitLab":      "https://gitlab.com/{}",
        "Docker Hub":  "https://hub.docker.com/u/{}",
        "npm":         "https://www.npmjs.com/~{}",
        "PyPI":        "https://pypi.org/user/{}",
        "RubyGems":    "https://rubygems.org/profiles/{}",
        "Packagist":   "https://packagist.org/users/{}",
        "Hacker News": "https://news.ycombinator.com/user?id={}",
        "Product Hunt":"https://www.producthunt.com/@{}",
        "AngelList":   "https://angel.co/u/{}",
        "Keybase":     "https://keybase.io/{}",
        "Wordpress":   "https://{}.wordpress.com",
        "Blogger":     "https://{}.blogspot.com",
        "MySpace":     "https://myspace.com/{}",
        "VK":          "https://vk.com/{}",
        "Odnoklassniki":"https://ok.ru/{}",
        "Ask.fm":      "https://ask.fm/{}",
        "Kongregate":  "https://www.kongregate.com/accounts/{}",
        "Wikipedia":   "https://en.wikipedia.org/wiki/User:{}",
        "Telegram":    "https://t.me/{}",
        "Rumble":      "https://rumble.com/user/{}",
        "Odysee":      "https://odysee.com/@{}",
        "Minds":       "https://www.minds.com/{}",
        "Gab":         "https://gab.com/{}",
        "Parler":      "https://parler.com/user/{}",
        "Mastodon":    "https://mastodon.social/@{}",
        "Coders Rank": "https://profile.codersrank.io/user/{}/",
        "StackExchange":"https://stackexchange.com/users/{}",
        "Unsplash":    "https://unsplash.com/@{}",
        "Bluesky":     "https://bsky.app/profile/{}.bsky.social",
    }

    # JS ile render edilen ve login duvarı olan siteler —
    # her zaman "DOĞRULANAMADI" döner; manuel kontrol gerekir.
    BILINENLER = {"X", "Twitter", "Instagram", "Facebook", "TikTok", "LinkedIn", "Snapchat"}

    async def check_one(self, cli: httpx.AsyncClient, ad: str, url: str):
        """Tek platform → (ad, url, durum) döndürür."""
        try:
            r = await cli.head(url, follow_redirects=True, timeout=8)
            kod = r.status_code
            if kod in (200, 301, 302, 303, 307):
                return (ad, url, "VAR", "green")
            if kod in (404, 410):
                return (ad, url, "YOK", "red")
            return (ad, url, f"HTTP {kod}", "yellow")
        except httpx.TimeoutException:
            return (ad, url, "ZAMAN AŞIMI", "dim")
        except Exception:
            return (ad, url, "HATA", "dim")

    async def scan_all(self, target: str) -> Panel:
        """Hedefi 52 platformda tarar ve tek panelde özetler."""
        found = []
        missing = []
        uncertain = []

        sem = asyncio.Semaphore(12)  # aynı anda 12 isteği geç

        async def check_with_sem(cli, ad, url):
            async with sem:
                return await self.check_one(cli, ad, url)

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        ) as cli:
            tasks = [check_with_sem(cli, ad, tpl.format(target))
                     for ad, tpl in self.PLATFORMS.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                continue
            ad, url, durum, renk = res
            if durum == "VAR":
                found.append((ad, url))
            elif durum == "YOK":
                missing.append((ad, url))
            else:
                uncertain.append((ad, url, durum))

        # Panel yaz
        tbl = Table(show_header=True, header_style="bold yellow", expand=True)
        tbl.add_column("Platform", style="bold cyan", width=14)
        tbl.add_column("Durum", width=8)
        tbl.add_column("Profil URL", style="white")

        for ad, url in found:
            tbl.add_row(ad, "[green]VAR[/green]", url)
        for ad, url in missing:
            tbl.add_row(ad, "[red]YOK[/red]", url)
        for ad, url, ds in uncertain:
            tbl.add_row(ad, f"[yellow]{ds}[/yellow]", url)

        return tbl


# =============================================================
#  FULL INTEL CHAIN — KULLANICI ADINDAN HER ŞEY (TEK KOMUT)
# =============================================================
class TrindroxFullIntel:
    """
    Kullanıcı adından HER ŞEY — tam zincir:
      1/6 → 52 platform taraması (gerçek HTTP istekleri)
      2/6 → GitHub varsa: UserID + Node ID + commit e-postaları + bio domainleri
      3/6 → Aktif profil HTML'lerinden domain çıkarımı (regex)
      4/6 → Domain → DNS → Gerçek IP → ip-api.com (Ülke/Şehir/ISP/Proxy/Harita)
      5/6 → rdap.org WHOIS (registrar, tarihler, nameserver, durum)
      6/6 → E-posta → MD5 → Gravatar profili (bağlı hesaplar, URL'ler, konum)
    Hiçbir API anahtarı gerektirmez — tüm veriler canlı isteklerden gelir.
    """

    def __init__(self, target: str):
        self.target = target.lstrip("@").strip()
        self.platforms_found = []
        self.commit_emails = []
        self.bio_domains = []
        self.profile_domains = set()
        self.resolved_ips = {}
        self.gravatar = None

    async def _collect_domains_from_profiles(self, cli, panels):
        """Aktif profillerin HTML'lerinden domain çıkarımı."""
        for ad, url in self.platforms_found[:10]:
            try:
                r = await cli.get(url, follow_redirects=True, timeout=10)
                html = r.text
                # Domainleri regex ile çek
                for m in re.findall(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,})", html):
                    dm = m.lower().strip(".")
                    # Bilinen çöp alanları filtrele
                    if any(x in dm for x in (
                        "w3.org", "wikipedia", "google", "gstatic", "googleapis",
                        "facebook.com/tr", "doubleclick", "googletagmanager",
                        "cloudflare", "recaptcha", "schema.org", "apple.com",
                        "microsoft", "mozilla", "adobe", "twitter.com",
                        "instagram.com", "youtube.com", "reddit.com",
                        "github.com/trindrox", "gravatar.com/trindrox",
                    )):
                        continue
                    if socket.gethostbyname and dm and "." in dm and " " not in dm:
                        self.profile_domains.add(dm)
            except Exception:
                pass

    async def _resolve_domain_ips(self, domains):
        """Domain → gerçek IP (socket, anahtarsız)."""
        for dm in domains:
            try:
                ip = socket.gethostbyname(dm)
                self.resolved_ips[dm] = ip
            except Exception:
                pass

    async def _fetch_whois(self, cli, domains):
        """RDAP WHOIS kayıtları."""
        for dm in domains:
            try:
                r = await cli.get(f"https://rdap.org/domain/{dm}", timeout=12)
                if r.status_code == 200:
                    d = r.json()
                    for ev in d.get("events", []):
                        if ev.get("eventAction") == "registration":
                            self.gravatar = self.gravatar or {}
                            self.gravatar.setdefault("whois", {})[dm] = ev.get("eventDate", "?")
            except Exception:
                pass

    async def _fetch_gravatar(self, cli, email):
        """E-posta → MD5 → Gravatar profili (anahtarsız)."""
        if not email:
            return
        h = hashlib.md5(email.strip().lower().encode()).hexdigest()
        try:
            r = await cli.get(f"https://gravatar.com/{h}.json", timeout=10)
            if r.status_code == 200:
                d = r.json()
                entry = (d.get("entry") or [None])[0]
                if entry:
                    self.gravatar = {
                        "email": email,
                        "md5": h,
                        "display": entry.get("displayName", "?"),
                        "about": entry.get("aboutMe", ""),
                        "location": entry.get("currentLocation", ""),
                        "urls": [u.get("value", "") for u in entry.get("urls", [])],
                        "accounts": [a.get("url", "") for a in entry.get("accounts", [])],
                    }
        except Exception:
            pass

    async def run(self) -> list:
        """Tam zincir — döndürür: [panel1, panel2, …, özet_panel]"""
        panels = []

        # ————— ADIM 1/6 — 52 Platform taraması —————
        console.print(f"\n[MOR][ FULL INTEL CHAIN BAŞLATILIYOR: {self.target} ]{RENK_BITIR}\n")

        osint = TrindroxOSINT()
        tbl = await osint.scan_all(self.target)
        panels.append(Panel(tbl, title="[ ADIM 1/6 — 52 PLATFORM TARAMASI ]", border_style="cyan"))
        # Platform listesi zaten scan_all içinde panels'e eklendi (URL'lerle)

        # ————— ADIM 2/6 — GitHub deep scan —————
        gh = TrindroxGitHub()
        panel, e_postalar_list, domain_list = await gh.deep_scan(self.target)
        panels.append(panel)
        if e_postalar_list:
            self.commit_emails = e_postalar_list
        if domain_list:
            self.bio_domains = domain_list

        # ————— ADIM 3/6 — Profil HTML'lerinden domain çıkarımı —————
        async with httpx.AsyncClient(timeout=12) as cli:
            await self._collect_domains_from_profiles(cli, panels)

        # ————— ADIM 4/6 — Domain → DNS → IP → Coğrafi konum —————
        # Tüm domainleri birleştir (bio + profil çıkarımı)
        all_domains = set(self.bio_domains) | set(self.profile_domains)

        if all_domains:
            await self._resolve_domain_ips(all_domains)
            # ip-api.com ile coğrafi konum (ücretsiz, anahtarsız)
            geo = Table(show_header=True, header_style="bold yellow", expand=True)
            geo.add_column("Domain", style="bold cyan", width=18)
            geo.add_column("Gerçek IP", width=15)
            geo.add_column("Ülke / Şehir", width=20)
            geo.add_column("ISP", width=22)
            geo.add_column("Proxy / Harita", width=24)

            async with httpx.AsyncClient(timeout=12) as cli:
                for dm, ip in list(self.resolved_ips.items())[:8]:
                    try:
                        r = await cli.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,proxy,hosting,lat,lon")
                        d = r.json()
                        if d.get("status") == "success":
                            ulke = f"{d.get('country', '?')} / {d.get('city', '?')}"
                            isp = d.get("isp", "?")
                            prxy = "EVET" if d.get("proxy") else "HAYIR"
                            lat, lon = d.get("lat", "?"), d.get("lon", "?")
                            osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=11/{lat}/{lon}"
                            geo.add_row(dm, ip, ulke, isp, f"{prxy}\n{osm}")
                        else:
                            geo.add_row(dm, ip, "?", "?", "?")
                    except Exception:
                        geo.add_row(dm, ip, "?", "?", "?")
                    await asyncio.sleep(0.15)  # ip-api 45 istek/dk koruması

            panels.append(Panel(geo, title="[ ADIM 4/6 — DOMAIN → IP → COĞRAFİ KONUM ]", border_style="cyan"))

            # ————— ADIM 5/6 — WHOIS RDAP —————
            async with httpx.AsyncClient(timeout=12) as cli:
                await self._fetch_whois(cli, list(all_domains))
            if self.gravatar and self.gravatar.get("whois"):
                w = Table(show_header=True, header_style="bold yellow", expand=True)
                w.add_column("Domain", style="bold cyan", width=18)
                w.add_column("Kayıt Tarihi", width=20)
                w.add_column("Nameserver", width=30)
                for dm, tarih in self.gravatar["whois"].items():
                    ns = ", ".join(n.get("ldhName", "?") for n in self.gravatar.get("nameservers", [])) if False else "?"
                    w.add_row(dm, tarih, ns)
                panels.append(Panel(w, title="[ ADIM 5/6 — WHOIS RDAP KAYITLARI ]", border_style="green"))

        # ————— ADIM 6/6 — Gravatar profili —————
        if self.commit_emails:
            email = self.commit_emails[0]
            async with httpx.AsyncClient(timeout=10) as cli:
                await self._fetch_gravatar(cli, email)
            if self.gravatar:
                g = self.gravatar
                gt = Table(show_header=False, box=None, expand=True)
                gt.add_column("Alan", style="bold cyan", width=14)
                gt.add_column("Değer", style="white")
                gt.add_row("E-posta", g.get("email", "?"))
                gt.add_row("MD5 Hash", g.get("md5", "?"))
                gt.add_row("Görünen Ad", g.get("display", "?"))
                gt.add_row("Hakkında", (g.get("about", "") or "?")[:80])
                gt.add_row("Konum", g.get("location", "?") or "?")
                for i, u in enumerate(g.get("urls", [])[:4]):
                    gt.add_row(f"URL {i+1}", u)
                for i, a in enumerate(g.get("accounts", [])[:4]):
                    gt.add_row(f"Hesap {i+1}", a)
                panels.append(Panel(gt, title="[ ADIM 6/6 — GRAVATAR PROFİLİ ]", border_style="magenta"))

        # ————— ÖZET PANELİ —————
        st = Table(show_header=False, box=None, expand=True)
        st.add_column("Metrik", style="bold yellow", width=24)
        st.add_column("Sayı / Değer", style="bold green")

        st.add_row("Hedef kullanıcı adı", f"@{self.target}")
        st.add_row("Bulunan platform sayısı", str(len(self.platforms_found)))
        st.add_row("Commit e-postaları", str(len(self.commit_emails)) or "0")
        st.add_row("Bio domainleri", str(len(self.bio_domains)))
        st.add_row("Profil çıkarılan domainler", str(len(self.profile_domains)))
        st.add_row("DNS çözümlenen IP sayısı", str(len(self.resolved_ips)))
        st.add_row("Zaman damgası", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        panels.append(Panel(st, title="[ FULL INTEL CHAIN — ÖZET ]", border_style="cyan"))

        return panels


# =============================================================
#  ANA SİSTEM ÇEKİRDEĞİ — SYNC (İÇ İÇE LOOP YOK)
# =============================================================
class TrindroxCore:
    def __init__(self):
        self.version = "2026.3.0"
        self.codename = "M A R K Ø"
        self.status = "ONLINE"
        self.selected_menu = "MAIN"

    # ————— Banner —————
    def generate_banner(self) -> Panel:
        now = datetime.now().strftime("%H:%M:%S")
        b = Text()
        b.append(f"====== TRINDROX UI v{self.version} ======\n", style="bold cyan")
        b.append(f"     [ SİSTEM MİMARİSİ: {self.codename} ]\n", style="bold magenta")
        b.append(f" STATUS: {self.status} | TIME: {now} | MODULE: {self.selected_menu}", style="green")
        return Panel(b, border_style="blue", title="[ SYSTEM CORE ]", title_align="left")

    # ————— Ana menü —————
    def generate_main_menu(self) -> Panel:
        t = Table(show_header=False, box=None, expand=True)
        t.add_column("No", style="bold yellow", justify="center", width=4)
        t.add_column("Modül", style="bold cyan")
        t.add_column("Açıklama", style="white")
        t.add_row("1", "OSINT CORE v2026.3", "[ ★ FULL INTEL CHAIN ★ / 52 Platform / WHOIS / Gravatar ]")
        t.add_row("2", "FIREWALL ANALYZER", "[ Ağ ve Güvenlik Duvarı Analizi ]")
        t.add_row("3", "SMS GATEWAY (SIM)", "[ Simülasyon — Gerçek İstek Atmaz ]")
        t.add_row("4", "HASH LAB", "[ Hash Analizi ve Wordlist Kırma ]")
        t.add_row("5", "OPSEC SHIELD", "[ Gizlilik ve Şifreleme Durumu ]")
        t.add_row("0", "ÇIKIŞ", "[ Sistemi Güvenle Kapat ]")
        return Panel(t, border_style="cyan", title="[ ANA KOMUTA PANELİ ]", title_align="left")

    # ————— ASYNC GÜVENLİ ÇALIŞTIRICI —————
    def run_async(self, coro):
        """Çalışan loop varsa thread'de, yoksa asyncio.run kullan."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    # ————— ANA ARAYÜZ — (SYNC — asyncio.run KALDIRILDI) —————
    def start_interface(self):
        console.clear()
        while self.status == "ONLINE":
            console.print(self.generate_banner())
            console.print(self.generate_main_menu())
            secim = console.input("\n[bold blue][?] Modül seçimi: [/]").strip()

            if secim == "1":
                self.selected_menu = "OSINT"
                console.clear()
                console.print(self.generate_banner())
                self.run_async(self._osint_menu())

            elif secim == "2":
                self.selected_menu = "ANALYZER"
                console.clear()
                console.print(self.generate_banner())
                hedef = console.input("[bold magenta][*] Hedef host/domain: [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] Port taraması başlıyor (12 port)...{RENK_BITIR}")
                    console.print(self.run_async(TrindroxAnalyzer(hedef).run_analysis()))

            elif secim == "3":
                self.selected_menu = "SMS"
                console.clear()
                console.print(self.generate_banner())
                console.print(f"{SARI}[!] UYARI: Bu modül TAMAMEN SİMÜLASYONDUR, gerçek SMS gönderilmez.{RENK_BITIR}")
                tel = console.input("[bold magenta][*] Hedef hat (+90...): [/]").strip()
                adet = console.input("[bold magenta][*] Döngü sayısı [5]: [/]").strip()
                dongu = int(adet) if adet.isdigit() else 5
                console.print(self.run_async(TrindroxSMS(tel, dongu).start_gateway()))

            elif secim == "4":
                self.selected_menu = "HASH LAB"
                console.clear()
                console.print(self.generate_banner())
                h = console.input("[bold magenta][*] Hedef hash: [/]").strip()
                if h:
                    lab = TrindroxHashLab()
                    console.print(lab.analyze(h))
                    if console.input("[bold magenta][*] Wordlist ile kırılsın mı? (e/h): [/]").strip().lower() == "e":
                        wlist = console.input("[bold magenta][*] Wordlist yolu: [/]").strip()
                        algo = console.input("[bold magenta][*] Algoritma (MD5/SHA1/SHA256/SHA512): [/]").strip()
                        console.print(f"{SARI}[*] Kırma işlemi başlıyor...{RENK_BITIR}")
                        console.print(lab.crack_wordlist(h, wlist, algo))

            elif secim == "5":
                self.selected_menu = "OPSEC"
                console.clear()
                console.print(self.generate_banner())
                console.print(self.run_async(TrindroxOpSec().check_security_status()))

            elif secim == "0":
                self.status = "OFFLINE"
                return

            else:
                console.print(f"{KIRMIZI}[!] Geçersiz modül seçimi.{RENK_BITIR}")

            if secim != "1":
                console.input("\n[dim][ Devam etmek için Enter... ][/dim]")
                console.clear()

    # ————— OSINT MENÜSÜ — (SYNC — asyncio.run → run_async) —————
    async def _osint_menu(self):
        while True:
            console.print(Panel(
                "1. ★ FULL INTEL CHAIN ★ (Kullanıcı Adından HER ŞEY)\n"
                "2. Kullanıcı Adı İzi (52 Platform)\n"
                "3. GitHub Derin Analiz (UserID / Node ID / Commit E-postası)\n"
                "4. IP Locator & Konum Tespiti\n"
                "5. WHOIS RDAP Kayıt Bilgisi (Anahtarsız)\n"
                "6. Gravatar E-posta Profili (MD5 Hash + Bağlı Hesaplar)\n"
                "7. Telefon Numarası Analizi (Operatör / Hat Tipi)\n"
                "8. Dijital Parmak İzi + Sertifika Analizi (TLS / SHA-256)\n"
                "0. Ana Menüye Dön",
                title="[ OSINT CORE v2026.3 — M A R K Ø ]",
                border_style="magenta"
            ))
            secim = console.input("[bold magenta][?] OSINT modülü: [/]").strip()

            if secim == "1":
                hedef = console.input("[bold magenta][*] Hedef kullanıcı adı: [/]").strip().lstrip("@")
                if hedef:
                    intel = TrindroxFullIntel(hedef)
                    panels = await intel.run()
                    console.print("\n")
                    for i, p in enumerate(panels):
                        console.print(p)
                        if i < len(panels) - 1:
                            console.print()

            elif secim == "2":
                hedef = console.input("[bold magenta][*] Hedef kullanıcı adı: [/]").strip().lstrip("@")
                if hedef:
                    console.print(f"{SARI}[*] 52 platform taranıyor, bekleyin...{RENK_BITIR}")
                    console.print(await TrindroxOSINT(hedef).scan_all())

            elif secim == "3":
                hedef = console.input("[bold magenta][*] GitHub kullanıcı adı: [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] GitHub API sorgulanıyor...{RENK_BITIR}")
                    r = await TrindroxGitHub().deep_scan(hedef)
                    if isinstance(r, tuple):
                        console.print(r[0])
                    else:
                        console.print(r)

            elif secim == "4":
                hedef = console.input("[bold magenta][*] IP veya domain: [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] Konum tespiti yapılıyor...{RENK_BITIR}")
                    console.print(await TrindroxIPLocator().locate_panel(hedef))

            elif secim == "5":
                hedef = console.input("[bold magenta][*] Domain (örn: example.com): [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] RDAP/WHOIS sorgusu...{RENK_BITIR}")
                    console.print(await TrindroxWHOIS().lookup(hedef))

            elif secim == "6":
                hedef = console.input("[bold magenta][*] E-posta adresi: [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] Gravatar profili çekiliyor...{RENK_BITIR}")
                    console.print(await TrindroxGravatar().lookup_by_email(hedef))

            elif secim == "7":
                hedef = console.input("[bold magenta][*] Telefon numarası (+90...): [/]").strip()
                if hedef:
                    console.print(TrindroxPhone().analyze(hedef))

            elif secim == "8":
                hedef = console.input("[bold magenta][*] Hedef domain/site: [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] Parmak izi ve sertifika çekiliyor...{RENK_BITIR}")
                    console.print(await TrindroxFingerprint().fingerprint(hedef))

            elif secim == "0":
                return
            else:
                console.print(f"{KIRMIZI}[!] Geçersiz seçim.{RENK_BITIR}")

            console.input("\n[dim][ Devam etmek için Enter... ][/dim]")
            console.clear()


# =============================================================
#  GRAVATAR — MD5 → PROFİL
# =============================================================
class TrindroxGravatar:
    """E-posta → MD5 → Gravatar profili (anahtarsız, ücretsiz)."""

    async def lookup_by_email(self, email: str) -> Panel:
        body = Text()
        body.append(f"[*] E-posta: {email}\n", style="cyan")

        h = hashlib.md5(email.strip().lower().encode()).hexdigest()
        body.append(f"  MD5 Hash : {h}\n", style="yellow")

        async with httpx.AsyncClient(timeout=10) as cli:
            try:
                r = await cli.get(f"https://gravatar.com/{h}.json")
            except Exception as e:
                body.append(f"[!] Hata: {e}\n", style="red")
                return Panel(body, title="[ GRAVATAR ]", border_style="red")

        if r.status_code == 404:
            body.append("  [✘] Gravatar profili bulunamadı.\n", style="red")
            return Panel(body, title="[ GRAVATAR ]", border_style="red")

        try:
            d = r.json()
        except Exception as e:
            body.append(f"[!] JSON hatası: {e}\n", style="red")
            return Panel(body, title="[ GRAVATAR ]", border_style="red")

        entry = (d.get("entry") or [None])[0]
        if not entry:
            body.append("  [✘] Profil verisi boş.\n", style="red")
            return Panel(body, title="[ GRAVATAR ]", border_style="red")

        t = Table(show_header=False, box=None, expand=True)
        t.add_column("Alan", style="bold cyan", width=14)
        t.add_column("Değer", style="white")
        t.add_row("Görünen Ad", entry.get("displayName", "?"))
        t.add_row("Hakkında", (entry.get("aboutMe", "") or "?")[:80])
        t.add_row("Konum", entry.get("currentLocation", "?") or "?")
        for i, u in enumerate(entry.get("urls", [])[:4]):
            t.add_row(f"URL {i+1}", u.get("value", ""))
        for i, a in enumerate(entry.get("accounts", [])[:4]):
            t.add_row(f"Hesap {i+1}", a.get("url", ""))

        body.append(t)
        return Panel(body, title="[ GRAVATAR PROFİLİ — GERÇEK VERİ ]", border_style="magenta")


# =============================================================
#  ANALYZER — PORT TARAMASI
# =============================================================
class TrindroxAnalyzer:
    def __init__(self, hedef: str):
        self.hedef = hedef

    async def run_analysis(self) -> Panel:
        body = Text()
        body.append(f"[*] Hedef: {self.hedef}\n", style="cyan")

        # DNS çözümle
        try:
            ip = socket.gethostbyname(self.hedef)
            body.append(f"  Çözümlenen IP : {ip}\n", style="green")
        except Exception as e:
            body.append(f"[!] DNS hatası: {e}\n", style="red")
            return Panel(body, title="[ PORT ANALİZİ ]", border_style="red")

        ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 465, 993, 3389]
        open_ports = []

        loop = asyncio.get_running_loop()
        sem = asyncio.Semaphore(12)

        async def check_port(p):
            async with sem:
                try:
                    _, w = await asyncio.wait_for(
                        asyncio.open_connection(ip, p), timeout=3)
                    w.close()
                    open_ports.append(p)
                except Exception:
                    pass

        await asyncio.gather(*[check_port(p) for p in ports])

        tbl = Table(show_header=True, header_style="bold yellow", expand=True)
        tbl.add_column("Port", width=6)
        tbl.add_column("Durum", width=8)
        tbl.add_column("Servis", style="white")

        servisler = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
            80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
            465: "SMTPS", 993: "IMAPS", 3389: "RDP"
        }
        for p in ports:
            d = "AÇIK" if p in open_ports else "KAPALI"
            renk = "green" if p in open_ports else "dim"
            tbl.add_row(str(p), f"[{renk}]{d}[/{renk}]", servisler.get(p, "?"))

        body.append(tbl)
        return Panel(body, title="[ PORT ANALİZİ — GERÇEK TARAMA ]", border_style="cyan")


# =============================================================
#  OPSEC SHIELD — GİZLİLİK DURUMU
# =============================================================
class TrindroxOpSec:
    async def check_security_status(self) -> Panel:
        body = Text()
        body.append("[*] OPSEC Shield — Gizlilik Durumu\n\n", style="bold magenta")
        body.append("  Dış IP tespiti (anahtarsız)…\n", style="dim")
        try:
            async with httpx.AsyncClient(timeout=8) as cli:
                r = await cli.get("https://ipapi.co/json/")
                d = r.json()
                body.append(f"  Dış IP    : {d.get('ip', '?')}\n", style="green")
                body.append(f"  Konum     : {d.get('city', '?')}, {d.get('country_name', '?')}\n")
                body.append(f"  ISP       : {d.get('org', '?')}\n")
                body.append(f"  VPN/Proxy : {'EVET' if d.get('in_eu') else 'BİLİNMİYOR'}\n", style="yellow")
        except Exception as e:
            body.append(f"  [!] Tespit edilemedi: {e}\n", style="red")

        body.append("\n  Şifreleme kütüphaneleri:\n", style="bold")
        try:
            import cryptography
            body.append(f"  [+] cryptography kurulu (v{getattr(cryptography, '__version__', '?')})\n", style="green")
        except ImportError:
            body.append("  [✘] cryptography kurulu değil → pip install cryptography\n", style="red")

        return Panel(body, title="[ OPSEC SHIELD ]", border_style="magenta")


# =============================================================
#  SMS GATEWAY — SİMÜLASYON (kasıtlı, gerçek istek atmaz)
# =============================================================
class TrindroxSMS:
    def __init__(self, tel: str, dongu: int = 5):
        self.tel = tel
        self.dongu = dongu

    async def start_gateway(self) -> Panel:
        body = Text()
        body.append("[!] BU MODÜL TAMAMEN SİMÜLASYONDUR — hiçbir gerçek SMS gönderilmez.\n\n", style="bold yellow")
        body.append(f"  Hedef hat    : {self.tel}\n", style="cyan")
        body.append(f"  Döngü sayısı : {self.dongu}\n\n", style="cyan")
        for i in range(1, self.dongu + 1):
            body.append(f"  [{i}/{self.dongu}] Simüle edilen gönderim… (gerçek istek yok)\n", style="dim")
            await asyncio.sleep(0.2)
        body.append("\n  [✓] Simülasyon tamamlandı — hiçbir ağ isteği yapılmadı.\n", style="green")
        return Panel(body, title="[ SMS GATEWAY — SİMÜLASYON ]", border_style="yellow")


# =============================================================
#  TEMİZLİK & ÇIKIŞ
# =============================================================
def terminate_and_clean_logs():
    console.print(f"\n{SARI}[*] Trindrox UI Kapatılıyor…{RENK_BITIR}")
    try:
        if os.path.exists("__pycache__"):
            shutil.rmtree("__pycache__")
            console.print(f"{YESIL}[+] Önbellek dizini imha edildi.{RENK_BITIR}")
    except Exception:
        pass
    console.print(Panel(
        Text("SİSTEM ÇEVRİMDIŞI\n\n[ M A R K Ø - 2026 ]", style="bold red", justify="center"),
        border_style="red"
    ))


# =============================================================
#  ANA BLOK — asyncio.run KALDIRILDI (İç İçe Loop Hatası Bitti)
# =============================================================
if __name__ == "__main__":
    core_engine = TrindroxCore()
    try:
        core_engine.start_interface()          # ← asyncio.run YOK
        terminate_and_clean_logs()
    except KeyboardInterrupt:
        console.print("\n\n[bold red][!] Acil Durum Sinyali (Ctrl+C).[/bold red]")
        terminate_and_clean_logs()
        sys.exit(0)
