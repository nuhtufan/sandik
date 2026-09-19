#!/usr/bin/env python3
"""
Borç durumundan Markdown raporlar üretir.
Girdi:  veri/durum/<donem>.json
Çıktı:  cikti/<donem>-ozet.md
        cikti/<donem>-borclu.md
        cikti/<donem>-ogrenci-<id>.md  (--kisi <id> ile)

Kullanım:
  python3 bin/rapor_uret.py                    # özet + borçlular
  python3 bin/rapor_uret.py --kisi 001         # tek öğrenci raporu
  python3 bin/rapor_uret.py --hepsi            # tüm raporlar
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJE_KOK  = Path(__file__).parent.parent
DURUM_DIR  = PROJE_KOK / "veri" / "durum"
CIKTI_DIR  = PROJE_KOK / "cikti"

AY_ADLARI = {
    "01": "Ocak",   "02": "Şubat",  "03": "Mart",
    "04": "Nisan",  "05": "Mayıs",  "06": "Haziran",
    "07": "Temmuz", "08": "Ağustos","09": "Eylül",
    "10": "Ekim",   "11": "Kasım",  "12": "Aralık",
}

DURUM_EMOJI = {
    "tam":      "✅",
    "eksik":    "🟡",
    "fazla":    "💚",
    "odenmedi": "❌",
}


def ay_adi(kod: str) -> str:
    """2023-02 → Şubat 2023"""
    yil, ay = kod.split("-")
    return f"{AY_ADLARI[ay]} {yil}"


def para(tutar: float) -> str:
    return f"{tutar:,.0f} TL".replace(",", ".")


def son_durum_dosya() -> Path:
    dosyalar = sorted(DURUM_DIR.glob("*.json"))
    if not dosyalar:
        print("veri/durum/ klasöründe dosya yok. Önce: python3 bin/borc_guncelle.py")
        sys.exit(1)
    return dosyalar[-1]


# ─── Rapor 1: Dönem Özeti ────────────────────────────────────────────────────

def rapor_ozet(veri: dict) -> str:
    donem     = veri["donem"]
    tarih     = veri["hesaplama_tarihi"]
    ogrenciler = veri["ogrenciler"]

    toplam_beklenen = sum(o["toplam_beklenen"] for o in ogrenciler)
    toplam_odenen   = sum(o["toplam_odenen"]   for o in ogrenciler)
    toplam_bakiye   = toplam_odenen - toplam_beklenen

    # Tüm fee_months'u topla
    tum_aylar: set[str] = set()
    for o in ogrenciler:
        tum_aylar.update(o["aylar"].keys())
    fee_months = sorted(tum_aylar)

    satirlar = [
        f"# {donem} Dönem Özeti",
        f"",
        f"_Hesaplama: {tarih}_",
        f"",
        f"## Genel Durum",
        f"",
        f"| | |",
        f"|---|---|",
        f"| Toplam öğrenci | {len(ogrenciler)} |",
        f"| Toplam beklenen | {para(toplam_beklenen)} |",
        f"| Toplam ödenen | {para(toplam_odenen)} |",
        f"| Toplam bakiye | {para(toplam_bakiye)} |",
        f"| Tahsilat oranı | %{100*toplam_odenen/toplam_beklenen:.1f} |",
        f"",
        f"## Ay Ay Durum",
        f"",
        f"| Ay | ✅ Tam | 🟡 Eksik | ❌ Ödemedi | Gelen |",
        f"|---|---|---|---|---|",
    ]

    for ay in fee_months:
        tam = eksik = odenmedi = 0
        gelen = 0.0
        for o in ogrenciler:
            ay_veri = o["aylar"].get(ay, {})
            d = ay_veri.get("durum", "odenmedi")
            if d in ("tam", "fazla"):
                tam += 1
            elif d == "eksik":
                eksik += 1
            else:
                odenmedi += 1
            gelen += ay_veri.get("odenen", 0)
        satirlar.append(
            f"| {ay_adi(ay)} | {tam} | {eksik} | {odenmedi} | {para(gelen)} |"
        )

    satirlar += [
        f"",
        f"## Öğrenci Listesi",
        f"",
        f"| Öğrenci | Sınıf | Beklenen | Ödenen | Bakiye | Durum |",
        f"|---|---|---|---|---|---|",
    ]

    for o in sorted(ogrenciler, key=lambda x: x["bakiye"]):
        satirlar.append(
            f"| {o['ad']} | {o['sinif']} | {para(o['toplam_beklenen'])} "
            f"| {para(o['toplam_odenen'])} | {para(o['bakiye'])} | {o['durum']} |"
        )

    return "\n".join(satirlar)


# ─── Rapor 2: Borçlular Listesi ──────────────────────────────────────────────

def rapor_borclu(veri: dict) -> str:
    donem      = veri["donem"]
    tarih      = veri["hesaplama_tarihi"]
    ogrenciler = veri["ogrenciler"]

    borclu  = sorted([o for o in ogrenciler if o["bakiye"] < 0],
                     key=lambda x: x["bakiye"])
    ileride = [o for o in ogrenciler if o["bakiye"] >= 0]

    satirlar = [
        f"# {donem} Borçlular Listesi",
        f"",
        f"_Hesaplama: {tarih}_",
        f"",
        f"**Toplam borçlu:** {len(borclu)} öğrenci  "
        f"| **Toplam borç:** {para(sum(o['bakiye'] for o in borclu))}",
        f"",
        f"## Borçlu Öğrenciler",
        f"",
        f"| # | Öğrenci | Sınıf | Ödenen | Borç | Durum |",
        f"|---|---|---|---|---|---|",
    ]

    for i, o in enumerate(borclu, 1):
        satirlar.append(
            f"| {i} | {o['ad']} | {o['sinif']} "
            f"| {para(o['toplam_odenen'])} | {para(abs(o['bakiye']))} | {o['durum']} |"
        )

    if ileride:
        satirlar += [
            f"",
            f"## İleride Öğrenciler",
            f"",
            f"| Öğrenci | Sınıf | Fazla Ödeme |",
            f"|---|---|---|",
        ]
        for o in ileride:
            satirlar.append(
                f"| {o['ad']} | {o['sinif']} | {para(o['bakiye'])} |"
            )

    return "\n".join(satirlar)


# ─── Rapor 3: Kişi Bazlı ─────────────────────────────────────────────────────

def rapor_kisi(veri: dict, ogr_id: str) -> str:
    donem = veri["donem"]
    tarih = veri["hesaplama_tarihi"]
    ogr   = next((o for o in veri["ogrenciler"] if o["id"] == ogr_id), None)

    if not ogr:
        return f"# Öğrenci bulunamadı: {ogr_id}"

    satirlar = [
        f"# {ogr['ad']} — {donem} Borç Durumu",
        f"",
        f"_Hesaplama: {tarih}_",
        f"",
        f"| | |",
        f"|---|---|",
        f"| Sınıf | {ogr['sinif']} |",
        f"| Aylık aidat | {para(ogr['aylik_aidat'])} |",
        f"| Toplam beklenen | {para(ogr['toplam_beklenen'])} |",
        f"| Toplam ödenen | {para(ogr['toplam_odenen'])} |",
        f"| Bakiye | {para(ogr['bakiye'])} |",
        f"| Durum | {ogr['durum']} |",
        f"",
        f"## Aylık Tablo",
        f"",
        f"| Ay | Beklenen | Ödenen | Durum |",
        f"|---|---|---|---|",
    ]

    for ay, av in ogr["aylar"].items():
        emoji = DURUM_EMOJI.get(av["durum"], "❓")
        satirlar.append(
            f"| {ay_adi(ay)} | {para(av['beklenen'])} "
            f"| {para(av['odenen'])} | {emoji} {av['durum']} |"
        )

    if ogr["odemeler"]:
        satirlar += [
            f"",
            f"## Ödeme Geçmişi",
            f"",
            f"| Tarih | Tutar | Açıklama |",
            f"|---|---|---|",
        ]
        for od in ogr["odemeler"]:
            satirlar.append(
                f"| {od['tarih']} | {para(od['tutar'])} | {od['aciklama']} |"
            )
    else:
        satirlar += ["", "_Kayıtlı ödeme yok._"]

    return "\n".join(satirlar)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    args     = sys.argv[1:]
    kisi_id  = None
    hepsi    = "--hepsi" in args

    if "--kisi" in args:
        idx = args.index("--kisi")
        kisi_id = args[idx + 1] if idx + 1 < len(args) else None

    dosya = son_durum_dosya()
    veri  = json.loads(dosya.read_text(encoding="utf-8"))
    donem = veri["donem"]

    CIKTI_DIR.mkdir(parents=True, exist_ok=True)

    if kisi_id:
        icerik = rapor_kisi(veri, kisi_id)
        hedef  = CIKTI_DIR / f"{donem}-ogrenci-{kisi_id}.md"
        hedef.write_text(icerik, encoding="utf-8")
        print(f"✓ {hedef.relative_to(PROJE_KOK)}")

    elif hepsi:
        for hedef, icerik in [
            (CIKTI_DIR / f"{donem}-ozet.md",   rapor_ozet(veri)),
            (CIKTI_DIR / f"{donem}-borclu.md", rapor_borclu(veri)),
        ]:
            hedef.write_text(icerik, encoding="utf-8")
            print(f"✓ {hedef.relative_to(PROJE_KOK)}")

        for ogr in veri["ogrenciler"]:
            hedef = CIKTI_DIR / f"{donem}-ogrenci-{ogr['id']}.md"
            hedef.write_text(rapor_kisi(veri, ogr["id"]), encoding="utf-8")
            print(f"✓ {hedef.relative_to(PROJE_KOK)}")

    else:
        for hedef, icerik in [
            (CIKTI_DIR / f"{donem}-ozet.md",   rapor_ozet(veri)),
            (CIKTI_DIR / f"{donem}-borclu.md", rapor_borclu(veri)),
        ]:
            hedef.write_text(icerik, encoding="utf-8")
            print(f"✓ {hedef.relative_to(PROJE_KOK)}")


if __name__ == "__main__":
    main()
