"""
kurgu.py — Keşkeler için profesyonel montaj (müziksiz).

Yapı:
  1. KANCA (0-10 sn): Siyah ekranda "Bir karar. İki hayat." sonra ilk sahne açılır.
  2. Her sahne ~5 sn'lik Ken Burns çekimlerine bölünür (geniş/yakın/kaydırma).
  3. Sahneler arası sert kesme; siyah geçiş ya da uzun sessizlik yok.
  4. Son sahne: izleyici sorusu üstünde kırmızı pano.
  5. Müzik YOK — sadece anlatıcı sesi.
"""

import os
import subprocess


FPS = 30
CEKIM_SN = 5.0

# (z0, z1, cx0, cy0, cx1, cy1)
CERCEVELER = [
    (1.00, 1.08, .50, .50, .50, .50),   # geniş, hafif yaklaşma
    (1.45, 1.55, .36, .45, .38, .45),   # yakın sol
    (1.45, 1.55, .64, .45, .62, .45),   # yakın sağ
    (1.25, 1.25, .40, .50, .60, .50),   # yatay kaydırma
    (1.60, 1.70, .50, .42, .50, .42),   # yüz yakın
]


def sure(yol):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", yol],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg hatası: " + r.stderr[-800:])


def yazi_tipi(boyut, bold=True):
    from PIL import ImageFont
    yollar = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ]
    for y in yollar:
        if os.path.exists(y):
            return ImageFont.truetype(y, boyut)
    return ImageFont.load_default()


def _buyuk(metin):
    """Türkçe doğru büyük harf (i→İ, ı→I)."""
    return metin.replace("i", "İ").replace("ı", "I").upper()


# ---------------- AÇILIŞ KARESİ ----------------

