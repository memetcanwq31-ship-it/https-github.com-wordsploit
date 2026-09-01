# =====================================================================
# TRINDROX UI v2026.3.0 - YENİ NESİL SİBER GÜVENLİK FRAMEWORK
# GELİŞTİRİCİ / KOD ADI: M A R K Ø
# =====================================================================

import os
import sys
import re
import ssl
import socket
import hashlib
import asyncio
import json
import uuid
from datetime import datetime
from urllib.parse import urlparse

import httpx
from colorama import init

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

# Opsiyonel ama gerçek analiz için önerilir
try:
    import phonenumbers
    from phonenumbers import carrier as tel_carrier, timezone as tel_tz, geocoder as tel_geo
    PHONENUMBERS_OK = True
except ImportError:
    PHONENUMBERS_OK = False

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False

init(autoreset=True)
console = Console()

KIRMIZI = "[bold red]"
YESIL = "[bold green]"
MAVI = "[bold blue]"
SARI = "[bold yellow]"
MOR = "[bold magenta]"
CYAN = "[bold cyan]"
RENK_BITIR = "[/]"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DOMAIN_REGEX = re.compile(r"(?:https?://)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}")
IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


# =====================================================================
# OSINT CORE 1 — KULLANICI ADI İZİ TARAMASI (GENİŞ LETİLMİŞ)
# =====================================================================

class TrindroxOSINT:
    def __init__(self, target_username: str):
        self.target = target_username
        self.results = {}
        # Sherlock data.json referanslı, doğrulanmış URL patternleri
        self.platforms = {
            "Instagram":   f"https://www.instagram.com/{self.target}/",
            "GitHub":      f"https://github.com/{self.target}",
            "X (Twitter)": f"https://x.com/{self.target}",
            "Reddit":      f"https://www.reddit.com/user/{self.target}/about.json",
            "TikTok":      f"https://www.tiktok.com/@{self.target}",
            "Telegram":    f"https://t.me/{self.target}",
            "YouTube":     f"https://www.youtube.com/@{self.target}",
            "Medium":      f"https://medium.com/@{self.target}",
            "Pinterest":   f"https://www.pinterest.com/{self.target}/",
            "Steam":       f"https://steamcommunity.com/id/{self.target}",
            "Facebook":    f"https://www.facebook.com/{self.target}",
            "Twitch":      f"https://www.twitch.tv/{self.target}",
            "Spotify":     f"https://open.spotify.com/user/{self.target}",
            "SoundCloud":  f"https://soundcloud.com/{self.target}",
            "Bluesky":     f"https://bsky.app/profile/{self.target}",
            "Mastodon":    f"https://mastodon.social/@{self.target}",
            "GitLab":      f"https://gitlab.com/{self.target}",
            "Bitbucket":   f"https://bitbucket.org/{self.target}",
            "Keybase":     f"https://keybase.io/{self.target}",
            "Ko-fi":       f"https://ko-fi.com/{self.target}",
            "BuyMeCoffee": f"https://www.buymeacoffee.com/{self.target}",
            "Patreon":     f"https://www.patreon.com/{self.target}",
            "Pexels":      f"https://www.pexels.com/@{self.target}/",
            "DeviantArt":  f"https://www.deviantart.com/{self.target}",
            "ArtStation":  f"https://www.artstation.com/{self.target}",
            "Bandcamp":    f"https://{self.target}.bandcamp.com",
            "Last.fm":     f"https://www.last.fm/user/{self.target}",
            "Flickr":      f"https://www.flickr.com/people/{self.target}",
            "Imgur":       f"https://imgur.com/user/{self.target}",
            "Vimeo":       f"https://vimeo.com/{self.target}",
            "Dailymotion": f"https://www.dailymotion.com/{self.target}",
            "Letterboxd":  f"https://letterboxd.com/{self.target}/",
            "Chess.com":   f"https://www.chess.com/member/{self.target}",
            "Lichess":     f"https://lichess.org/@/{self.target}",
            "HackerNews":  f"https://news.ycombinator.com/user?id={self.target}",
            "HackerEarth": f"https://www.hackerearth.com/@{self.target}/",
            "CodePen":     f"https://codepen.io/{self.target}",
            "Replit":      f"https://replit.com/@{self.target}",
            "Codewars":    f"https://www.codewars.com/users/{self.target}",
            "LeetCode":    f"https://leetcode.com/{self.target}/",
            "About.me":    f"https://about.me/{self.target}",
            "Wikipedia":   f"https://en.wikipedia.org/wiki/User:{self.target}",
            "Wikivoyage":  f"https://en.wikivoyage.org/wiki/User:{self.target}",
            "WordPress":   f"https://{self.target}.wordpress.com",
            "Blogger":     f"https://{self.target}.blogspot.com",
            "Tumblr":      f"https://{self.target}.tumblr.com",
            "Goodreads":   f"https://www.goodreads.com/{self.target}",
            "Trakt":       f"https://trakt.tv/users/{self.target}",
            "Discogs":     f"https://www.discogs.com/user/{self.target}",
            "unsplash":    f"https://unsplash.com/@{self.target}",
            "itch.io":     f"https://{self.target}.itch.io",
            " roblox":     f"https://www.roblox.com/user.aspx?username={self.target}",
            "speedrun.com": f"https://www.speedrun.com/user/{self.target}",
        }

    async def check_platform(self, client, name: str, url: str):
        try:
            response = await client.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
            body = response.text

            if name == "Telegram":
                if response.status_code == 200 and "tgme_page_extra" in body:
                    self.results[name] = f"{YESIL}AKTİF → {url}{RENK_BITIR}"
                else:
                    self.results[name] = f"{KIRMIZI}BULUNAMADI{RENK_BITIR}"
                return

            if name == "Reddit":
                if response.status_code == 200 and '"error"' not in body[:200]:
                    self.results[name] = f"{YESIL}AKTİF → {url}{RENK_BITIR}"
                else:
                    self.results[name] = f"{KIRMIZI}BULUNAMADI{RENK_BITIR}"
                return

            if name == "X (Twitter)":
                if response.status_code == 200 and self.target.lower() in body.lower():
                    self.results[name] = f"{SARI}DOĞRULANAMADI (X anti-bot koruması){RENK_BITIR}"
                else:
                    self.results[name] = f"{KIRMIZI}BULUNAMADI{RENK_BITIR}"
                return

            if response.status_code == 200:
                # Bazı siteler 200 döner ama "user not found" sayfası gösterir
                not_found_signals = [
                    "user not found", "page not found", "404",
                    "not_found", "no user found", "no such user"
                ]
                body_lower = body[:3000].lower()
                if any(sig in body_lower for sig in not_found_signals):
                    self.results[name] = f"{KIRMIZI}BULUNAMADI{RENK_BITIR}"
                else:
                    self.results[name] = f"{YESIL}AKTİF → {url}{RENK_BITIR}"
            elif response.status_code == 404:
                self.results[name] = f"{KIRMIZI}BULUNAMADI{RENK_BITIR}"
            elif response.status_code in (403, 429):
                self.results[name] = f"{SARI}ERİŞİM ENGELLENDİ (KOD: {response.status_code}){RENK_BITIR}"
            elif response.status_code in (301, 302, 307, 308):
                self.results[name] = f"{SARI}YÖNLENDİRME ({response.status_code}){RENK_BITIR}"
            else:
                self.results[name] = f"{SARI}ŞÜPHELİ (KOD: {response.status_code}){RENK_BITIR}"

        except httpx.TimeoutException:
            self.results[name] = "[dim white]ZAMAN AŞIMI[/dim white]"
        except httpx.TooManyRedirects:
            self.results[name] = "[dim white]YÖNLENDİRME DÖNGÜSÜ[/dim white]"
        except Exception as e:
            self.results[name] = f"[dim white]BAĞLANTI HATASI ({type(e).__name__})[/dim white]"

    async def scan_all(self) -> Panel:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0, connect=8.0),
            limits=httpx.Limits(max_connections=30, max_keepalive_connections=10)
        ) as client:
            tasks = [self.check_platform(client, n, u) for n, u in self.platforms.items()]
            await asyncio.gather(*tasks)

        table = Table(title=f"[ İSTİHBARAT RAPORU: {self.target} ] ({len(self.platforms)} PLATFORM)", title_style="bold magenta", expand=True)
        table.add_column("Platform", style="cyan", justify="left")
        table.add_column("Durum / Tespit Linki", style="white", justify="left")
        for platform, status in self.results.items():
            table.add_row(platform, status)

        aktif = sum(1 for s in self.results.values() if "AKTİF" in s)
        engelli = sum(1 for s in self.results.values() if "ENGELLENDİ" in s)
        table.add_section()
        ozet = f"{YESIL}{aktif}/{len(self.platforms)} platformda aktif iz.{RENK_BITIR}"
        if engelli > 0:
            ozet += f" | {SARI}{engelli} platform anti-bot engelli.{RENK_BITIR}"
        table.add_row("[bold]ÖZET[/bold]", ozet)
        return Panel(table, border_style="green", title="[ OSINT CORE OUTPUT ]", title_align="left")

    def get_active_urls(self) -> list:
        """Aktif bulunan URL'leri döndür (FullIntel için)"""
        return [url for status in self.results.values() if "AKTİF" in status
                for url in [re.search(r'https?://\S+', status)] if url]

    def get_found_platforms(self) -> dict:
        """Bulunan platformları döndür (isim → URL)"""
        found = {}
        for name, status in self.results.items():
            match = re.search(r'https?://\S+', status)
            if match and ("AKTİF" in status or "ENGELLENDİ" in status):
                found[name] = match.group(0)
        return found


