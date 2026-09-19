#!/usr/bin/env python3
"""
Ham ödemeleri öğrenci kaydıyla eşleştirir.
Girdi:  veri/ham-odemeler/*.json
Çıktı:  veri/odemeler/*.json       (yüksek güven, otomatik eşleşti)
        veri/bekleyen/*.json       (düşük güven, insan onayı bekliyor)

Kullanım:
  python3 bin/ogrenci_eslestir.py
  python3 bin/ogrenci_eslestir.py veri/ham-odemeler/ekstre-2023-02.json
"""

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

PROJE_KOK = Path(__file__).parent.parent
OGRENCILER_DOSYA = PROJE_KOK / "veri" / "ogrenciler.json"
HAM_DIR = PROJE_KOK / "veri" / "ham-odemeler"
ODEMELER_DIR = PROJE_KOK / "veri" / "odemeler"
BEKLEYEN_DIR = PROJE_KOK / "veri" / "bekleyen"

GUVEN_YUKSEK = 0.82   # otomatik eşleştir
GUVEN_DUSUK  = 0.50   # bekleyene al


# --- Benzerlik ---

def normalize(s: str) -> str:
    return (s.lower()
            .replace("ş", "s").replace("ç", "c").replace("ğ", "g")
            .replace("ü", "u").replace("ö", "o").replace("ı", "i")
            .replace("İ", "i").strip())


def benzerlik(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def en_iyi_eslesme(metin: str, aday_listesi: list[tuple]) -> tuple:
    """
    aday_listesi: [(skor, ogrenci_id, eslestirme_yolu), ...]
    Döndürür: (en_yüksek_skor, ogrenci_id, yol)
    """
    en_iyi = (0.0, None, None)
    for (skor, ogr_id, yol) in aday_listesi:
        if skor > en_iyi[0]:
            en_iyi = (skor, ogr_id, yol)
    return en_iyi


# --- Ana eşleştirme mantığı ---

def isle_islem(islem: dict, ogrenciler: list) -> dict:
    """
    Öncelik sırası:
    1. cocuk_temiz  → öğrenci adı
    2. gonderen     → veli adı
    3. cocuk_temiz  → veli adı   (açıklama otomatik veli adı yazmışsa)
    """
    adaylar = []

    for ogr in ogrenciler:
        ogr_ad = ogr["ad"]
        ogr_id = ogr["id"]

        # 1. Çocuk adıyla eşleştir
        if islem.get("cocuk_temiz"):
            s = benzerlik(islem["cocuk_temiz"], ogr_ad)
            adaylar.append((s, ogr_id, "cocuk_temiz→ogrenci_ad"))

        # 2. Gönderen adını veli adıyla eşleştir
        for veli in ogr.get("veliler", []):
            if islem.get("gonderen"):
                s = benzerlik(islem["gonderen"], veli)
                adaylar.append((s, ogr_id, f"gonderen→veli({veli})"))

            # 3. Açıklamada veli adı otomatik yazılmışsa
            if islem.get("cocuk_temiz"):
                s = benzerlik(islem["cocuk_temiz"], veli)
                adaylar.append((s, ogr_id, f"cocuk_temiz→veli({veli})"))

    skor, ogr_id, yol = en_iyi_eslesme("", adaylar)

    return {
        "ogrenci_id": ogr_id,
        "guven": round(skor, 3),
        "yol": yol,
    }


# --- Pipeline ---

def eslestir(ham_dosya: Path):
    ogrenciler = json.loads(OGRENCILER_DOSYA.read_text(encoding="utf-8"))["ogrenciler"]
    veri = json.loads(ham_dosya.read_text(encoding="utf-8"))
    islemler = veri["islemler"]

    otomatik = []
    bekleyen = []
    eslesmeyen = []

    for islem in islemler:
        eslestirme = isle_islem(islem, ogrenciler)
        islem["eslestirme"] = eslestirme

        guven = eslestirme["guven"]
        if guven >= GUVEN_YUKSEK:
            otomatik.append(islem)
        elif guven >= GUVEN_DUSUK:
            bekleyen.append(islem)
        else:
            eslesmeyen.append(islem)

    # --- Çıktılar ---
    ODEMELER_DIR.mkdir(parents=True, exist_ok=True)
    BEKLEYEN_DIR.mkdir(parents=True, exist_ok=True)

    stem = ham_dosya.stem

    if otomatik:
        cikti = {**veri, "islemler": otomatik, "durum": "otomatik"}
        (ODEMELER_DIR / f"{stem}.json").write_text(
            json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if bekleyen or eslesmeyen:
        cikti_b = {**veri, "islemler": bekleyen + eslesmeyen, "durum": "bekleyen"}
        (BEKLEYEN_DIR / f"{stem}.json").write_text(
            json.dumps(cikti_b, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\n{'─'*55}")
    print(f"  Kaynak     : {ham_dosya.name}")
    print(f"  Toplam     : {len(islemler)}")
    print(f"  ✅ Otomatik : {len(otomatik)}")
    print(f"  🟡 Bekleyen : {len(bekleyen)}")
    print(f"  ❌ Eşleşmedi: {len(eslesmeyen)}")
    print(f"{'─'*55}")

    # Bekleyenleri göster
    if bekleyen:
        print("\n  İnsan onayı gerekenler:")
        for i in bekleyen:
            e = i["eslestirme"]
            ogr = next((o for o in ogrenciler if o["id"] == e["ogrenci_id"]), {})
            print(f"  [{e['guven']:.2f}] {i['cocuk_temiz'] or i['gonderen']!r}"
                  f" → {ogr.get('ad','?')} ({e['yol']})")

    if eslesmeyen:
        print("\n  Eşleşmeyen (manuel bakılacak):")
        for i in eslesmeyen:
            print(f"  [----] {i['cocuk_temiz']!r} / gönderen: {i['gonderen']!r}")


def main():
    if len(sys.argv) > 1:
        dosyalar = [Path(sys.argv[1])]
    else:
        dosyalar = sorted(HAM_DIR.glob("*.json"))
        if not dosyalar:
            print("veri/ham-odemeler/ klasöründe dosya yok.")
            sys.exit(0)

    for d in dosyalar:
        eslestir(d)


if __name__ == "__main__":
    main()
