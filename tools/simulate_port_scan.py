# Zararsız port tarayıcı simülatörü - SADECE LOCALHOST'a izin verir
TOOL_NAME = "Simüle Port Tarayıcı (localhost only)"
TOOL_DESC = "Eğitim amaçlı: localhost üzerinde belirtilen portları kontrol eder (bağlanma simülasyonu)."

import socket
import time

def run(ctx):
    logger = ctx.get("logger")
    print("UYARI: Bu araç yalnızca yerel makinede (localhost) eğitim amaçlıdır.")
    target = input("Hedef (varsayılan: localhost): ").strip() or "localhost"
    if target not in ("localhost", "127.0.0.1"):
        print("Güvenlik nedeniyle yalnızca localhost taraması izinli.")
        return
    ports_raw = input("Kontrol edilecek portları virgül ile ayırın (örnek: 22,80,443) veya aralık (1000-1010): ").strip()
    ports = []
    try:
        if "-" in ports_raw:
            a,b = ports_raw.split("-",1)
            ports = list(range(int(a), int(b)+1))
        else:
            ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
    except Exception as e:
        print("Port listesi çözümlenemedi.")
        return

    for port in ports:
        # Gerçek TCP bağlanması yapmıyoruz; sadece kısa bir socket denemesi ile local testi yapabiliriz.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        try:
            res = s.connect_ex(("127.0.0.1", port))
            if res == 0:
                print(f"[OPEN] Port {port} - localhost üzerinde dinleniyor olabilir.")
            else:
                print(f"[CLOSED] Port {port}")
        except Exception:
            print(f"[?] Port {port} hakkında bilgi alınamadı.")
        finally:
            s.close()
        time.sleep(0.05)
    logger.info("Simulated scan finished for localhost")
