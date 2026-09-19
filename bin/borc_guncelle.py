#!/usr/bin/env python3
"""
Eşleşmiş ödemelerden öğrenci borç durumunu hesaplar.
Girdi:  veri/odemeler/*.json  +  veri/ogrenciler.json
Çıktı:  veri/durum/<donem>.json

FIFO mantığı: ödemeler tarihe göre sıralanır, en eski ödenmemiş aya atanır.

Kullanım:
  python3 bin/borc_guncelle.py
"""

import json
from datetime import datetime
from pathlib import Path

PROJE_KOK      = Path(__file__).parent.parent
OGRENCILER     = PROJE_KOK / "veri" / "ogrenciler.json"
ODEMELER_DIR   = PROJE_KOK / "veri" / "odemeler"
DURUM_DIR      = PROJE_KOK / "veri" / "durum"


# --- Yardımcılar ---

def tarih_parse(s: str) -> datetime:
    """DD.MM.YYYY → datetime"""
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return datetime.min


def fifo_ata(odemeler: list[dict], fee_months: list[str], aylik_aidat: float) -> dict:
    """
    Ödemeleri FIFO ile aylara atar.
    Ay durumu: tam | eksik | fazla | odenmedi
    """
    aylar = {m: {"beklenen": aylik_aidat, "odenen": 0.0, "durum": "odenmedi"}
             for m in fee_months}

    # Tarihe göre sırala, toplam tutarı kalan bakiye olarak tut
    kalan = sum(o["tutar"] for o in odemeler)

    for ay in fee_months:
        if kalan <= 0:
            break
        beklenen = aylik_aidat
        atanan = min(kalan, beklenen)
        aylar[ay]["odenen"] = atanan
        kalan -= atanan

    # Fazla ödeme: son aydan sonra hâlâ kalan varsa
    if kalan > 0:
        # son aya ekle (veya ayrı bir "fazla" alanı)
        son_ay = fee_months[-1]
        aylar[son_ay]["odenen"] += kalan

    # Durum etiketleri
    for ay, veri in aylar.items():
        o = veri["odenen"]
        b = veri["beklenen"]
        if o == 0:
            veri["durum"] = "odenmedi"
        elif o < b:
            veri["durum"] = "eksik"
        elif o == b:
            veri["durum"] = "tam"
        else:
            veri["durum"] = "fazla"

    return aylar


def karsilik_ay_sayisi(toplam_odenen: float, aylik_aidat: float) -> float:
    if aylik_aidat <= 0:
        return 0
    return round(toplam_odenen / aylik_aidat, 1)


def durum_etiketi(bakiye: float) -> str:
    if bakiye >= 0:
        return "ileride"
    if bakiye >= -290:
        return "1 ay geride"
    return f"{abs(int(bakiye // 290))} ay geride"


# --- Ana hesaplama ---

def hesapla():
    config     = json.loads(OGRENCILER.read_text(encoding="utf-8"))
    donem      = config["donem"]
    fee_months = config["fee_months"]
    ogrenciler = config["ogrenciler"]

    # Tüm eşleşmiş ödemeleri topla
    tum_odemeler: list[dict] = []
    for dosya in sorted(ODEMELER_DIR.glob("*.json")):
        veri = json.loads(dosya.read_text(encoding="utf-8"))
        tum_odemeler.extend(veri.get("islemler", []))

    # Öğrenciye göre grupla
    ogr_odemeler: dict[str, list] = {o["id"]: [] for o in ogrenciler}
    for odeme in tum_odemeler:
        e = odeme.get("eslestirme") or {}
        ogr_id = e.get("ogrenci_id")
        if ogr_id and ogr_id in ogr_odemeler:
            ogr_odemeler[ogr_id].append({
                "tarih":  odeme["tarih"],
                "tutar":  odeme["tutar"],
                "id":     odeme["id"],
                "aciklama": odeme.get("cocuk_temiz") or odeme.get("aciklama_ham", ""),
            })

    # Her öğrenci için durum hesapla
    sonuclar = []
    for ogr in ogrenciler:
        oid         = ogr["id"]
        aylik       = ogr["aylik_aidat"]
        beklenen    = ogr["toplam_beklenen"]
        odeme_listesi = sorted(ogr_odemeler[oid], key=lambda x: tarih_parse(x["tarih"]))
        toplam_odenen = sum(o["tutar"] for o in odeme_listesi)
        bakiye        = toplam_odenen - beklenen
        aylar         = fifo_ata(odeme_listesi, fee_months, aylik)

        sonuclar.append({
            "id":             oid,
            "ad":             ogr["ad"],
            "sinif":          ogr["sinif"],
            "aylik_aidat":    aylik,
            "toplam_beklenen": beklenen,
            "toplam_odenen":  round(toplam_odenen, 2),
            "bakiye":         round(bakiye, 2),
            "karsilik_ay":    karsilik_ay_sayisi(toplam_odenen, aylik),
            "durum":          durum_etiketi(bakiye),
            "aylar":          aylar,
            "odemeler":       odeme_listesi,
        })

    # Kaydet
    DURUM_DIR.mkdir(parents=True, exist_ok=True)
    cikti_dosya = DURUM_DIR / f"{donem}.json"
    cikti = {
        "donem":             donem,
        "hesaplama_tarihi":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "toplam_ogrenci":    len(sonuclar),
        "ogrenciler":        sonuclar,
    }
    cikti_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")

    # Özet ekrana
    print(f"\nDönem: {donem}  |  {len(sonuclar)} öğrenci\n")
    print(f"  {'Ad':<30} {'Beklenen':>10} {'Ödenen':>10} {'Bakiye':>10}  Durum")
    print("  " + "─" * 70)
    for s in sonuclar:
        print(f"  {s['ad']:<30} {s['toplam_beklenen']:>10,.0f} "
              f"{s['toplam_odenen']:>10,.0f} {s['bakiye']:>+10,.0f}  {s['durum']}")

    print(f"\n  → {cikti_dosya.relative_to(PROJE_KOK)}")


if __name__ == "__main__":
    hesapla()