def siyah_kanca(cikti, yazi="Bir karar.  İki hayat.", sure_sn=2.5):
    """Siyah ekranda beyaz serif yazı — açılış kartı."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1920, 1080), (12, 12, 14))
    d = ImageDraw.Draw(img)
    f = yazi_tipi(100)
    g = d.textlength(yazi, font=f)
    bbox = d.textbbox((0, 0), yazi, font=f)
    th = bbox[3] - bbox[1]
    d.text(((1920 - g) / 2, (1080 - th) / 2 - 10), yazi, font=f, fill=(242, 230, 206))
    # altı ince kırmızı çizgi
    d.line((860, 640, 1060, 640), fill=(196, 48, 48), width=3)
    kare = cikti.replace(".mp4", ".jpg")
    img.save(kare, quality=92)

    # hafif fade-in animasyon
    ffmpeg("-loop", "1", "-framerate", str(FPS), "-i", kare, "-t", f"{sure_sn:.2f}",
           "-f", "lavfi", "-t", f"{sure_sn:.2f}", "-i", "anullsrc=r=48000:cl=stereo",
           "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={sure_sn-0.3:.2f}:d=0.3,setsar=1,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-shortest", cikti)
    return cikti


# ---------------- KANCA RESMİ ----------------

def kanca_resmi(resim, kanca_sorusu, cikti):
    """İlk sahnenin üstüne büyük sarı soru yazısı (10 saniye içinde yazıyla izleyiciyi tutmak için)."""
    from PIL import Image, ImageDraw
    img = Image.open(resim).convert("RGB").resize((1920, 1080))
    d = ImageDraw.Draw(img)

    yazi = _buyuk(kanca_sorusu)
    # satırlara böl, sığdır
    en_fazla_en = 1700
    for boyut in range(140, 60, -4):
        f = yazi_tipi(boyut)
        kelimeler = yazi.split()
        satirlar, suan = [], ""
        for k in kelimeler:
            dene = (suan + " " + k).strip()
            if d.textlength(dene, font=f) <= en_fazla_en:
                suan = dene
            else:
                if suan:
                    satirlar.append(suan)
                suan = k
        satirlar.append(suan)
        if len(satirlar) <= 2:
            break

    th = int(boyut * 1.15)
    toplam = th * len(satirlar)
    y = 1080 - toplam - 70
    for s in satirlar:
        g = d.textlength(s, font=f)
        d.text(((1920 - g) / 2, y), s, font=f, fill=(255, 214, 0),
               stroke_width=max(6, boyut // 10), stroke_fill=(15, 15, 30))
        y += th
    img.save(cikti, quality=92)
    return cikti


# ---------------- SAHNE KLİBİ ----------------

def _ifade(parcalar, varsayilan):
    s = varsayilan
    for bitis, e in reversed(parcalar):
        s = f"if(lt(on\\,{bitis})\\,{e}\\,{s})"
    return s


def sahne_klibi(resim, ses, cikti, sira, tek_cekim=False, bas_bosluk=0.15, son_bosluk=0.35):
    """Resmi ~5 sn çekimlere böler + seslendirme. Siyah geçiş yok."""
    s = sure(ses) + bas_bosluk + son_bosluk
    kare = int(round(s * FPS))
    n = 1 if tek_cekim else max(1, round(s / CEKIM_SN))
    sinirlar = [round(kare * (i + 1) / n) for i in range(n)]
    zp, xp, yp = [], [], []
    bas = 0
    for i, bit in enumerate(sinirlar):
        z0, z1, cx0, cy0, cx1, cy1 = CERCEVELER[0] if tek_cekim else \
            CERCEVELER[(sira * 2 + i) % len(CERCEVELER)]
        if tek_cekim:
            z0, z1 = 1.0, 1.05
        L = max(1, bit - bas)
        p = f"((on-{bas})/{L})"
        z = f"({z0}+({z1 - z0:.4f})*{p})"
        cx = f"({cx0}+({cx1 - cx0:.4f})*{p})"
        cy = f"({cy0}+({cy1 - cy0:.4f})*{p})"
        zp.append((bit, z))
        xp.append((bit, f"max(0\\,min(iw-iw/zoom\\,{cx}*iw-iw/zoom/2))"))
        yp.append((bit, f"max(0\\,min(ih-ih/zoom\\,{cy}*ih-ih/zoom/2))"))
        bas = bit
    z_e = _ifade(zp[:-1], zp[-1][1])
    x_e = _ifade(xp[:-1], xp[-1][1])
    y_e = _ifade(yp[:-1], yp[-1][1])
    vf = (f"scale=2880:1620,zoompan=z={z_e}:x={x_e}:y={y_e}:d=1:s=1920x1080:fps={FPS},"
          f"setsar=1,format=yuv420p")
    af = f"adelay={int(bas_bosluk * 1000)}|{int(bas_bosluk * 1000)},apad,atrim=0:{s:.2f},aresample=48000"
    ffmpeg("-loop", "1", "-framerate", str(FPS), "-i", resim, "-i", ses, "-t", f"{s:.2f}",
           "-vf", vf, "-af", af, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", cikti)
    return cikti


def birlestir(klipler, cikti, crf="20"):
    girdiler, f = [], ""
    for i, k in enumerate(klipler):
        girdiler += ["-i", k]
        f += f"[{i}:v]setsar=1,fps={FPS},format=yuv420p[v{i}];[{i}:a]aresample=48000[a{i}];"
    f += "".join(f"[v{i}][a{i}]" for i in range(len(klipler)))
    f += f"concat=n={len(klipler)}:v=1:a=1[v][a];[a]loudnorm=I=-16:TP=-1.5:LRA=11[an]"
    ffmpeg(*girdiler, "-filter_complex", f, "-map", "[v]", "-map", "[an]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", crf, "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", cikti)
    return cikti


# ---------------- ANA KURGU ----------------

def kurgula(hikaye, sesler, resimler, klasor, cikti_mp4):
    """Hikaye + sesler + resimler → tek mp4 video.

    hikaye: hikaye_yaz() çıktısı dict (sahneler listesi)
    sesler: her sahne için bir mp3 yolu
    resimler: her sahne için bir png yolu
    """
    os.makedirs(klasor, exist_ok=True)
    klipler = []

    # 1. siyah açılış kartı
    siyah = os.path.join(klasor, "_00_siyah.mp4")
    siyah_kanca(siyah)
    klipler.append(siyah)

    # 2. ilk sahne: kanca sorusu üstte büyük yazı
    ilk_resim_kanca = os.path.join(klasor, "_ilk_kanca.jpg")
    kanca_resmi(resimler[0], hikaye["sahneler"][0]["metin"][:60], ilk_resim_kanca)
    k1 = sahne_klibi(ilk_resim_kanca, sesler[0], os.path.join(klasor, "_01.mp4"), 0, tek_cekim=True)
    klipler.append(k1)

    # 3. kalan sahneler normal Ken Burns
    for i in range(1, len(resimler)):
        kl = sahne_klibi(resimler[i], sesler[i], os.path.join(klasor, f"_{i+1:02d}.mp4"), i)
        klipler.append(kl)

    # birleştir
    return birlestir(klipler, cikti_mp4)
