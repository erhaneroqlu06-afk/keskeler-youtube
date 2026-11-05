"""
kapak.py — YouTube küçük resmi (1280x720).

Kapak kalıbı:
- Üst üçte bir: büyük sarı başlık (kanca sorusu), siyah kenarlı
- Alt üçte iki: Gemini'nin çizdiği sahne
- Sağ alt köşede küçük "KEŞKELER" rozeti (marka tutarlılığı)
"""

import os
from PIL import Image, ImageDraw


SARI = (255, 214, 0)
INK = (28, 20, 14)
SEPIA = (242, 230, 206)


def _yazi_tipi(boyut, bold=True):
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
    return metin.replace("i", "İ").replace("ı", "I").upper()


def _satirlara_bol(d, metin, en, boyut_ust, boyut_alt, azami=2):
    kelimeler = metin.split()
    for boyut in range(boyut_ust, boyut_alt - 1, -4):
        f = _yazi_tipi(boyut)
        satirlar, suan = [], ""
        for k in kelimeler:
            dene = (suan + " " + k).strip()
            if d.textlength(dene, font=f) <= en:
                suan = dene
            else:
                if suan:
                    satirlar.append(suan)
                suan = k
        satirlar.append(suan)
        if len(satirlar) <= azami and all(d.textlength(s, font=f) <= en for s in satirlar):
            return f, boyut, satirlar
    f = _yazi_tipi(boyut_alt)
    return f, boyut_alt, [metin[:40]]


def kapak_yap(sahne_resmi, kanca_sorusu, bolum_no, cikti):
    """YouTube 1280x720 küçük resim: renkli çizim, üstte iri sarı başlık, köşede kırmızı rozet."""
    from PIL import ImageEnhance
    sahne = Image.open(sahne_resmi).convert("RGB").resize((1280, 720))
    sahne = ImageEnhance.Color(sahne).enhance(1.2)
    sahne = ImageEnhance.Contrast(sahne).enhance(1.1)

    # Üstte yumuşak koyu geçiş: yazı her resimde okunsun
    kar = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    kd = ImageDraw.Draw(kar)
    for y in range(0, 330):
        a = int(200 * (1 - y / 330) ** 1.4)
        kd.line((0, y, 1280, y), fill=(10, 8, 20, a))
    img = Image.alpha_composite(sahne.convert("RGBA"), kar)
    d = ImageDraw.Draw(img)

    yazi = _buyuk(kanca_sorusu)
    f, boyut, satirlar = _satirlara_bol(d, yazi, 1200, 104, 54, azami=2)
    y = 28
    for s_ in satirlar:
        g = d.textlength(s_, font=f)
        d.text(((1280 - g) / 2, y), s_, font=f, fill=SARI,
               stroke_width=max(6, boyut // 9), stroke_fill=(15, 10, 25))
        y += int(boyut * 1.12)

    # Sağ altta KEŞKELER rozeti (kırmızı)
    fr = _yazi_tipi(34)
    rozet = f"KEŞKELER  ·  #{bolum_no:03d}"
    g = d.textlength(rozet, font=fr)
    d.rounded_rectangle((1280 - g - 48, 646, 1256, 700), radius=14, fill=(196, 48, 48, 255))
    d.text((1280 - g - 24, 656), rozet, font=fr, fill=(255, 255, 255))

    img.convert("RGB").save(cikti, quality=92)
    return cikti