# =====================================================================
# OSINT CORE 2 — GITHUB DERİN ANALİZ (GENİŞ LETİLMİŞ)
# =====================================================================

class TrindroxGitHub:
    async def deep_scan(self, username: str) -> Panel:
        api = f"https://api.github.com/users/{username}"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(api, headers=HEADERS, timeout=10.0)
        except Exception:
            return Panel(f"{KIRMIZI}[!] GitHub API'ye ulaşılamadı.{RENK_BITIR}", border_style="red")

        if r.status_code == 404:
            return Panel(f"{KIRMIZI}[!] GitHub kullanıcısı bulunamadı: {username}{RENK_BITIR}", border_style="red")
        if r.status_code == 403:
            return Panel(f"{SARI}[!] GitHub API rate-limit (60/saat). Biraz bekle.{RENK_BITIR}", border_style="yellow")

        d = r.json()
        table = Table(title=f"[ GITHUB DERİN ANALİZ: {username} ]", title_style="bold magenta", expand=True)
        table.add_column("Alan", style="cyan")
        table.add_column("Gerçek Veri", style="white")

        table.add_row("Kullanıcı Adı", d.get("login", "-"))
        table.add_row("USER ID (Gerçek)", f"{YESIL}{d.get('id', '-')}{RENK_BITIR}")
        table.add_row("NODE ID (Global GUID)", f"{YESIL}{d.get('node_id', '-')}{RENK_BITIR}")
        table.add_row("Hesap Oluşturma", d.get("created_at", "-"))
        table.add_row("Son Güncelleme", d.get("updated_at", "-"))
        table.add_row("Ad", d.get("name") or "-")
        table.add_row("Bio", d.get("bio") or "-")
        table.add_row("Şirket", d.get("company") or "-")
        table.add_row("Konum (kendi bildirmiş)", d.get("location") or "-")
        table.add_row("E-posta (profil)", d.get("email") or "-")
        table.add_row("Blog / Site", d.get("blog") or "-")
        table.add_row("Twitter", d.get("twitter_username") or "-")
        table.add_row("Takipçi / Takip", f"{d.get('followers', 0)} / {d.get('following', 0)}")
        table.add_row("Herkese Açık Repo", str(d.get("public_repos", 0)))
        table.add_row("Profil URL", d.get("html_url", "-"))
        table.add_row("Avatar URL", d.get("avatar_url", "-"))
        table.add_row("Hireable", str(d.get("hireable", "-")))

        # --- Commit e-postası ve domain çıkarımı ---
        found_emails = set()
        found_domains = set()
        try:
            async with httpx.AsyncClient() as client:
                er = await client.get(
                    f"https://api.github.com/users/{username}/events/public?per_page=100",
                    headers=HEADERS, timeout=10.0
                )
                if er.status_code == 200:
                    for ev in er.json():
                        # Commit yazarı e-postası
                        for commit in ev.get("payload", {}).get("commits", []):
                            em = commit.get("author", {}).get("email")
                            nm = commit.get("author", {}).get("name")
                            if em and "noreply" not in em and "users.noreply.github.com" not in em:
                                found_emails.add(f"{nm} <{em}>")
                            # Commit mesajlarında domain
                            msg = commit.get("message", "")
                            for dm in DOMAIN_REGEX.findall(msg):
                                if not any(x in dm for x in ["github.com", "githubusercontent", "localhost", "127.0.0"]):
                                    found_domains.add(dm)

                        # Issue/PR gövdesinde e-posta
                        if ev.get("type") in ("IssuesEvent", "PullRequestEvent"):
                            body = ev.get("payload", {}).get("issue", {}).get("body") or ""
                            for em in EMAIL_REGEX.findall(body):
                                if "github" not in em and "noreply" not in em:
                                    found_emails.add(em)
        except Exception:
            pass

        if found_emails:
            table.add_section()
            table.add_row("COMMIT E-POSTALARI", f"{SARI}{', '.join(list(found_emails)[:5])}{RENK_BITIR}")
        if found_domains:
            table.add_row("BULUNAN DOMAİNLER", f"{CYAN}{', '.join(list(found_domains)[:5])}{RENK_BITIR}")

        return Panel(table, border_style="magenta", title="[ GITHUB DEEP OSINT OUTPUT ]", title_align="left"), \
               list(found_emails), list(found_domains)

    async def extract_intel(self, username: str):
        """FullIntel için veri çıkarma (Panel + e-posta + domain)"""
        result = await self.deep_scan(username)
        if isinstance(result, tuple):
            return result
        return result, [], []


# =====================================================================
# WHOIS (RDAP - ANAHTARSIZ ÜCRETSİZ)
# =====================================================================

