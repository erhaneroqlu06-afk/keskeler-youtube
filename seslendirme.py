"""
seslendirme.py — Edge TTS ile sakin erkek sesi.

Keşkeler anlatıcı sesi:
- Sakin, düşük tempolu, ağırbaşlı
- Türkçe yetişkin kitleye uygun
- Nostalji ve duygu taşıyan ama abartısız

Edge TTS Türkçe sesleri:
- tr-TR-AhmetNeural: Erkek, berrak (varsayılan)
- tr-TR-EmelNeural: Kadın (yedek)
"""

import asyncio
import os


SES = os.environ.get("EDGE_SES", "tr-TR-AhmetNeural")
HIZ = os.environ.get("EDGE_HIZ", "-5%")
PERDE = os.environ.get("EDGE_PERDE", "-2Hz")


async def _uret(metin, cikti_yolu):
    import edge_tts
    iletisimci = edge_tts.Communicate(metin, SES, rate=HIZ, pitch=PERDE)
    await iletisimci.save(cikti_yolu)


def seslendir(metin, cikti_yolu):
    """Metni MP3 olarak seslendir. Sakin tempo için orijinal hızın %5 altında."""
    try:
        asyncio.run(_uret(metin, cikti_yolu))
        return cikti_yolu
    except Exception as e:
        # Yedek: gTTS
        print(f"[seslendirme] Edge başarısız, gTTS'e dönülüyor: {e}", flush=True)
        from gtts import gTTS
        gTTS(metin, lang="tr").save(cikti_yolu)
        return cikti_yolu


def hikayeyi_seslendir(hikaye, klasor):
    """Hikayenin her sahnesini ayrı mp3 olarak seslendirir."""
    os.makedirs(klasor, exist_ok=True)
    sesler = []
    for i, sahne in enumerate(hikaye["sahneler"], 1):
        yol = os.path.join(klasor, f"ses{i:02d}.mp3")
        if not os.path.exists(yol):
            seslendir(sahne["metin"], yol)
        sesler.append(yol)
    return sesler
