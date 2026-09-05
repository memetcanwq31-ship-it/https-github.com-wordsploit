# SMS Fudos simulator - harmless simulation plugin
TOOL_NAME = "SMS Fudos (simülasyon)"
TOOL_DESC = "Eğitim amaçlı SMS 'Fudos' davranışı simülasyonu. Gerçek SMS gönderilmez; sadece localhost backend ile iletişim kurar."

from tools.tool_client import send_command


def run(ctx):
    logger = ctx.get("logger")
    print("UYARI: Bu bir simülasyondur. Gerçek SMS gönderimi yapılmaz.")
    target = input("Hedef telefon numarası (örnek): ").strip() or "0000000000"
    message = input("Mesaj içeriği (örnek): ").strip() or "[SIM] Test mesajı"
    repeats_raw = input("Kaç tekrar (sayı, simüle edilecek): ").strip() or "1"
    try:
        repeats = int(repeats_raw)
        if repeats < 1:
            repeats = 1
    except Exception:
        repeats = 1

    # Safety: never accept remote IPs or real gateways. Only localhost backend is used.
    payload = {
        "target": target,
        "message": message,
        "repeats": repeats
    }

    print(f"\n[Simülasyon] {repeats} adet mesaj gönderiliyormuş gibi davranılıyor...\n")
    # show incremental simulated progress
    for i in range(1, repeats+1):
        print(f"[SIM] ({i}/{repeats}) -> {target}: {message}")

    # Send record to local backend for logging/simulation
    resp = send_command(TOOL_NAME, payload)
    if isinstance(resp, dict) and resp.get("status") == "ok":
        print("\n[backend] Simülasyon kaydı oluşturuldu.")
        print(resp.get("result"))
        logger.info("SMS Fudos simülasyonu: %s repeats to %s", repeats, target)
    elif isinstance(resp, dict) and resp.get("error") == "backend_unavailable":
        print("\n[!] Backend sunucusu bulunamadı. Lütfen backend_server.py'nin çalıştığından emin olun (127.0.0.1:9999).")
        logger.warning("Backend unavailable when running SMS Fudos simulator")
    else:
        print("\n[!] Backend ile iletişimde bir hata oluştu:", resp)
        logger.warning("Backend error: %s", resp)