class TrindroxWHOIS:
    async def lookup(self, domain: str) -> Panel:
        domain = domain.strip().lower().replace("http://", "").replace("https://", "").strip("/")
        # Subdomain varsa ana domaini al
        parts = domain.split(".")
        if len(parts) > 2 and parts[-2].lower() not in ("co", "org", "net", "gov", "edu"):
            domain = ".".join(parts[-2:])

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"https://rdap.org/domain/{domain}",
                    headers={**HEADERS, "Accept": "application/rdap+json"},
                    timeout=15.0,
                    follow_redirects=True
                )
        except Exception:
            return Panel(f"{KIRMIZI}[!] RDAP sunucusuna ulaşılamadı: {domain}{RENK_BITIR}", border_style="red")

        if r.status_code == 404:
            return Panel(f"{KIRMIZI}[!] Domain kaydı bulunamadı: {domain}{RENK_BITIR}", border_style="red")
        if r.status_code != 200:
            return Panel(f"{KIRMIZI}[!] RDAP sorgusu başarısız (KOD: {r.status_code}){RENK_BITIR}", border_style="red")

        d = r.json()
        table = Table(title=f"[ WHOIS RDAP RAPORU: {domain} ]", title_style="bold blue", expand=True)
        table.add_column("Alan", style="cyan")
        table.add_column("Gerçek Veri", style="white")

        table.add_row("Domain", f"{YESIL}{d.get('ldhName', domain)}{RENK_BITIR}")

        # Handle
        handle = d.get("handle", "-")
        table.add_row("Registry Handle", handle)

        # Durum (status codes)
        statuses = d.get("status", [])
        if statuses:
            status_str = ", ".join(statuses[:5])
            locked = any("lock" in s.lower() or "prohibited" in s.lower() for s in statuses)
            status_col = CYAN if locked else SARI
            table.add_row("Durum Kodları", f"{status_col}{status_str}{RENK_BITIR}")

        # Eventler (oluşturma, güncelleme, bitiş)
        events = d.get("events", [])
        for ev in events:
            ev_action = ev.get("eventAction", "")
            ev_date = ev.get("eventDate", "")
            if ev_action and ev_date:
                display_name = {
                    "registration": "Kayıt Tarihi",
                    "expiration": "Bitiş Tarihi",
                    "last changed": "Son Değişiklik",
                    "last update of RDAP database": "RDAP Güncelleme",
                    "transfer": "Transfer",
                }.get(ev_action, ev_action.title())
                table.add_row(display_name, ev_date[:10])

        # Nameservers
        nameservers = d.get("nameservers", [])
        ns_list = [ns.get("ldhName", "") for ns in nameservers[:5]]
        if ns_list:
            table.add_row("Nameserverlar", ", ".join(filter(None, ns_list)))

        # Entities (registrar, kayıt sahibi)
        entities = d.get("entities", [])
        for entity in entities[:3]:
            roles = entity.get("roles", [])
            vcard = entity.get("vcardArray", [None, []])
            name = "-"
            for item in vcard[1] if len(vcard) > 1 else []:
                if item[0] == "fn":
                    name = item[3]
                    break
            email = "-"
            for item in vcard[1] if len(vcard) > 1 else []:
                if item[0] == "email":
                    email = item[3]
                    break
            role_str = ", ".join(roles[:3])
            table.add_row(f"Entity ({role_str})", f"{name}" + (f" | {email}" if email != "-" else ""))

        return Panel(table, border_style="blue", title="[ WHOIS RDAP OUTPUT ]", title_align="left")


# =====================================================================
# GRAVATAR — E-POSTADAN PROFİL ÇEKME
# =====================================================================

class TrindroxGravatar:
    async def lookup_by_email(self, email: str) -> Panel:
        email = email.strip().lower()
        md5_hash = hashlib.md5(email.encode()).hexdigest()

        # Avatar URL
        avatar_url = f"https://www.gravatar.com/avatar/{md5_hash}?s=200&d=identicon"

        # Profil JSON (eski endpoint, hala aktif)
        profile_url = f"https://www.gravatar.com/{md5_hash}.json"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(profile_url, headers=HEADERS, timeout=10.0, follow_redirects=True)
        except Exception:
            return Panel(f"{KIRMIZI}[!] Gravatar servisine ulaşılamadı.{RENK_BITIR}", border_style="red")

        table = Table(title=f"[ GRAVATAR OSINT: {email} ]", title_style="bold yellow", expand=True)
        table.add_column("Alan", style="cyan")
        table.add_column("Değer", style="white")
        table.add_row("E-posta", email)
        table.add_row("MD5 Hash", f"{SARI}{md5_hash}{RENK_BITIR}")
        table.add_row("Avatar URL", f"[link={avatar_url}]{avatar_url[:50]}...[/link]")

        if r.status_code == 200:
            d = r.json()
            entry = d.get("entry", [{}])[0]
            table.add_row("Profil Mevcut", f"{YESIL}EVET{RENK_BITIR}")
            table.add_row("Hash (Gravatar)", entry.get("hash", "-"))
            table.add_row("Görünen Ad", entry.get("displayName", "-"))
            table.add_row("Hakkında", entry.get("aboutMe", "-"))
            table.add_row("Mevcut Konum", entry.get("currentLocation", "-"))
            if entry.get("thumbnailUrl"):
                table.add_row("Avatar Thumb", f"https://www.gravatar.com{entry['thumbnailUrl']}")
            urls = entry.get("urls", [])
            if urls:
                url_list = ", ".join([u.get("value", "") for u in urls[:3]])
                table.add_row("Bağlantılı URLler", url_list)
            if entry.get("accounts"):
                accounts = entry.get("accounts", [])
                acc_str = ", ".join([f"{a.get('shortname', '')}({a.get('url', '')[:30]})" for a in accounts[:4]])
                table.add_row("Bağlı Hesaplar", acc_str)
        elif r.status_code == 404:
            table.add_row("Profil Mevcut", f"{KIRMIZI}HAYIR (Profil yok veya gizli){RENK_BITIR}")
        else:
            table.add_row("Profil Sorgusu", f"{SARI}KOD: {r.status_code}{RENK_BITIR}")

        return Panel(table, border_style="yellow", title="[ GRAVATAR OUTPUT ]", title_align="left")


# =====================================================================
# OSINT CORE 3 — IP LOCATOR (GENİŞ LETİLMİŞ)
# =====================================================================

