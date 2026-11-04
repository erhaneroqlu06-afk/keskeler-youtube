# Keşkeler — YouTube kanal fabrikası

"Ya olsaydı?" temalı Türkçe YouTube kanalı için otomatik video üretim sistemi.

**Kanal:** [@keskelertv](https://www.youtube.com/@keskelertv)

## Ne yapar?

Her 2 günde bir, 20:00 Türkiye saatinde:
- Claude bir "ya olsaydı" hikayesi yazar (iki paralel senaryo)
- Gemini sepia + kırmızı aksanlı gazete illüstrasyonu çizer
- Edge TTS sakin bir sesle anlatır
- ffmpeg Ken Burns kurgusuyla 10 dakikalık video üretir
- YouTube'a otomatik yükler

## Modüller

- fabrika.py — ana orchestration
- hikaye.py — Claude ile iki senaryolu hikaye
- gorsel.py — Gemini ile çizim
- seslendirme.py — Edge TTS
- kurgu.py — ffmpeg kurgusu (kanca + Ken Burns)
- kapak.py — YouTube küçük resim
- seo.py — başlık/açıklama/etiket
- yukleme.py — YouTube API
- program.json — bölüm planı

## Kurallar

1. Her bölüm iki paralel senaryo anlatır
2. İlk 10 saniyede kanca: "Bir karar. İki hayat."
3. Her bölüm sonunda konuya özel "senin keşken?" sorusu
4. Müzik YOK — sadece sakin anlatıcı sesi
5. Görsel stil: sepia + kırmızı aksan
6. Yetişkin içerik (çocuklara özel değil)
