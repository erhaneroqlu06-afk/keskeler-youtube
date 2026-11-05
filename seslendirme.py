"""
seslendirme.py — Gemini'nin doğal sesiyle anlatıcı (yedek: Edge TTS, sonra gTTS).

Keşkeler anlatıcı sesi:
- Canlı, heyecanlı, sürükleyici hikâye anlatıcısı; her sahneye özel duygu (ton)
- Müzik yok, sadece ses
- Model adı hesaptan otomatik bulunur (adı "tts" içeren flash model); GEMINI_TTS_MODEL ile değiştirilebilir
- Ses: GEMINI_SES (varsayılan Puck, canlı/heyecanlı); hız SES_HIZI (varsayılan 1.08)
"""

import asyncio
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor


GEMINI_SES = os.environ.get("GEMINI_SES", "Puck")
TALIMAT = ("Aşağıdaki metni İstanbul Türkçesiyle, tamamen Türk bir hikâye anlatıcısı gibi, doğal Türkçe "
           "telaffuzla oku; asla yabancı aksan olmasın. Ses sıcak, yumuşak, samimi ve içten olsun; sanki yakın "
           "bir arkadaşına şefkatle bir hikâye anlatıyormuş gibi (tender, warm, intimate). Bağırma, abartma; "
           "doğal duraklar yap, önemli kelimeleri hafifçe vurgula, soru cümlelerinde sesi nazikçe yükselt. "
           "Duygu değişse bile bu yumuşak ve sıcak tını hep korunsun. ")
HIZ = float(os.environ.get("SES_HIZI", "1.0"))  # ffmpeg atempo: perde bozulmadan biraz hızlandırır

EDGE_SES = os.environ.get("EDGE_SES", "tr-TR-AhmetNeural")
EDGE_HIZ = os.environ.get("EDGE_HIZ", "-5%")
EDGE_PERDE = os.environ.get("EDGE_PERDE", "-2Hz")

_model_adi = None


def _tts_modeli():
    """Hesapta ses üretebilen flash modeli bulur."""
    global _model_adi
    if _model_adi:
        return _model_adi
    if os.environ.get("GEMINI_TTS_MODEL"):
        _model_adi = os.environ["GEMINI_TTS_MODEL"]
        return _model_adi
    from google import genai
    adaylar = []
    try:
        istemci = genai.Client()  # değişkende tut: geçici istemci kapanıp liste yarım kalıyordu
        for m in istemci.models.list():
            ad = m.name.replace("models/", "")
            if "tts" in ad:
                adaylar.append(ad)
    except Exception as e:
        print(f"[seslendirme] model listesi alınamadı: {e}", flush=True)
    adaylar.sort(key=lambda a: ("pro" in a, "preview" in a, a))  # flash ve kararlı olan önce
    _model_adi = adaylar[0] if adaylar else "gemini-2.5-flash-preview-tts"
    print(f"[seslendirme] ses modeli: {_model_adi}", flush=True)
    return _model_adi


def _gemini_ses(metin, cikti_yolu, ton=""):
    from google import genai
    from google.genai import types

    client = genai.Client()
    son_hata = None
    for deneme in range(6):
        try:
            yanit = client.models.generate_content(
                model=_tts_modeli(),
                contents=TALIMAT.rstrip() + (f" Bu cümledeki duygu (İngilizce): {ton}." if ton else "") + " Metin: " + metin,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=GEMINI_SES)
                        )
                    ),
                ),
            )
            veri = yanit.candidates[0].content.parts[0].inline_data.data
            if not veri:
                raise RuntimeError("ses verisi boş")
            ham = cikti_yolu + ".pcm"
            with open(ham, "wb") as f:
                f.write(veri)
            # Gemini ses çıktısı: 24 kHz, 16 bit, tek kanal ham PCM
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", "24000",
                                "-ac", "1", "-i", ham, "-af", f"atempo={HIZ}", "-b:a", "128k", cikti_yolu],
                               capture_output=True, text=True)
            os.remove(ham)
            if r.returncode != 0:
                raise RuntimeError("ffmpeg: " + r.stderr[-300:])
            return cikti_yolu
        except Exception as e:
            son_hata = e
            time.sleep(5 * (deneme + 1))
    raise RuntimeError(f"Gemini ses üretilemedi: {son_hata}")


async def _edge(metin, cikti_yolu):
    import edge_tts
    await edge_tts.Communicate(metin, EDGE_SES, rate=EDGE_HIZ, pitch=EDGE_PERDE).save(cikti_yolu)


def seslendir(metin, cikti_yolu, ton=""):
    """Metni mp3 yapar: önce Gemini, olmazsa Edge TTS, olmazsa gTTS."""
    try:
        return _gemini_ses(metin, cikti_yolu, ton)
    except Exception as e:
        print(f"[seslendirme] Gemini başarısız, Edge'e dönülüyor: {e}", flush=True)
    try:
        asyncio.run(_edge(metin, cikti_yolu))
        return cikti_yolu
    except Exception as e:
        print(f"[seslendirme] Edge başarısız, gTTS'e dönülüyor: {e}", flush=True)
        from gtts import gTTS
        gTTS(metin, lang="tr").save(cikti_yolu)
        return cikti_yolu


def hikayeyi_seslendir(hikaye, klasor, paralel=3):
    """Hikayenin her sahnesini ayrı mp3 olarak seslendirir."""
    os.makedirs(klasor, exist_ok=True)
    yollar = [os.path.join(klasor, f"ses{i:02d}.mp3") for i in range(1, len(hikaye["sahneler"]) + 1)]

    def is_(i):
        if not os.path.exists(yollar[i]):
            seslendir(hikaye["sahneler"][i]["metin"], yollar[i], hikaye["sahneler"][i].get("ton", ""))
        return yollar[i]

    _tts_modeli()  # model adını bir kez bul (paralel işlerde tekrar aranmasın)
    with ThreadPoolExecutor(max_workers=paralel) as havuz:
        list(havuz.map(is_, range(len(yollar))))
    return yollar