class TrindroxIPLocator:
    async def locate(self, target: str) -> tuple:
        """Panel + çözümlenen IP'yi döndürür"""
        target_ip = target
        # IPv6 check
        if ":" in target and IP_REGEX.match(target) is None:
            return Panel(f"{KIRMIZI}[!] IPv6 henüz desteklenmiyor: {target}{RENK_BITIR}", border_style="red"), None

        try:
            resolved = socket.gethostbyname(target)
            if resolved != target:
                target_ip = resolved
        except socket.gaierror:
            return Panel(f"{KIRMIZI}[!] Hedef çözümlenemedi: {target}{RENK_BITIR}", border_style="red"), None

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"http://ip-api.com/json/{target_ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting,query,reverse",
                    headers=HEADERS, timeout=10.0
                )
                if r.status_code == 429:
                    return Panel(f"{SARI}[!] ip-api rate-limit (45/min). 60sn bekle.{RENK_BITIR}", border_style="yellow"), None
                if r.status_code != 200 or r.json().get("status") != "success":
                    return Panel(f"{KIRMIZI}[!] Konum servisi yanıt vermedi: {r.json().get('message', '')}{RENK_BITIR}", border_style="red"), None
                d = r.json()
        except Exception:
            return Panel(f"{KIRMIZI}[!] Konum servisine bağlanılamadı.{RENK_BITIR}", border_style="red"), None

        proxy_flag = f"{KIRMIZI}EVET (Proxy/VPN/TOR){RENK_BITIR}" if d.get("proxy") else f"{YESIL}HAYIR{RENK_BITIR}"
        hosting_flag = f"{SARI}EVET (Sunucu/Hosting){RENK_BITIR}" if d.get("hosting") else "HAYIR"
        mobile_flag = f"{SARI}EVET (Mobil şebeke){RENK_BITIR}" if d.get("mobile") else "HAYIR"
        harita = f"https://www.google.com/maps?q={d.get('lat')},{d.get('lon')}"
        reverse_dns = d.get("reverse") or "-"

        table = Table(title=f"[ IP LOCATOR RAPORU: {target} → {target_ip} ]", title_style="bold cyan", expand=True)
        table.add_column("Bilgi", style="cyan")
        table.add_column("Gerçek Değer", style="white")

        table.add_row("Çözümlenen IP", f"{YESIL}{d.get('query')}{RENK_BITIR}")
        table.add_row("Reverse DNS (PTR)", reverse_dns)
        table.add_row("Ülke / Kod", f"{d.get('country')} ({d.get('countryCode')})")
        table.add_row("Bölge / Şehir", f"{d.get('regionName')} / {d.get('city')}")
        table.add_row("Posta Kodu", d.get("zip") or "-")
        table.add_row("Koordinat (Lat/Lon)", f"{d.get('lat')}, {d.get('lon')}")
        table.add_row("Saat Dilimi", d.get("timezone") or "-")
        table.add_row("ISP", d.get("isp") or "-")
        table.add_row("Organizasyon", d.get("org") or "-")
        table.add_row("AS Numarası", d.get("as") or "-")
        table.add_row("Proxy/VPN Tespiti", proxy_flag)
        table.add_row("Hosting/Sunucu", hosting_flag)
        table.add_row("Mobil Şebeke", mobile_flag)
        table.add_section()
        table.add_row("TAM KONUM (HARİTA)", f"[bold yellow underline link={harita}]{harita}[/bold yellow underline][/]")
        return Panel(table, border_style="cyan", title="[ IP LOCATOR OUTPUT ]", title_align="left"), target_ip

    async def locate_panel(self, target: str) -> Panel:
        """Sadece Panel döndürür (mevcut davranış)"""
        panel, _ = await self.locate(target)
        return panel


# =====================================================================
# OSINT CORE 4 — TELEFON NUMARASI ANALİZİ (MEVCUT - İYİ)
# =====================================================================

class TrindroxPhone:
    def analyze(self, phone: str) -> Panel:
        if not PHONENUMBERS_OK:
            return Panel(f"{KIRMIZI}[!] phonenumbers kütüphanesi yok. Kur: pip install phonenumbers{RENK_BITIR}", border_style="red")

        try:
            if phone.startswith("+"):
                num = phonenumbers.parse(phone)
            else:
                num = phonenumbers.parse(phone, "TR")
        except Exception:
            return Panel(f"{KIRMIZI}[!] Numara ayrıştırılamadı: {phone}{RENK_BITIR}", border_style="red")

        gecerli = phonenumbers.is_valid_number(num)
        table = Table(title=f"[ TELEFON ANALİZ RAPORU: {phone} ]", title_style="bold yellow", expand=True)
        table.add_column("Bilgi", style="cyan")
        table.add_column("Gerçek Değer", style="white")

        table.add_row("E.164 Formatı", f"{YESIL if gecerli else KIRMIZI}{phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)}{RENK_BITIR}")
        table.add_row("Numara Geçerli mi", f"{YESIL}GEÇERLİ{RENK_BITIR}" if gecerli else f"{KIRMIZI}GEÇERSİZ{RENK_BITIR}")
        table.add_row("Ülke", tel_geo.country_name_for_number(num, "tr") or "-")
        bolge = tel_geo.description_for_number(num, "tr") or "-"
        table.add_row("Bölge/Şehir Kodu", bolge)
        operator = tel_carrier.name_for_number(num, "tr") or "-"
        table.add_row("Operatör (Gerçek)", f"{SARI}{operator}{RENK_BITIR}")

        tip_map = {
            phonenumbers.PhoneNumberType.MOBILE: "MOBİL HAT",
            phonenumbers.PhoneNumberType.FIXED_LINE: "SABİT HAT",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "SABİT/MOBİL",
            phonenumbers.PhoneNumberType.VOIP: "VOIP (İnternet Hattı)",
            phonenumbers.PhoneNumberType.TOLL_FREE: "ÜCRETSİZ HAT",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "PRİM HATTI",
        }
        hat_tipi = tip_map.get(phonenumbers.number_type(num), "BELİRSİZ")
        table.add_row("Hat Tipi", hat_tipi)

        try:
            tz_list = tel_tz.time_zones_for_number(num)
            table.add_row("Saat Dilimi", ", ".join(tz_list))
        except Exception:
            pass

        table.add_section()
        table.add_row("[bold]NOT[/bold]", "[dim]Hat sahibi kimlik verisi operatör API'sine bağlıdır ve halka açık değildir.[/dim]")
        return Panel(table, border_style="yellow", title="[ PHONE INTEL OUTPUT ]", title_align="left")


# =====================================================================
# OSINT CORE 5 — DİJİTAL PARMAK İZİ + SERTİFİKA (MEVCUT - İYİ)
# =====================================================================

class TrindroxFingerprint:
    async def fingerprint(self, host: str) -> Panel:
        host = host.replace("https://", "").replace("http://", "").strip().strip("/")
        table = Table(title=f"[ DİJİTAL PARMAK İZİ: {host} ]", title_style="bold magenta", expand=True)
        table.add_column("Katman", style="cyan")
        table.add_column("Gerçek Veri", style="white")

        try:
            async with httpx.AsyncClient(verify=False) as client:
                r = await client.get(f"https://{host}", headers=HEADERS, timeout=10.0, follow_redirects=True)
            h = r.headers
            table.add_row("HTTP Durumu", str(r.status_code))
            server = h.get("server") or "-"
            table.add_row("Server (Sunucu İzi)", f"{YESIL}{server}{RENK_BITIR}")
            table.add_row("X-Powered-By", h.get("x-powered-by") or "-")
            table.add_row("Content-Type", h.get("content-type") or "-")
            table.add_row("CF-Ray (Cloudflare İzi)", h.get("cf-ray") or "YOK")
            guvenlik = []
            for hdr in ["strict-transport-security", "content-security-policy", "x-frame-options", "x-content-type-options"]:
                guvenlik.append(f"{hdr}: {'VAR' if hdr in h else 'YOK'}")
            table.add_row("Güvenlik Başlıkları", " | ".join(guvenlik))
            cookies = h.get("set-cookie")
            if cookies:
                c_names = [c.split("=")[0] for c in cookies.split("; ") if "=" in c][:4]
                table.add_row("Cookie Parmak İzi", f"{SARI}{', '.join(c_names)}{RENK_BITIR}")
        except Exception as e:
            table.add_row("HTTP Katmanı", f"{KIRMIZI}HATA: {type(e).__name__}{RENK_BITIR}")

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, 443), timeout=6) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    tls_version = ssock.version()
                    cipher = ssock.cipher()[0] if ssock.cipher() else "-"
                    der = ssock.getpeercert(binary_form=True)
            table.add_row("TLS Sürümü", f"{YESIL}{tls_version}{RENK_BITIR}")
            table.add_row("Şifre Paketi (Cipher)", cipher)

            if der and CRYPTO_OK:
                cert = x509.load_der_x509_certificate(der)
                sha_fp = cert.fingerprint(hashes.SHA256()).hex(":")
                table.add_row("Sertifika Seri No (GERÇEK)", f"{SARI}{cert.serial_number}{RENK_BITIR}")
                try:
                    nb, na = cert.not_valid_before_utc, cert.not_valid_after_utc
                except AttributeError:
                    nb, na = cert.not_valid_before, cert.not_valid_after
                table.add_row("Sertifika Geçerlilik", f"{nb.strftime('%Y-%m-%d')} → {na.strftime('%Y-%m-%d')}")
                table.add_row("Konu (Subject)", cert.subject.rfc4514_string()[:60])
                table.add_row("Veren (Issuer)", cert.issuer.rfc4514_string()[:60])
                table.add_row("SHA-256 Parmak İzi", f"[bold yellow]{sha_fp}[/bold yellow]")
            elif der and not CRYPTO_OK:
                raw_fp = hashlib.sha256(der).hexdigest()
                table.add_row("SHA-256 Parmak İzi (ham)", raw_fp)
                table.add_row("Not", "[dim]Detaylı sertifika alanları için: pip install cryptography[/dim]")
        except Exception:
            table.add_row("TLS Katmanı", f"{KIRMIZI}Bağlantı kurulamadı / TLS yok{RENK_BITIR}")

        return Panel(table, border_style="magenta", title="[ FINGERPRINT OUTPUT ]", title_align="left")


