# Basit, zararsız OSINT mock eklentisi (örnek)
TOOL_NAME = "OSINT Mock (örnek)"
TOOL_DESC = "Gerçek dışı örnek verilerle OSINT simülasyonu yapar. Hiçbir gerçek dışı sorgu yapılmaz."

def run(ctx):
    name = input("Araştırılacak isim veya kullanıcı adı (örnek): ").strip()
    if not name:
        print("Girdi yok, çıkılıyor.")
        return
    print(f"\n{name} için örnek OSINT sonuçları (mock):")
    print("- Hesap bulunamadı (bu bir örnektir).")
    print("- Coğrafi veri: 41.01, 28.97 (örnek, doğrulanmamış).")
    print("- Bağlantılar: twitter.com/example, github.com/example")
    ctx.get("logger").info("OSINT mock ran for %s", name)
