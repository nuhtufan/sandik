# excel-parse

Vakıfbank ekstre Excel dosyasını okur, her satırı yapısal veriye dönüştürür.

## Ne yapar
1. Excel'deki `İşlem Tarihi | Açıklama | İşlem Tutarı | Yeni Bakiye` satırlarını okur
2. Açıklama metnini üç parçaya ayırır: **gönderen**, **çocuk_ham**, **banka**
3. Çocuk adındaki gürültüyü temizler (ay isimleri, yıl, aidat/ödeme kelimeleri)
4. Her işleme tekil `id` üretir (tarih+tutar+açıklama hash'i)
5. `eslestirme: null` alanını boş bırakır — `ogrenci-eslestir` takımı dolduracak

## Açıklama formatları
| Format | Örnek |
|---|---|
| `GÖNDEREN 'DAN çocuk , Banka` | `ALİ AYDOĞDU 'DAN alya aydoğdu , Vakıflar Bankası` |
| `GÖNDEREN / çocuk` | `ZEKİ ÇALIŞ / DEFNE ÇALIŞ` |
| Serbest metin | `EGE ALTON ŞUBAT AYI ÖDEMESİ` |

## Çalıştırma
```bash
# Tek dosya
python3 bin/ekstre_isle.py gelen/ekstre.xlsx

# gelen/ klasöründeki tümü
python3 bin/ekstre_isle.py
```

## Girdi
`gelen/*.xlsx` — Vakıfbank "Vadesiz Hesap Detay Bilgileri" formatı

## Çıktı
`veri/ham-odemeler/<dosya_adi>.json`

```json
{
  "kaynak_dosya": "ekstre.xlsx",
  "islem_tarihi": "2024-09-19 10:00",
  "toplam_islem": 148,
  "islemler": [
    {
      "id": "ham-a1b2c3d4",
      "tarih": "01.02.2023",
      "tutar": 290.0,
      "aciklama_ham": "ALİ AYDOĞDU 'DAN alya aydoğdu , Türkiye Vakıflar Bankası",
      "gonderen": "ALİ AYDOĞDU",
      "cocuk_ham": "alya aydoğdu",
      "cocuk_temiz": "alya aydoğdu",
      "banka": "Türkiye Vakıflar Bankası",
      "eslestirme": null
    }
  ]
}
```

## Sınırlar
- Yalnızca Vakıfbank formatı desteklenir
- Gönderen adı bazen çocuk adıyla aynıdır (banka otomatik yazar) — eşleştirme bu skille değil, `isim-eslestir` ile yapılır
- Açıklama 255 karakterde kesik gelebilir (Excel hücresi limiti)