# =====================================================================
# FIREWALL ANALYZER — MEVCUT (İYİ)
# =====================================================================

class TrindroxAnalyzer:
    def __init__(self, target_host: str):
        self.host = target_host
        self.target_ports = {
            21: "FTP (Dosya)", 22: "SSH (Güvenli)", 23: "Telnet",
            25: "SMTP (E-Posta)", 53: "DNS (Sistem)", 80: "HTTP (Web)",
            110: "POP3 (Posta)", 443: "HTTPS (Güvenli Web)", 445: "SMB (Paylaşım)",
            3306: "MySQL", 3389: "RDP (Uzak Masaüstü)", 8080: "HTTP-Alt",
        }
        self.open_ports = []
        self.firewall_detected = False

    async def scan_port(self, port: int, description: str):
        try:
            conn = asyncio.open_connection(self.host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=2.5)
            self.open_ports.append((port, description, f"{YESIL}AÇIK (Açık Kapı){RENK_BITIR}"))
            try:
                banner = await asyncio.wait_for(reader.read(128), timeout=1.5)
                banner_str = banner.decode(errors="replace").strip().replace("\n", " ")[:60]
                if banner_str:
                    self.open_ports.append(("", "", f"[dim]└ Banner: {banner_str}[/dim]"))
            except Exception:
                pass
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except asyncio.TimeoutError:
            self.firewall_detected = True
        except Exception:
            pass

    async def run_analysis(self) -> Panel:
        try:
            target_ip = socket.gethostbyname(self.host)
        except socket.gaierror:
            return Panel(f"{KIRMIZI}[!] Hata: Makine ({self.host}) bulunamadı.{RENK_BITIR}", border_style="red")

        tasks = [self.scan_port(port, desc) for port, desc in self.target_ports.items()]
        await asyncio.gather(*tasks)

        table = Table(title=f"[ NETWORK ANALİZ RAPORU: {self.host} ({target_ip}) ]", title_style="bold cyan", expand=True)
        table.add_column("Port", style="yellow", justify="center")
        table.add_column("Servis Adı", style="white")
        table.add_column("Sistem Durumu", style="green")

        if self.open_ports:
            for port, desc, status in self.open_ports:
                table.add_row(str(port), desc, status)
        else:
            table.add_row("---", "Açık kritik port tespit edilemedi.", "[dim white]KAPALI[/dim white]")

        fw_status = f"{KIRMIZI}AKTİF / AGRESİF (Filtreliyor){RENK_BITIR}" if self.firewall_detected else f"{SARI}ZAYIF VEYA YOK (Açık){RENK_BITIR}"
        table.add_section()
        table.add_row("[bold]FIREWALL[/bold]", "[bold]Güvenlik Duvarı Durumu:[/bold]", fw_status)
        return Panel(table, border_style="cyan", title="[ FIREWALL ANALYZER OUTPUT ]", title_align="left")


# =====================================================================
# SMS GATEWAY — SİMÜLASYON (DEĞİŞMEDİ - GÜVENLİ TASARIM)
# =====================================================================

class TrindroxSMS:
    """Simülasyon modülü: Gerçek SMS gateway'lerine istek ATMAZ."""

    def __init__(self, target_phone: str, loop_count: int = 5):
        self.phone = target_phone
        self.loops = loop_count
        self.success_count = 0
        self.failed_count = 0

    async def send_single_sms(self, step: int):
        await asyncio.sleep(0.3)
        if step % 5 != 0:
            self.success_count += 1
        else:
            self.failed_count += 1

    async def start_gateway(self) -> Panel:
        tasks = [self.send_single_sms(i) for i in range(1, self.loops + 1)]
        await asyncio.gather(*tasks)

        table = Table(title=f"[ GATEWAY TRAFİK RAPORU: {self.phone} ] (SİMÜLASYON)", title_style="bold yellow", expand=True)
        table.add_column("İşlem Türü", style="cyan")
        table.add_column("İstatistik / Durum", style="white", justify="center")
        table.add_row("Mod", f"{SARI}SİMÜLASYON (Gerçek istek atılmadı){RENK_BITIR}")
        table.add_row("Başarılı Gönderim", f"{YESIL}{self.success_count} Adet{RENK_BITIR}")
        table.add_row("Başarısız/Engellenen", f"{KIRMIZI}{self.failed_count} Adet{RENK_BITIR}")

        status_summary = f"{YESIL}TAMAMLANDI{RENK_BITIR}" if self.failed_count == 0 else f"{SARI}KISMEN ENGELLENDİ (RATE LIMIT){RENK_BITIR}"
        table.add_section()
        table.add_row("[bold]SONUÇ[/bold]", status_summary)
        return Panel(table, border_style="yellow", title="[ SMS GATEWAY OUTPUT ]", title_align="left")


# =====================================================================
# HASH LAB — MEVCUT (İYİ)
# =====================================================================

