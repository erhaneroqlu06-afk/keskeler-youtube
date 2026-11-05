"""
gorsel.py — Gemini 2.5 Flash Image ile renkli çizgi film tarzı çizimler.

Keşkeler görsel stili:
- Modern 2D çizgi film (kalın temiz çizgi, sıcak düz renkler, yumuşak gölge)
- Ayrıntılı gündelik Türk mekânları (apartman, çay bardağı, salon, sokak)
- Her bölümün kahramanı baştan sona AYNI kişi (önce bir referans çizim üretilir,
  sonraki her sahneye referans olarak verilir)
- Resimde yazı, logo, marka YOK
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor


STIL_TARIFI = (
    "Modern 2D cartoon illustration for a YouTube storytelling video. Clean bold outlines, "
    "warm saturated flat colors with soft shading, expressive friendly faces, rich detailed "
    "everyday Turkish settings (apartment blocks, tea glasses, patterned sofas, neighborhood "
    "streets, shops). Warm cinematic lighting, clear focal point, uncluttered composition. "
    "No text, no letters, no logos, no brand names, no watermarks."
)

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-image")


def _istemci():
    from google import genai
    return genai.Client()


def _resim_iste(contents, cikti_yolu, en_boy):
    """Gemini'den tek resim ister; 429/geçici hatalarda tekrar dener."""
    from google.genai import types

    client = _istemci()
    son_hata = None
    for deneme in range(5):
        try:
            yanit = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=en_boy),
                ),
            )
            for parca in yanit.candidates[0].content.parts:
                if parca.inline_data is not None:
                    with open(cikti_yolu, "wb") as f:
                        f.write(parca.inline_data.data)
                    return cikti_yolu
            raise RuntimeError("Gemini yanıtında resim yok")
        except Exception as e:
            son_hata = e
            time.sleep(6 * (deneme + 1))
    raise RuntimeError(f"Gemini çizim üretilemedi: {son_hata}")


def gorsel_uret(tarif, cikti_yolu, en_boy="16:9", referans=None, karakter=None):
    """Tek çizim. referans: kahraman çiziminin yolu (varsa aynı kişiyi korur)."""
    from google.genai import types

    metin = f"{tarif}\n\nSTYLE: {STIL_TARIFI}"
    if karakter:
        metin += f"\n\nMAIN CHARACTER: {karakter}"
    if referans and os.path.exists(referans):
        metin += ("\n\nThe attached image is the main character reference. Draw the SAME person "
                  "(same face, hair, build and clothing style; adjust age and clothing only if the "
                  "scene's era requires it) in the new scene.")
        with open(referans, "rb") as f:
            resim = types.Part.from_bytes(data=f.read(), mime_type="image/png")
        contents = [resim, metin]
    else:
        contents = metin
    return _resim_iste(contents, cikti_yolu, en_boy)


def karakter_ciz(hikaye, klasor):
    """Kahramanın referans çizimi (tam boy, sade arka plan)."""
    yol = os.path.join(klasor, "karakter.png")
    if not os.path.exists(yol):
        print("  kahraman referansı çiziliyor...", flush=True)
        gorsel_uret(
            f"Character reference portrait, waist-up, facing the viewer with a calm friendly "
            f"expression, plain soft background. The character: {hikaye['karakter']}",
            yol, "16:9")
    return yol


def tum_sahneleri_ciz(hikaye, klasor, paralel=4):
    """Her sahne için çizim üretir (4 paralel), dosya yollarını sırayla döner."""
    os.makedirs(klasor, exist_ok=True)
    ref = karakter_ciz(hikaye, klasor)
    karakter = hikaye["karakter"]
    yollar = [os.path.join(klasor, f"sahne{i:02d}.png") for i in range(1, len(hikaye["sahneler"]) + 1)]

    def is_(i):
        if not os.path.exists(yollar[i]):
            print(f"  sahne {i + 1} çiziliyor...", flush=True)
            gorsel_uret(hikaye["sahneler"][i]["gorsel"], yollar[i], "16:9",
                        referans=ref, karakter=karakter)
        return yollar[i]

    with ThreadPoolExecutor(max_workers=paralel) as havuz:
        list(havuz.map(is_, range(len(yollar))))
    return yollar


def kapak_ciz(hikaye, cikti_yolu):
    """YouTube küçük resmi için ana çizim (başlık üstüne eklenmeden önce)."""
    ref = os.path.join(os.path.dirname(cikti_yolu), "karakter.png")
    gorsel_uret(hikaye["kapak_gorsel"], cikti_yolu, "16:9",
                referans=ref, karakter=hikaye.get("karakter"))
    return cikti_yolu
