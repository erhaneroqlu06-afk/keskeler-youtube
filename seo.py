"""
seo.py — Claude ile YouTube SEO (başlık, açıklama, etiket) üretimi.

Keşkeler başlık kalıbı:
  "Keşke [soru] — [duygulu alt metin] | Bir Karar, İki Hayat #<N>"
  Örnek: "Keşke O Evi Satmasaydın — 1999 Depreminden Hemen Önce | Bir Karar, İki Hayat #001"
"""

import json
import os


SISTEM_PROMPTU = """Sen "Keşkeler" adlı Türkçe YouTube kanalının SEO editörüsün.
Kanal her bölümde bir "ya olsaydı?" sorusunu iki paralel senaryo ile anlatır.
İzleyici kitlesi yetişkinler (30-60 yaş), özellikle emekliler ve orta yaş.

BAŞLIK (70-90 karakter)
- Kalıp: "Keşke [kısa soru] — [duygulu alt metin] | Bir Karar, İki Hayat #<N>"
- Örnek: "Keşke O Evi Satmasaydın — 1999 Depreminden Önce | Bir Karar, İki Hayat #001"
- Dürüst, duygulu, abartısız. CAPS LOCK, çok ünlem, "ŞOK", "İNANAMAYACAKSINIZ" yok.
- Emoji yok (beyaz başlık görünümü istiyoruz).

AÇIKLAMA (1500 karakter)
- İlk iki satır: kanca sorusu + bölümün ne anlattığı
- Orta kısım: izleyiciye "senin de bir keşken oldu mu?" sorusu, yorum davet
- Dürüst: "gerçek olaylardan esinlenilerek yazılmıştır, kişiler hayalidir" notu
- Son: hashtag (#Keşkeler #BirKararİkiHayat + konuya özel 2-3 hashtag)

ETİKETLER (10-15 adet, Türkçe, küçük harf)
- Konu + varyantları
- Nostalji, hikaye, ya olsaydı, iki hayat gibi uzun kuyruklu aramalar
- "keşkeler", "bir karar iki hayat" seri etiketleri her zaman
- Her etiket en fazla 30 karakter"""


CIKTI_SEMASI = {
    "type": "object",
    "properties": {
        "baslik": {"type": "string"},
        "aciklama": {"type": "string"},
        "etiketler": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["baslik", "aciklama", "etiketler"],
    "additionalProperties": False,
}


def seo_uret(bolum, hikaye):
    """Başlık, açıklama, etiketler üretir."""
    import anthropic

    client = anthropic.Anthropic()
    girdi = {
        "bolum_no": bolum["no"],
        "kanca_sorusu": bolum["kanca"],
        "donem": bolum["donem"],
        "konu": bolum["konu"],
        "ozet": hikaye.get("ozet", ""),
    }

    yanit = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"),
        max_tokens=4000,
        system=SISTEM_PROMPTU,
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": CIKTI_SEMASI},
        },
        messages=[{
            "role": "user",
            "content": "Bölüm bilgisi:\n" + json.dumps(girdi, ensure_ascii=False, indent=2),
        }],
    )

    metin = next(b.text for b in yanit.content if b.type == "text")
    seo = json.loads(metin)

    # temizlik
    seo["baslik"] = seo["baslik"][:100].strip()
    seo["aciklama"] = seo["aciklama"][:5000].strip()
    seo["etiketler"] = [e.strip().lower()[:30] for e in seo["etiketler"] if e.strip()][:15]

    return seo