class TrindroxHashLab:
    MODLAR = {
        32: ["MD5", "NTLM", "MD4", "LM"],
        40: ["SHA1", "MySQL5"],
        56: ["SHA224"],
        64: ["SHA256", "SHA3-256", "BLAKE2s"],
        96: ["SHA384"],
        128: ["SHA512", "Whirlpool", "SHA3-512"],
    }

    def analyze(self, hash_string: str) -> Panel:
        hash_string = hash_string.strip()
        uzunluk = len(hash_string)
        muhtemel = self.MODLAR.get(uzunluk, [])
        hex_gecerli = bool(re.fullmatch(r"[0-9a-fA-F]+", hash_string))
        karakter_seti = "Hexadecimal" if hex_gecerli else "BİLİNMİYEN (Hex değil!)"
        buyuk_harf = hash_string.isupper()

        table = Table(title="[ HASH KRİPTANALİZ RAPORU ]", title_style="bold magenta", expand=True)
        table.add_column("Özellik", style="cyan")
        table.add_column("Tespit", style="white")
        table.add_row("Hash Değeri", f"[bold yellow]{hash_string[:32]}{'...' if uzunluk > 32 else ''}[/bold yellow]")
        table.add_row("Uzunluk", f"{uzunluk} karakter")
        table.add_row("Karakter Seti", karakter_seti)

        if muhtemel and hex_gecerli:
            tahmin = " / ".join(muhtemel)
            if uzunluk == 32 and buyuk_harf:
                tahmin += " (Büyük harf → Windows NTLM/LM olabilir)"
            table.add_row("Muhtemel Algoritma", f"{YESIL}{tahmin}{RENK_BITIR}")
        else:
            table.add_row("Muhtemel Algoritma", f"{KIRMIZI}Tespit edilemedi (sıra/salt'lı format olabilir){RENK_BITIR}")

        table.add_section()
        table.add_row("[bold]İPUCU[/bold]", "Kırma için: hashcat -m <mod> hash.txt wordlist.txt")
        return Panel(table, border_style="magenta", title="[ HASH LAB OUTPUT ]", title_align="left")

    def crack_wordlist(self, hash_string: str, wordlist_path: str, algorithm: str) -> Panel:
        algo_map = {
            "MD5": hashlib.md5,
            "SHA1": hashlib.sha1,
            "SHA256": hashlib.sha256,
            "SHA512": hashlib.sha512,
        }
        h_fonk = algo_map.get(algorithm.upper())
        if not h_fonk:
            return Panel(f"{KIRMIZI}[!] Desteklenen algoritmalar: MD5, SHA1, SHA256, SHA512{RENK_BITIR}", border_style="red")

        hedef = hash_string.strip().lower()
        try:
            with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
                denenen = 0
                for satir in f:
                    kelime = satir.strip()
                    if not kelime:
                        continue
                    denenen += 1
                    if h_fonk(kelime.encode()).hexdigest() == hedef:
                        table = Table(title="[ KIRMA BAŞARILI ]", title_style="bold green", expand=True)
                        table.add_column("Alan", style="cyan")
                        table.add_column("Değer", style="white")
                        table.add_row("Hash", hash_string)
                        table.add_row("Düz Metin", f"{YESIL}{kelime}{RENK_BITIR}")
                        table.add_row("Algoritma", algorithm.upper())
                        table.add_row("Denenen Kelime", str(denenen))
                        return Panel(table, border_style="green", title="[ HASH LAB OUTPUT ]", title_align="left")

            return Panel(f"{KIRMIZI}[!] {denenen} denemede kırılamadı. Wordlist'i değiştir.{RENK_BITIR}", border_style="red")
        except FileNotFoundError:
            return Panel(f"{KIRMIZI}[!] Wordlist dosyası bulunamadı: {wordlist_path}{RENK_BITIR}", border_style="red")


# =====================================================================
# OPSEC SHIELD — MEVCUT (İYİ)
# =====================================================================

class TrindroxOpSec:
    def __init__(self):
        self.current_ip = "BİLİNMİYOR"
        self.vpn_status = f"{KIRMIZI}RİSKLİ (VPN YOK){RENK_BITIR}"
        self.tor_status = f"{KIRMIZI}PASİF (Tor Yok){RENK_BITIR}"

    async def check_security_status(self) -> Panel:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://ipapi.co/json/", headers=HEADERS, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    self.current_ip = data.get("ip", "BİLİNMİYOR")
                    org = (data.get("org") or "").lower()
                    if any(x in org for x in ["vpn", "hosting", "cloud", "server", "ovh", "digitalocean", "linode", "vultr", "m247", "datacamp"]):
                        self.vpn_status = f"{YESIL}GÜVENLİ (VPN/Sunucu Aktif){RENK_BITIR}"
                    else:
                        self.vpn_status = f"{SARI}AÇIK AĞ (Yerel ISP){RENK_BITIR}"
        except Exception:
            self.current_ip = "BAĞLANTI YOK"

        table = Table(title="[ OPSEC GİZLİLİK VE ŞİFRELEME DURUMU ]", title_style="bold green", expand=True)
        table.add_column("Güvenlik Katmanı", style="cyan")
        table.add_column("Mevcut Analiz Çıktısı", style="white")
        table.add_row("Dış IP Adresi", f"[bold yellow]{self.current_ip}[/bold yellow]")
        table.add_row("VPN Kalkanı", self.vpn_status)
        table.add_row("Tor Yönlendirmesi", self.tor_status)
        return Panel(table, border_style="green", title="[ OPSEC SHIELD OUTPUT ]", title_align="left")


# =====================================================================
# ★★★ FULL INTEL CHAIN — KULLANICI ADINDAN HER ŞEY ★★★
# =====================================================================

