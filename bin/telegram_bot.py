#!/usr/bin/env python3
"""
Sandık Telegram Botu — uzun yoklama (long polling)

Komutlar:
  /ozet              → dönem özet raporu
  /borclu            → borçlular listesi
  /ogrenci <ad|id>   → kişi bazlı rapor
  /pipeline          → mevcut gelen/ dosyalarını işle
  /yardim            → komut listesi

Dosya gönderme:
  .xlsx dosyası gönder → pipeline çalışır, raporlar döner

Kullanım:
  python3 bin/telegram_bot.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

PROJE_KOK = Path(__file__).parent.parent
BIN       = PROJE_KOK / "bin"
CIKTI_DIR = PROJE_KOK / "cikti"
GELEN_DIR = PROJE_KOK / "gelen"
DURUM_DIR = PROJE_KOK / "veri" / "durum"


# ─── .env yükleyici ──────────────────────────────────────────────────────────

def env_yukle() -> dict:
    env_dosya = PROJE_KOK / ".env"
    env = {}
    if env_dosya.exists():
        for satir in env_dosya.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir and not satir.startswith("#") and "=" in satir:
                k, v = satir.split("=", 1)
                env[k.strip()] = v.strip()
    # Gerçek env değişkenleri .env'yi geçersiz kılar
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


ENV      = env_yukle()
TOKEN    = ENV.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID  = ENV.get("TELEGRAM_CHAT_ID", "")   # boşsa herkese cevap ver
API_BASE = f"https://api.telegram.org/bot{TOKEN}"


# ─── Telegram API ─────────────────────────────────────────────────────────────

def api(metod: str, **kwargs) -> dict:
    r = requests.post(f"{API_BASE}/{metod}", json=kwargs, timeout=30)
    return r.json()


def mesaj_gonder(chat_id: str | int, metin: str):
    api("sendMessage", chat_id=chat_id, text=metin, parse_mode="Markdown")


def dosya_gonder(chat_id: str | int, dosya: Path):
    with open(dosya, "rb") as f:
        requests.post(
            f"{API_BASE}/sendDocument",
            data={"chat_id": chat_id},
            files={"document": (dosya.name, f)},
            timeout=60,
        )


def dosya_indir(file_id: str, hedef: Path):
    r   = api("getFile", file_id=file_id)
    yol = r["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{TOKEN}/{yol}"
    veri = requests.get(url, timeout=60).content
    hedef.write_bytes(veri)


# ─── Pipeline çalıştırıcı ─────────────────────────────────────────────────────

def pipeline_calistir(xlsx: Path | None = None) -> str:
    args = [sys.executable, str(BIN / "pipeline.py")]
    if xlsx:
        args.append(str(xlsx))
    sonuc = subprocess.run(args, cwd=PROJE_KOK, capture_output=True, text=True)
    return sonuc.stdout + sonuc.stderr


def son_durum() -> dict | None:
    dosyalar = sorted(DURUM_DIR.glob("*.json"))
    if not dosyalar:
        return None
    return json.loads(dosyalar[-1].read_text(encoding="utf-8"))


# ─── Komut işleyiciler ────────────────────────────────────────────────────────

def cmd_ozet(chat_id):
    dosya = sorted(CIKTI_DIR.glob("*-ozet.md"))
    if not dosya:
        mesaj_gonder(chat_id, "❌ Henüz rapor yok. Önce bir ekstre gönderin.")
        return
    metin = dosya[-1].read_text(encoding="utf-8")
    mesaj_gonder(chat_id, metin[:4000])


def cmd_borclu(chat_id):
    dosya = sorted(CIKTI_DIR.glob("*-borclu.md"))
    if not dosya:
        mesaj_gonder(chat_id, "❌ Henüz rapor yok. Önce bir ekstre gönderin.")
        return
    metin = dosya[-1].read_text(encoding="utf-8")
    mesaj_gonder(chat_id, metin[:4000])


def cmd_ogrenci(chat_id, sorgu: str):
    veri = son_durum()
    if not veri:
        mesaj_gonder(chat_id, "❌ Henüz veri yok.")
        return

    sorgu_lower = sorgu.lower()
    ogr = next(
        (o for o in veri["ogrenciler"]
         if o["id"] == sorgu or sorgu_lower in o["ad"].lower()),
        None,
    )

    if not ogr:
        mesaj_gonder(chat_id, f"❌ '{sorgu}' bulunamadı.")
        return

    dosya = sorted(CIKTI_DIR.glob(f"*-ogrenci-{ogr['id']}.md"))
    if not dosya:
        mesaj_gonder(chat_id, "❌ Rapor dosyası yok. Önce pipeline çalıştırın.")
        return

    metin = dosya[-1].read_text(encoding="utf-8")
    mesaj_gonder(chat_id, metin[:4000])


def cmd_pipeline(chat_id):
    mesaj_gonder(chat_id, "⏳ Pipeline çalışıyor...")
    log = pipeline_calistir()
    mesaj_gonder(chat_id, f"✅ Tamamlandı.\n\n```\n{log[-1500:]}\n```")
    cmd_ozet(chat_id)


def cmd_yardim(chat_id):
    mesaj_gonder(chat_id, (
        "*Sandık Bot Komutları*\n\n"
        "/ozet — dönem özet raporu\n"
        "/borclu — borçlular listesi\n"
        "/ogrenci <ad veya id> — kişi bazlı rapor\n"
        "/pipeline — gelen/ dosyalarını işle\n"
        "/yardim — bu mesaj\n\n"
        "📎 Ekstre (.xlsx) göndererek de pipeline başlatabilirsiniz."
    ))


def xlsx_isle(chat_id, file_id: str, dosya_adi: str):
    hedef = GELEN_DIR / dosya_adi
    mesaj_gonder(chat_id, f"📥 '{dosya_adi}' alındı, işleniyor...")

    try:
        dosya_indir(file_id, hedef)
        log = pipeline_calistir(hedef)
        mesaj_gonder(chat_id, f"✅ İşlendi.\n\n```\n{log[-1200:]}\n```")
        cmd_ozet(chat_id)
        cmd_borclu(chat_id)
    except Exception as e:
        mesaj_gonder(chat_id, f"❌ Hata: {e}")


# ─── Mesaj yönlendirici ───────────────────────────────────────────────────────

def mesaj_isle(msg: dict):
    chat_id = msg["chat"]["id"]

    # Güvenlik: sadece yetkili chat
    if CHAT_ID and str(chat_id) != str(CHAT_ID):
        return

    # .xlsx dosyası
    if "document" in msg:
        doc = msg["document"]
        if doc.get("file_name", "").endswith(".xlsx"):
            xlsx_isle(chat_id, doc["file_id"], doc["file_name"])
        else:
            mesaj_gonder(chat_id, "❌ Yalnızca .xlsx dosyaları desteklenir.")
        return

    metin = msg.get("text", "").strip()
    if not metin:
        return

    parcalar = metin.split(maxsplit=1)
    komut    = parcalar[0].lower().lstrip("/")
    arg      = parcalar[1] if len(parcalar) > 1 else ""

    if komut in ("ozet", "özet"):
        cmd_ozet(chat_id)
    elif komut in ("borclu", "borçlu", "borcluler", "borçlular"):
        cmd_borclu(chat_id)
    elif komut in ("ogrenci", "öğrenci"):
        if arg:
            cmd_ogrenci(chat_id, arg)
        else:
            mesaj_gonder(chat_id, "Kullanım: /ogrenci <ad veya id>")
    elif komut == "pipeline":
        cmd_pipeline(chat_id)
    elif komut in ("yardim", "yardım", "start", "help"):
        cmd_yardim(chat_id)
    else:
        # Serbest metin → öğrenci arama dene
        veri = son_durum()
        if veri:
            ogr = next(
                (o for o in veri["ogrenciler"] if metin.lower() in o["ad"].lower()),
                None,
            )
            if ogr:
                cmd_ogrenci(chat_id, ogr["id"])
                return
        cmd_yardim(chat_id)


# ─── Long polling döngüsü ─────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN eksik. .env dosyasını kontrol edin.")
        sys.exit(1)

    print("🤖 Sandık Bot başlatıldı. Çıkmak için Ctrl+C.")
    offset = 0

    while True:
        try:
            r = api("getUpdates", offset=offset, timeout=30)
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    mesaj_isle(update["message"])
        except KeyboardInterrupt:
            print("\nBot durduruldu.")
            break
        except Exception as e:
            print(f"Hata: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
