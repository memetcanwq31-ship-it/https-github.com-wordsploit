MarkOS (SAFE) - Kullanım ve eklenti rehberi

- Bu paket zararsız örnekler içerir. Kötüye kullanım veya saldırı amaçlı araçlar içermez.
- tools/ dizinine yeni bir eklenti eklemek için:
   1) Yeni .py dosyası oluşturun.
   2) TOOL_NAME, TOOL_DESC değişkenlerini tanımlayın.
   3) run(ctx) fonksiyonunu sağlayın. ctx içinde data_sources ve logger bulunur.

- Örnek eklentiler:
   - simulate_port_scan.py : sadece localhost taraması (eğitim amaçlı).
   - osint_mock.py : gerçek sorgu yapmayan örnek OSINT çıktısı.

- Çalıştırma:
   python3 markos_safe.py