class TrindroxFullIntel:
    """
    FULL ZİNCİR: Kullanıcı Adı → Platformlar → GitHub → Bio/Blog Domainleri
    → DNS Çözümleme → Gerçek IP → Coğrafi Konum → E-posta → Gravatar → Tüm Rapor
    """

    def __init__(self, target_username: str):
        self.target = target_username
        self.found_platforms = {}
        self.extracted_emails = []
        self.extracted_domains = []
        self.resolved_ips = {}  # domain → IP

    async def extract_domains_from_profiles(self, client, urls: list) -> set:
        """Aktif profil sayfalarından domain çıkarır"""
        domains = set()
        for url in urls[:10]:  # ilk 10 aktif profil
            try:
                r = await client.get(url, headers=HEADERS, timeout=8.0, follow_redirects=True)
                if r.status_code == 200:
                    body = r.text[:50000]
                    for dm in DOMAIN_REGEX.findall(body):
                        dm = dm.lower().rstrip(".")
                        # Filtreleme
                        skip = ["github", "instagram", "twitter", "x.com", "reddit", "tiktok",
                                "telegram", "youtube", "medium", "pinterest", "steam", "facebook",
                                "twitch", "spotify", "soundcloud", "google", "apple", "microsoft",
                                "amazon", "cloudflare", "cdn", "gravatar", "w3.org", "schema.org",
                                "localhost", "127.0.0", "example.com", "0.0.0", "1.1.1"]
                        if not any(s in dm for s in skip) and "." in dm:
                            # IP adreslerini domain olarak alma
                            if not IP_REGEX.match(dm):
                                # Sadece ana domainleri al
                                parts = dm.split(".")
                                if len(parts) >= 2:
                                    main_domain = ".".join(parts[-2:]) if len(parts) > 2 else dm
                                    if len(main_domain) > 3:
                                        domains.add(main_domain)
            except Exception:
                continue
        return domains

    async def resolve_and_geolocate(self, domains: set) -> dict:
        """Domain → IP → Coğrafi Konum zinciri"""
        results = {}
        for dm in list(domains)[:8]:  # max 8 domain
            try:
                ip = socket.gethostbyname(dm)
                self.resolved_ips[dm] = ip
                # ip-api.com geolocation
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.get(
                            f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org,lat,lon,proxy,hosting",
                            headers=HEADERS, timeout=8.0
                        )
                        if r.status_code == 200 and r.json().get("status") == "success":
                            results[dm] = {"ip": ip, **r.json()}
                        else:
                            results[dm] = {"ip": ip, "status": "geo_bulunamadi"}
                except Exception:
                    results[dm] = {"ip": ip, "status": "geo_hatasi"}
            except socket.gaierror:
                results[dm] = {"ip": None, "status": "dns_hatasi"}
            except Exception:
                results[dm] = {"ip": None, "status": "hata"}
            await asyncio.sleep(0.15)  # ip-api rate limit koruması
        return results

    async def run(self) -> list:
        """Tüm zinciri çalıştırır ve panel listesi döndürür"""
        panels = []

        # ========= ADIM 1: Platform Taraması =========
        console.print(f"\n{CYAN}[*] ADIM 1/6 — Platform taraması başlıyor...{RENK_BITIR}")
        osint = TrindroxOSINT(self.target)
        panel1 = await osint.scan_all()
        self.found_platforms = osint.get_found_platforms()
        panels.append(panel1)

        if not self.found_platforms:
            console.print(f"{KIRMIZI}[!] Hiçbir platformda aktif profil bulunamadı.{RENK_BITIR}")
            return panels

        console.print(f"{YESIL}[+] {len(self.found_platforms)} platformda profil bulundu.{RENK_BITIR}")

        # ========= ADIM 2: GitHub Derin Analiz =========
        if "GitHub" in self.found_platforms:
            console.print(f"{CYAN}[*] ADIM 2/6 — GitHub derin taraması...{RENK_BITIR}")
            gh = TrindroxGitHub()
            gh_panel, gh_emails, gh_domains = await gh.extract_intel(self.target)
            panels.append(gh_panel)
            self.extracted_emails.extend(gh_emails)
            self.extracted_domains.extend(gh_domains)
        else:
            console.print(f"{SARI}[*] GitHub profili yok, adım atlanıyor.{RENK_BITIR}")

        # ========= ADIM 3: Profil sayfalarından domain çıkarımı =========
        console.print(f"{CYAN}[*] ADIM 3/6 — Profil sayfalarından domain çıkarımı...{RENK_BITIR}")
        active_urls = [url for url in self.found_platforms.values()]
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(15.0)) as client:
            html_domains = await self.extract_domains_from_profiles(client, active_urls)
        self.extracted_domains.extend(html_domains)
        self.extracted_domains = list(set(self.extracted_domains))

        if self.extracted_domains:
            console.print(f"{YESIL}[+] {len(self.extracted_domains)} domain çıkarıldı: {', '.join(self.extracted_domains[:5])}{RENK_BITIR}")

        # ========= ADIM 4: Domain → IP → Coğrafi Konum =========
        if self.extracted_domains:
            console.print(f"{CYAN}[*] ADIM 4/6 — DNS çözümleme + IP konumlandırma...{RENK_BITIR}")
            geo_results = await self.resolve_and_geolocate(set(self.extracted_domains))

            geo_table = Table(title=f"[ DOMAIN → IP → KONUM RAPORU ]", title_style="bold cyan", expand=True)
            geo_table.add_column("Domain", style="white")
            geo_table.add_column("Çözümlenen IP", style="green")
            geo_table.add_column("Ülke/Şehir", style="white")
            geo_table.add_column("ISP/Org", style="cyan")
            geo_table.add_column("Proxy?", style="red")
            geo_table.add_column("Harita", style="yellow")

            for dm, info in geo_results.items():
                if info.get("ip"):
                    if info.get("status") != "geo_bulunamadi" and info.get("country"):
                        harita_link = f"https://www.google.com/maps?q={info.get('lat')},{info.get('lon')}"
                        proxy = "EVET" if info.get("proxy") else "Hayır"
                        hosting = " [HOSTING]" if info.get("hosting") else ""
                        geo_table.add_row(
                            dm, info["ip"],
                            f"{info.get('country', '')} / {info.get('city', '')}",
                            f"{info.get('isp', '')} / {info.get('org', '')}{hosting}",
                            proxy,
                            f"[link={harita_link}]Harita[/link]"
                        )
                    else:
                        geo_table.add_row(dm, info["ip"], "-", "-", "-", "-")
                else:
                    geo_table.add_row(dm, "Çözümlenemedi", "-", "-", "-", "-")

            panels.append(Panel(geo_table, border_style="cyan", title="[ DOMAIN-INTEL OUTPUT ]", title_align="left"))
        else:
            console.print(f"{SARI}[*] Çıkarılabilir domain bulunamadı.{RENK_BITIR}")

        # ========= ADIM 5: WHOIS (bulunan domainler için) =========
        if self.extracted_domains:
            console.print(f"{CYAN}[*] ADIM 5/6 — WHOIS/RDAP kayıtları...{RENK_BITIR}")
            whois_mod = TrindroxWHOIS()
            for dm in self.extracted_domains[:3]:  # ilk 3 domain
                w_panel = await whois_mod.lookup(dm)
                panels.append(w_panel)

        # ========= ADIM 6: E-posta → Gravatar =========
        if self.extracted_emails:
            console.print(f"{CYAN}[*] ADIM 6/6 — E-posta + Gravatar taraması...{RENK_BITIR}")
            grav = TrindroxGravatar()
            for email in self.extracted_emails[:3]:
                # Email formatını temizle "Name <email@x.com>" → "email@x.com"
                em_match = EMAIL_REGEX.search(email)
                if em_match:
                    clean_email = em_match.group(0)
                    g_panel = await grav.lookup_by_email(clean_email)
                    panels.append(g_panel)

        # ========= ÖZET PANELİ =========
        summary_table = Table(title="[ FULL INTEL ÖZET RAPORU ]", title_style="bold magenta", expand=True)
        summary_table.add_column("Metrik", style="cyan")
        summary_table.add_column("Değer", style="white")
        summary_table.add_row("Hedef Kullanıcı Adı", f"[bold yellow]{self.target}[/bold yellow]")
        summary_table.add_row("Bulunan Platform", f"{YESIL}{len(self.found_platforms)}{RENK_BITIR}")
        summary_table.add_row("Bulunan E-posta", f"{SARI}{len(self.extracted_emails)}{RENK_BITIR}")
        summary_table.add_row("Çıkarılan Domain", f"{CYAN}{len(self.extracted_domains)}{RENK_BITIR}")
        summary_table.add_row("Çözümlenen IP", f"{YESIL}{len(self.resolved_ips)}{RENK_BITIR}")
        if self.resolved_ips:
            ip_str = ", ".join(self.resolved_ips.values()[:5])
            summary_table.add_row("IP Adresleri", ip_str)
        summary_table.add_row("Tarama Zamanı", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        panels.append(Panel(summary_table, border_style="magenta", title="[ FULL INTEL CHAIN COMPLETE ]", title_align="left"))
        return panels


# =====================================================================
# OSINT MENÜ SÜRÜCÜSÜ
# =====================================================================

def osint_menu():
    while True:
        console.print(Panel(
            "1. ★ FULL INTEL CHAIN ★ (Kullanıcı Adından HER ŞEY: Platform+GitHub+Domain+IP+WHOIS+Gravatar)\n"
            "2. Kullanıcı Adı İzi (52 Platform)\n"
            "3. GitHub Derin Analiz (UserID / Node ID / Commit E-postası)\n"
            "4. IP Locator & Konum Tespiti (Koordinat + Harita + Reverse DNS)\n"
            "5. WHOIS RDAP Kayıt Bilgisi (Anahtarsız Ücretsiz)\n"
            "6. Gravatar E-posta Profili (MD5 Hash + Bağlı Hesaplar)\n"
            "7. Telefon Numarası Analizi (Operatör / Hat Tipi)\n"
            "8. Dijital Parmak İzi + Sertifika Analizi (TLS / SHA-256)\n"
            "0. Ana Menüye Dön",
            title="[ OSINT CORE v2026.3 - M A R K Ø ]",
            border_style="magenta"
        ))
        secim = console.input("[bold magenta][?] OSINT modülü: [/]").strip()

        if secim == "1":
            hedef = console.input("[bold magenta][*] Hedef kullanıcı adı: [/]").strip().lstrip("@")
            if hedef:
                console.print(f"\n{MOR}{'='*60}{RENK_BITIR}")
                console.print(f"{MOR}[ FULL INTEL CHAIN BAŞLATILIYOR: {hedef} ]{RENK_BITIR}")
                console.print(f"{MOR}{'='*60}{RENK_BITIR}\n")
                intel = TrindroxFullIntel(hedef)
                panels = asyncio.run(intel.run())
                console.print("\n")
                for i, panel in enumerate(panels):
                    console.print(panel)
                    if i < len(panels) - 1:
                        console.print()

        elif secim == "2":
            hedef = console.input("[bold magenta][*] Hedef kullanıcı adı: [/]").strip().lstrip("@")
            if hedef:
                console.print(f"{SARI}[*] 52 platform taranıyor, bekleyin...{RENK_BITIR}")
                console.print(asyncio.run(TrindroxOSINT(hedef).scan_all()))

        elif secim == "3":
            hedef = console.input("[bold magenta][*] GitHub kullanıcı adı: [/]").strip()
            if hedef:
                console.print(f"{SARI}[*] GitHub API sorgulanıyor...{RENK_BITIR}")
                gh = TrindroxGitHub()
                result = asyncio.run(gh.deep_scan(hedef))
                if isinstance(result, tuple):
                    console.print(result[0])
                else:
                    console.print(result)

        elif secim == "4":
            hedef = console.input("[bold magenta][*] IP veya domain: [/]").strip()
            if hedef:
                console.print(f"{SARI}[*] Konum tespiti yapılıyor...{RENK_BITIR}")
                locator = TrindroxIPLocator()
                console.print(asyncio.run(locator.locate_panel(hedef)))

        elif secim == "5":
            hedef = console.input("[bold magenta][*] Domain (örn: example.com): [/]").strip()
            if hedef:
                console.print(f"{SARI}[*] RDAP/WHOIS sorgusu...{RENK_BITIR}")
                console.print(asyncio.run(TrindroxWHOIS().lookup(hedef)))

        elif secim == "6":
            hedef = console.input("[bold magenta][*] E-posta adresi: [/]").strip()
            if hedef:
                console.print(f"{SARI}[*] Gravatar profili çekiliyor...{RENK_BITIR}")
                console.print(asyncio.run(TrindroxGravatar().lookup_by_email(hedef)))

        elif secim == "7":
            hedef = console.input("[bold magenta][*] Telefon numarası (+90...): [/]").strip()
            if hedef:
                console.print(TrindroxPhone().analyze(hedef))

        elif secim == "8":
            hedef = console.input("[bold magenta][*] Hedef domain/site: [/]").strip()
            if hedef:
                console.print(f"{SARI}[*] Parmak izi ve sertifika çekiliyor...{RENK_BITIR}")
                console.print(asyncio.run(TrindroxFingerprint().fingerprint(hedef)))

        elif secim == "0":
            return
        else:
            console.print(f"{KIRMIZI}[!] Geçersiz seçim.{RENK_BITIR}")

        console.input("\n[dim][ Devam etmek için Enter... ][/dim]")
        console.clear()


# =====================================================================
# ANA SİSTEM ÇEKİRDEĞİ
# =====================================================================

class TrindroxCore:
    def __init__(self):
        self.version = "2026.3.0"
        self.codename = "M A R K Ø"
        self.status = "ONLINE"
        self.selected_menu = "MAIN"

    def generate_banner(self) -> Panel:
        now = datetime.now().strftime("%H:%M:%S")
        banner_text = Text()
        banner_text.append(f"====== TRINDROX UI v{self.version} ======\n", style="bold cyan")
        banner_text.append(f"     [ SİSTEM MİMARİSİ: {self.codename} ]\n", style="bold magenta")
        banner_text.append(f" STATUS: {self.status} | TIME: {now} | MODULE: {self.selected_menu}", style="green")
        return Panel(banner_text, border_style="blue", title="[ SYSTEM CORE ]", title_align="left")

    def generate_main_menu(self) -> Panel:
        table = Table(show_header=False, box=None, expand=True)
        table.add_column("No", style="bold yellow", justify="center", width=4)
        table.add_column("Modül", style="bold cyan")
        table.add_column("Açıklama", style="white")
        table.add_row("1", "OSINT CORE v2026.3", "[ ★ FULL INTEL CHAIN ★ / 52 Platform / WHOIS / Gravatar ]")
        table.add_row("2", "FIREWALL ANALYZER", "[ Ağ ve Güvenlik Duvarı Analizi ]")
        table.add_row("3", "SMS GATEWAY (SIM)", "[ Simülasyon - Gerçek İstek Atmaz ]")
        table.add_row("4", "HASH LAB", "[ Hash Analizi ve Wordlist Kırma ]")
        table.add_row("5", "OPSEC SHIELD", "[ Gizlilik ve Şifreleme Durumu ]")
        table.add_row("0", "ÇIKIŞ", "[ Sistemi Güvenle Kapat ]")
        return Panel(table, border_style="cyan", title="[ ANA KOMUTA PANELİ ]", title_align="left")

    async def start_interface(self):
        console.clear()
        while self.status == "ONLINE":
            console.print(self.generate_banner())
            console.print(self.generate_main_menu())
            secim = console.input("\n[bold blue][?] Modül seçimi: [/]").strip()

            if secim == "1":
                self.selected_menu = "OSINT"
                console.clear()
                console.print(self.generate_banner())
                osint_menu()
                self.selected_menu = "MAIN"

            elif secim == "2":
                self.selected_menu = "ANALYZER"
                console.clear()
                console.print(self.generate_banner())
                hedef = console.input("[bold magenta][*] Hedef host/domain: [/]").strip()
                if hedef:
                    console.print(f"{SARI}[*] Port taraması başlıyor (12 port)...{RENK_BITIR}")
                    console.print(await TrindroxAnalyzer(hedef).run_analysis())

            elif secim == "3":
                self.selected_menu = "SMS"
                console.clear()
                console.print(self.generate_banner())
                console.print(f"{SARI}[!] UYARI: Bu modül TAMAMEN SİMÜLASYONDUR, gerçek SMS gönderilmez.{RENK_BITIR}")
                tel = console.input("[bold magenta][*] Hedef hat (+90...): [/]").strip()
                adet = console.input("[bold magenta][*] Döngü sayısı [5]: [/]").strip()
                dongu = int(adet) if adet.isdigit() else 5
                console.print(await TrindroxSMS(tel, dongu).start_gateway())

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
                console.print(await TrindroxOpSec().check_security_status())

            elif secim == "0":
                self.status = "OFFLINE"
                return

            else:
                console.print(f"{KIRMIZI}[!] Geçersiz modül seçimi.{RENK_BITIR}")

            if secim != "1":
                console.input("\n[dim][ Devam etmek için Enter... ][/dim]")
                console.clear()


def terminate_and_clean_logs():
    console.print(f"\n{SARI}[*] Trindrox UI Kapatılıyor...{RENK_BITIR}")
    try:
        if os.path.exists("__pycache__"):
            import shutil
            shutil.rmtree("__pycache__")
            console.print(f"{YESIL}[+] Önbellek dizini imha edildi.{RENK_BITIR}")
    except Exception:
        pass
    console.print(Panel(
        Text("SİSTEM ÇEVRİMDIŞI\n\n[ M A R K Ø - 2026 ]", style="bold red", justify="center"),
        border_style="red"
    ))


if __name__ == "__main__":
    core_engine = TrindroxCore()
    try:
        asyncio.run(core_engine.start_interface())
        terminate_and_clean_logs()
    except KeyboardInterrupt:
        console.print("\n\n[bold red][!] Acil Durum Sinyali Alındı (Ctrl+C).[/bold red]")
        terminate_and_clean_logs()
        sys.exit(0)
