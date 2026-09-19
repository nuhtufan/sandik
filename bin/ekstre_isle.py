#!/usr/bin/env python3
"""
Vakıfbank ekstre Excel'ini parse eder.
Girdi:  gelen/<dosya>.xlsx
Çıktı:  veri/ham-odemeler/<dosya>.json

Kullanım:
  python3 bin/ekstre_isle.py gelen/ekstre.xlsx
  python3 bin/ekstre_isle.py          # gelen/ klasöründeki tüm .xlsx dosyaları
"""

import json
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path

PROJE_KOK = Path(__file__).parent.parent
GELEN_DIR = PROJE_KOK / "gelen"
CIKTI_DIR = PROJE_KOK / "veri" / "ham-odemeler"

# --- Temizleme ---

MONTHS = [
    "ocak", "şubat", "subat", "mart", "nisan", "mayıs", "mayis",
    "haziran", "temmuz", "ağustos", "agustos", "ekim", "kasım", "kasim",
    "aralık", "aralik",
]

NOISE_WORDS = [
    r"aidat[ıi]?(?:d[ıi]r)?", r"ay[ıi]dat[ıi]?(?:d[ıi]r)?",
    r"[oö]demes[iı](?:dir)?", r"[oö]deme(?:dir)?", r"odemesi?",
    r"[uü]creti?", r"yardım", r"yardim",
    r"ay[ıi]", r"okul", r"aile", r"birli[ğg][iı]", r"anaokul[u]?",
    r"o\.?a\.?b\.?", r"ad[ıi]na", r"için", r"fark",
    r"gelen\s+fast(?:\s+[oö]demes[iı])?",
    r"taraf[ıi]ndan\s+aktar[ıi]lan",
    r"hesaba\s+aktar[ıi]lan",
    r"minik\s+mucitler\s+s[ıi]n[ıi]f[ıi]",
    r"okul\s+aile\s+birli[ğg][iı]",
    r"tam\s+g[uü]n(?:\s+için)?",
    r"yar[ıi]m\s+g[uü]n",
    r"\bve\b",
]


def temizle_cocuk_adi(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()

    t = re.sub(r".+?[''`]DAN\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\([^)]*\)", "", t)
    t = re.sub(r"\([^)]*$", "", t)
    t = re.sub(r"20\d{2}(?=[a-zA-ZÇĞİÖŞÜçğışöüı])", "", t)
    t = re.sub(r"\b20\d{2}\b", "", t)

    for m in MONTHS:
        t = re.sub(r"\b" + m + r"\b", "", t, flags=re.IGNORECASE)

    t = re.sub(r"\b\d{7,}\b", "", t)

    for w in NOISE_WORDS:
        t = re.sub(r"\b" + w + r"\b", "", t, flags=re.IGNORECASE)

    t = re.sub(r"\b\d[a-z/][a-z]?\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d\s*ya[şs]\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"CEP-EFT\w*-\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*-+\s*-+\s*", " ", t)
    t = re.sub(r"^\s*[-_/]+\s*", "", t)
    t = re.sub(r"\s*[-_/]+\s*$", "", t)
    t = re.sub(r"^[.\s]+", "", t)
    t = t.rstrip("._-,;:")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_aciklama(aciklama: str) -> dict:
    """Açıklama metnini gonderen / cocuk_ham / banka üçlüsüne ayırır."""
    t = str(aciklama).strip()

    # Format 1: "GÖNDEREN 'DAN çocuk adı , Banka"
    m = re.match(r"(.+?)\s+[''`]DAN\s+(.+?)\s*,\s*(.+)", t)
    if m:
        return {
            "gonderen": m.group(1).strip(),
            "cocuk_ham": m.group(2).strip(),
            "banka": m.group(3).strip(),
        }

    # Format 2: "GÖNDEREN / çocuk adı"
    m2 = re.match(r"(.+?)\s*/\s*(.+)", t)
    if m2:
        return {
            "gonderen": m2.group(1).strip(),
            "cocuk_ham": m2.group(2).strip(),
            "banka": "",
        }

    # Format 3: Sadece açıklama metni
    return {"gonderen": "", "cocuk_ham": t, "banka": ""}


def islem_id(tarih: str, tutar: float, aciklama: str) -> str:
    ham = f"{tarih}|{tutar}|{aciklama}"
    return "ham-" + hashlib.md5(ham.encode()).hexdigest()[:8]


def excel_oku(dosya: Path) -> list[dict]:
    import openpyxl

    wb = openpyxl.load_workbook(dosya)
    ws = wb.active
    islemler = []

    for row in ws.iter_rows(values_only=True):
        tarih, aciklama, tutar, _ = (list(row) + [None, None, None, None])[:4]

        if not isinstance(tutar, (int, float)):
            continue
        if not aciklama or not tarih:
            continue

        tarih_str = str(tarih).strip()
        parsed = parse_aciklama(str(aciklama))
        cocuk_temiz = temizle_cocuk_adi(parsed["cocuk_ham"])

        islemler.append({
            "id": islem_id(tarih_str, tutar, str(aciklama)),
            "tarih": tarih_str,
            "tutar": float(tutar),
            "aciklama_ham": str(aciklama).strip(),
            "gonderen": parsed["gonderen"],
            "cocuk_ham": parsed["cocuk_ham"],
            "cocuk_temiz": cocuk_temiz,
            "banka": parsed["banka"],
            "eslestirme": None,  # ogrenci-eslestir takımı dolduracak
        })

    return islemler


def isle(dosya: Path) -> Path:
    print(f"→ İşleniyor: {dosya.name}")
    islemler = excel_oku(dosya)

    cikti = {
        "kaynak_dosya": dosya.name,
        "islem_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "toplam_islem": len(islemler),
        "islemler": islemler,
    }

    cikti_dosya = CIKTI_DIR / (dosya.stem + ".json")
    CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    cikti_dosya.write_text(
        json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✓ {len(islemler)} işlem → {cikti_dosya.relative_to(PROJE_KOK)}")
    return cikti_dosya


def main():
    if len(sys.argv) > 1:
        dosyalar = [Path(sys.argv[1])]
    else:
        dosyalar = sorted(GELEN_DIR.glob("*.xlsx"))
        if not dosyalar:
            print("gelen/ klasöründe .xlsx dosyası yok.")
            sys.exit(0)

    for dosya in dosyalar:
        if not dosya.exists():
            print(f"✗ Dosya bulunamadı: {dosya}")
            continue
        isle(dosya)


if __name__ == "__main__":
    main()
