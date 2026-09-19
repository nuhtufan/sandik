#!/usr/bin/env python3
"""
Tam pipeline'ı sırayla çalıştırır.
gelen/*.xlsx → ekstre_isle → ogrenci_eslestir → borc_guncelle → rapor_uret

Kullanım:
  python3 bin/pipeline.py                    # gelen/ klasöründeki tüm xlsx
  python3 bin/pipeline.py gelen/ekstre.xlsx  # tek dosya
"""

import subprocess
import sys
from pathlib import Path

PROJE_KOK = Path(__file__).parent.parent
BIN       = PROJE_KOK / "bin"


def calistir(betik: str, *args) -> bool:
    cmd = [sys.executable, str(BIN / betik), *args]
    print(f"\n{'─'*55}")
    print(f"  ▶ {betik}" + (f"  {' '.join(args)}" if args else ""))
    print(f"{'─'*55}")
    sonuc = subprocess.run(cmd, cwd=PROJE_KOK)
    if sonuc.returncode != 0:
        print(f"  ✗ {betik} hata ile bitti (kod: {sonuc.returncode})")
        return False
    return True


def main():
    xlsx_arg = sys.argv[1] if len(sys.argv) > 1 else None

    adimlar = [
        ("ekstre_isle.py",      [xlsx_arg] if xlsx_arg else []),
        ("ogrenci_eslestir.py", []),
        ("borc_guncelle.py",    []),
        ("rapor_uret.py",       []),
    ]

    for betik, args in adimlar:
        if not calistir(betik, *args):
            print("\n  Pipeline durdu.")
            sys.exit(1)

    print(f"\n{'═'*55}")
    print(f"  ✓ Pipeline tamamlandı.")
    print(f"  Raporlar: cikti/ klasöründe")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()
