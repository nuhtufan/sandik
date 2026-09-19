# Sandık — Claude için Proje Bağlamı

OAB (Okul Aile Birliği) aidat takip sistemi.
Vakıfbank ekstre Excel'lerini alır, öğrenci eşleştirmesi yapar, borç durumu hesaplar, raporlar üretir.

## Çalışma Şekli

AI engineer gibi davran — kısa, direkt, teknik. Büyük bir işe başlamadan önce yol haritası çıkar ve onay al. Mimari belirsizlik varsa tahminle devam etme, sor.

## Repo

- GitHub: https://github.com/nuhtufan/sandik
- A Şirketi referans projesi: https://github.com/selmakcby/a-sirketi

## Tamamlanan Fazlar

| Faz | Dosya | Ne yapar |
|---|---|---|
| 0 | veri/ogrenciler.json | İskelet, veri modeli |
| 1 | bin/ekstre_isle.py | Vakıfbank Excel → veri/ham-odemeler/*.json |
| 2 | bin/ogrenci_eslestir.py | Ham ödemeleri öğrenciyle eşleştir (fuzzy) |
| 3 | bin/borc_guncelle.py | FIFO borç hesaplama, aylık breakdown |
| 4 | bin/rapor_uret.py | özet / borçlular / kişi bazlı Markdown raporlar |
| 5 | bin/pipeline.py | Tüm adımları tek komutla çalıştırır |
| 5 | bin/telegram_bot.py | xlsx gönder → pipeline → raporlar döner |

## Veri Akışı

```
gelen/*.xlsx
  → bin/ekstre_isle.py      → veri/ham-odemeler/*.json
  → bin/ogrenci_eslestir.py → veri/odemeler/*.json
                              veri/bekleyen/*.json      ← insan onayı
  → bin/borc_guncelle.py    → veri/durum/<donem>.json
  → bin/rapor_uret.py       → cikti/*.md
```

Tek komut: `python3 bin/pipeline.py`

## Kritik Tasarım Kararları

**Dönem:** Eylül–Haziran (10 ay). Kayıt Temmuz'da başlar, ilk aidat o an alınır → FIFO ile Eylül'e atanır.

**Eşleştirme önceliği:**
1. `cocuk_temiz` → öğrenci adı
2. `gonderen` → veli adı
3. `cocuk_temiz` → veli adı (banka otomatik veli adı yazmışsa)
4. Güven < 0.50 → `veri/bekleyen/` → insan onayı

**Güven eşikleri:** ≥ 0.82 otomatik · 0.50–0.82 bekleyen · < 0.50 eşleşmedi

**Takip modeli:** Kümülatif (kesin doğru) + aylık FIFO (kümülatiften türetilmiş)

## Mevcut Durum

- `veri/ogrenciler.json` → 15 test öğrenci var, gerçek liste henüz girilmedi
- Gerçek liste girilince eşleştirme oranı %12'den çok yukarı çıkar
- `veri/bekleyen/` insan onayı akışı Telegram'a henüz bağlanmadı
- `.env` → `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` girilmeli

## Sonraki Adımlar

1. `veri/ogrenciler.json`'a gerçek öğrenci listesini gir
2. `.env` doldur, `python3 bin/telegram_bot.py` çalıştır
3. `bekleyen/` onay akışını Telegram'a bağla

## Komutlar

```bash
python3 bin/pipeline.py                          # tam pipeline
python3 bin/ekstre_isle.py gelen/ekstre.xlsx     # sadece parse
python3 bin/ogrenci_eslestir.py                  # sadece eşleştir
python3 bin/borc_guncelle.py                     # sadece borç hesapla
python3 bin/rapor_uret.py                        # özet + borçlular
python3 bin/rapor_uret.py --kisi 001             # tek öğrenci
python3 bin/rapor_uret.py --hepsi                # tüm raporlar
python3 bin/telegram_bot.py                      # botu başlat
```
