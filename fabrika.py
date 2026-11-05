"""
fabrika.py — Keşkeler ana orchestration.

Modlar:
  ornek       -> gizli örnek üretim, yayın yok
  deneme      -> üretir ve YouTube'a GİZLİ yükler (sen onayla)
  otomatik    -> üretir, 20:00 TR'de yayına girecek şekilde yükler
  sadece_uret -> hiçbir şey yüklemez, cikti/ klasörüne bırakır

Yayın takvimi: her 2 günde bir, 20:00 TR (UTC 17:00).
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta

import hikaye as hm
import gorsel as gm
import seslendirme as sm
import kurgu as km
import kapak as pm
import seo as em


PROGRAM = "program.json"
URETIM_KAYDI = "uretim"
CIKTI = "cikti"
YUKLENENLER = "yuklenenler.txt"
YAYIN_SAATI_UTC = 17   # 20:00 Türkiye (UTC+3)
ARALIK_GUN = 2         # her 2 günde bir


def log(m):
    print(m, flush=True)


# ---------------- Sıradaki bölüm ----------------

def yuklenenleri_oku():
    if not os.path.exists(YUKLENENLER):
        return []
    with open(YUKLENENLER, encoding="utf-8") as f:
        return [s.strip() for s in f if s.strip()]


def sira(program):
    yuklenen = yuklenenleri_oku()
    bitmis = {int(a.split("_")[0][5:]) for a in yuklenen if a.startswith("Bolum") and "_" in a}
    for b in program["bolumler"]:
        if b["no"] not in bitmis:
            return b
    raise RuntimeError("Program bitti; yeni bölüm ekleyin.")


def son_uretim_tarihi():
    """Son yayınlanan Bolum dosyasının modify tarihinden hesaplar (gerekirse günlük akış)."""
    if not os.path.exists(YUKLENENLER):
        return None
    with open(YUKLENENLER, encoding="utf-8") as f:
        satirlar = [l.strip() for l in f if l.strip()]
    if not satirlar:
        return None
    # dosyanın son modify tarihi yaklaşık son üretim
    return datetime.fromtimestamp(os.path.getmtime(YUKLENENLER), tz=timezone.utc)


# ---------------- Yayın saati ----------------

def yayin_zamani():
    """Bugün Türkiye saati 20:00 — gelmediyse o saat, geçtiyse yarın 20:00."""
    simdi = datetime.now(timezone.utc)
    tr = simdi + timedelta(hours=3)
    hedef = tr.replace(hour=YAYIN_SAATI_UTC + 3, minute=0, second=0, microsecond=0) - timedelta(hours=3)
    if hedef - simdi > timedelta(minutes=10):
        return hedef
    # geçtiyse yarın
    return hedef + timedelta(days=1)


# ---------------- Üretim ----------------

def uret(bolum, ornek=False):
    """Bir bölümü baştan sona üretir. Örnek modu daha az sahne (4) üretebilir."""
    bno = bolum["no"]
    taban = f"Bolum{bno:03d}_{bolum['konu'].replace(' ', '_')[:30]}"
    klasor = os.path.join(CIKTI, taban)
    os.makedirs(klasor, exist_ok=True)

    log(f"\n===== Bölüm {bno}: {bolum['kanca']} =====")

    log("[1/6] Hikaye yazılıyor...")
    hikaye = hm.hikaye_yaz(bolum)
    hm.kaydet(bno, hikaye, URETIM_KAYDI)
    log(f"   {len(hikaye['sahneler'])} sahne üretildi")

    hikaye["kanca_sorusu"] = bolum["kanca"]

    # Örnek modunda ilk 7 sahne + son soru sahnesi (hızlı ve ucuz deneme)
    if ornek:
        hikaye["sahneler"] = hikaye["sahneler"][:7] + [hikaye["sahneler"][-1]]
        log(f"   örnek modu → {len(hikaye['sahneler'])} sahneye düşürüldü")

    log(f"[2/6] {len(hikaye['sahneler'])} çizim üretiliyor...")
    resimler = gm.tum_sahneleri_ciz(hikaye, klasor)

    log("[3/6] Kapak için çizim...")
    kapak_ham = os.path.join(klasor, "_kapak_ham.png")
    gm.kapak_ciz(hikaye, kapak_ham)

    log("[4/6] Seslendirme...")
    sesler = sm.hikayeyi_seslendir(hikaye, klasor)

    log("[5/6] Video kurgusu...")
    video = os.path.join(klasor, f"{taban}.mp4")
    km.kurgula(hikaye, sesler, resimler, klasor, video)
    log(f"   video: {km.sure(video):.0f} sn")

    log("[6/6] Küçük resim...")
    kapak = os.path.join(klasor, f"{taban}_kapak.jpg")
    pm.kapak_yap(kapak_ham, bolum["kanca"], bno, kapak)

    return {"taban": taban, "video": video, "kapak": kapak, "hikaye": hikaye,
            "bolum": bolum, "klasor": klasor}


def yayinla(sonuc, mod):
    """YouTube'a yükler."""
    import yukleme as ym

    yt = ym.youtube_servisi()
    yayin = yayin_zamani() if mod == "otomatik" else None
    gizlilik = "private" if (mod == "deneme" or yayin) else "public"

    # SEO üret
    seo = em.seo_uret(sonuc["bolum"], sonuc["hikaye"])

    # örnek videosu için uyarı başlığı
    if mod == "ornek":
        seo["baslik"] = f"ÖRNEK · {seo['baslik']}"
        gizlilik = "private"

    log(f"\nBaşlık: {seo['baslik']}")

    vid = ym.yukle(yt, sonuc["video"], seo, gizlilik, yayin, sonuc["kapak"])
    log(f"[BAŞARILI] https://youtu.be/{vid}")

    if mod != "ornek":
        with open(YUKLENENLER, "a", encoding="utf-8") as f:
            f.write(sonuc["taban"] + "\n")

    durum = ("yayında" if gizlilik == "public" else
             "20:00'de yayına girecek" if yayin else "GİZLİ (deneme)")
    return {"video_id": vid, "baslik": seo["baslik"], "durum": durum}


# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["ornek", "deneme", "otomatik", "sadece_uret"])
    ap.add_argument("--bolum", type=int, help="Belirli bir bölüm numarası (yoksa sıradaki)")
    a = ap.parse_args()

    with open(PROGRAM, encoding="utf-8") as f:
        program = json.load(f)

    # otomatik modda son üretimden en az ARALIK_GUN geçmiş olmalı
    son = son_uretim_tarihi()
    if a.mod == "otomatik" and son:
        gecen = datetime.now(timezone.utc) - son
        if gecen < timedelta(days=ARALIK_GUN, hours=-12):
            log(f"[DUR] Son üretimden sadece {gecen.total_seconds() / 3600:.1f} saat geçti; {ARALIK_GUN} gün gerek.")
            return

    # bölüm seç
    if a.bolum:
        bolum = next(b for b in program["bolumler"] if b["no"] == a.bolum)
    else:
        bolum = sira(program)

    try:
        sonuc = uret(bolum, ornek=(a.mod == "ornek"))
        if a.mod == "sadece_uret":
            log(f"\n[TAMAM] Dosyalar: {sonuc['klasor']}")
            return
        bilgi = yayinla(sonuc, a.mod)
        log(f"\n[TAMAM] {bilgi['durum']}  ·  Başlık: {bilgi['baslik']}")
    except Exception as e:
        log(f"\n[HATA] {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
