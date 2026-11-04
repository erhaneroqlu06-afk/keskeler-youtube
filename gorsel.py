"""
gorsel.py — Gemini 2.5 Flash Image ile sepia + kırmızı aksanlı çizim üretimi.

Keşkeler görsel stili:
- Gazete illüstrasyonu / vintage çizim
- Sepia ton (kirli krem zemin)
- Kırmızı aksan rengi (tek vurgu noktası)
- Siyah mürekkep çizgileri
- Noktalama/tarama (hatching) dokusu
- İnsan karakterleri nazik ifadeler, nostaljik duruş
- Telif işareti, logo, marka YOK
- Resimde yazı YOK
"""

import os
import time
import base64


STIL_TARIFI = (
    "Vintage Turkish newspaper illustration style, sepia-toned beige background "
    "(like aged paper), warm off-white tones with slight grain and hatching texture. "
    "Primary ink color is deep brown-black with fine pen cross-hatching. "
    "One accent color only: muted red (#C43030) used sparingly for emphasis "
    "(a single object, a highlight). No other bright colors. "
    "Nostalgic, quiet, dignified mood. Characters have gentle expressions, "
    "soft facial features, no exaggerated details. "
    "Classic illustration composition, clean negative space. "
    "No text, no logos, no brand names, no modern technology unless the era requires it."
)


def gorsel_uret(tarif, cikti_yolu, en_boy="16:9"):
    """Gemini ile tek bir çizim üretir.

    tarif: sahnenin İngilizce içerik tarifi (karakterlerin ne yaptığı, mekân, duygu).
    cikti_yolu: PNG çıktısı buraya yazılır.
    en_boy: "16:9" uzun video, "9:16" shorts, "1:1" kapak.
    """
    from google import genai
    from google.genai import types

    client = genai.Client()
    tam_prompt = f"{tarif}\n\nSTYLE: {STIL_TARIFI}\n\nAspect ratio: {en_boy}"

    son_hata = None
    for deneme in range(3):
        try:
            yanit = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-image"),
                contents=tam_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
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
            if deneme < 2:
                time.sleep(5 * (deneme + 1))

    raise RuntimeError(f"Gemini çizim üretilemedi: {son_hata}")


def tum_sahneleri_ciz(hikaye, klasor):
    """Hikayedeki her sahne için çizim üretir, dosya yollarını döner."""
    os.makedirs(klasor, exist_ok=True)
    resimler = []
    for i, sahne in enumerate(hikaye["sahneler"], 1):
        yol = os.path.join(klasor, f"sahne{i:02d}.png")
        if not os.path.exists(yol):
            print(f"  sahne {i} çiziliyor...", flush=True)
            gorsel_uret(sahne["gorsel"], yol, "16:9")
        resimler.append(yol)
    return resimler


def kapak_ciz(hikaye, cikti_yolu):
    """YouTube küçük resmi için ana çizim (başlık üstüne eklenmeden önce)."""
    gorsel_uret(hikaye["kapak_gorsel"], cikti_yolu, "16:9")
    return cikti_yolu
