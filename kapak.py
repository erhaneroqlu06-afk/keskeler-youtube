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
    """YouTube 1280x720 küçük resim üretir."""
    # Alt kısım: sahne resmi, biraz canlandırılmış
    from PIL import ImageEnhance
    sahne = Image.open(sahne_resmi).convert("RGB").resize((1280, 720))
    sahne = ImageEnhance.Color(sahne).enhance(1.15)
    sahne = ImageEnhance.Contrast(sahne).enhance(1.08)

    # Üst üçte bir için sepia arka plan şeridi
    img = sahne.copy()
    d = ImageDraw.Draw(img, "RGBA")

    # Üst şerit yarı saydam sepia
    d.rectangle((0, 0, 1280, 240), fill=(242, 230, 206, 235))

    # Başlık: kanca sorusu
    yazi = _buyuk(kanca_sorusu)
    f, boyut, satirlar = _satirlara_bol(d, yazi, 1180, 100, 54, azami=2)
    toplam_y = int(boyut * 1.12) * len(satirlar)
    y = (240 - toplam_y) // 2
    for s in satirlar:
        g = d.textlength(s, font=f)
        d.text(((1280 - g) / 2, y), s, font=f, fill=INK,
               stroke_width=4, stroke_fill=(248, 240, 220))
        y += int(boyut * 1.12)

    # Üst şerit ile alt kısım arası ince kırmızı çizgi
    d.line((0, 240, 1280, 240), fill=(196, 48, 48), width=4)

    # Sağ alt köşede KEŞKELER rozeti
    fr = _yazi_tipi(32)
    rozet = f"KEŞKELER  ·  #{bolum_no:03d}"
    g = d.textlength(rozet, font=fr)
    d.rounded_rectangle((1280 - g - 44, 650, 1262, 702), radius=12, fill=(28, 20, 14, 230))
    d.text((1280 - g - 22, 660), rozet, font=fr, fill=SEPIA)

    img.save(cikti, quality=92)
    return cikti
