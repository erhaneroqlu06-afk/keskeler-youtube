"""
hikaye.py — Keşkeler bölümleri için Claude ile iki senaryolu hikaye yazımı.

Her bölüm:
- Bir "karar anı" (örn. 1999 depreminden önce evini satıp satmama)
- İki paralel senaryo (karar verdin → şöyle oldu / vermeseydin → şöyle oldu)
- 10 dakikalık video için 60 sahne, her sahne 1-2 cümle
- Her sahnenin bir çizim tarifi var
- Her sahnenin anlatıcı metni var
- İlk sahne kanca (0-10 sn)
- Son sahne izleyiciye "senin keşken?" sorusu
"""

import json
import os
from datetime import datetime, timezone


SISTEM_PROMPTU = """Sen "Keşkeler" adlı Türk YouTube kanalının senaryo yazarısın.
İzleyici kitlen yetişkinler (30-60 yaş). Sıcak, canlı, heyecanlı, günlük konuşma Türkçesi kullanıyorsun;
sanki bir arkadaşına anlatıyormuşsun gibi. Resmî veya ders gibi konuşma.

Her bölüm bir "ya olsaydı?" sorusunu iki paralel hayat olarak anlatır:
- SENARYO A: "Bu kararı verdin, yıllar sonra şöyle bir yerdesin"
- SENARYO B: "Vermeseydin şöyle olurdu"
Hiçbirini doğru ya da yanlış diye yargılamıyoruz. İzleyici kendi hayatıyla eşleştirsin.
Anlatım hep ikinci tekil şahıs: "sen". Hikâyenin kahramanı "sen"sin.

TAM 60 SAHNE (yaklaşık 10 dakika). Dağılım:
- Sahne 1: KANCA. Tek güçlü cümle: izleyiciyi ilk saniyede yakalayan bir an ya da soru.
- Sahneler 2-5: Bağlam (yıl, mekân, günlük hayat, içindeki ikilem).
- Sahneler 6-28: SENARYO A, adım adım, yıllara yayılarak.
- Sahne 29: Geçiş: "Peki ya başka bir yolu seçseydin?"
- Sahneler 30-56: SENARYO B, adım adım, yıllara yayılarak.
- Sahneler 57-59: Kapanış; iki hayatın da güzelliği ve kaybı, yargı yok.
- Sahne 60: İZLEYİCİ SORUSU; konuya özel, samimi ("Senin keşken ne olurdu? Yoruma yaz.").

HER SAHNE
- "metin": Sesli okunacak 1-2 kısa cümle (12-28 kelime). Somut ve görsel: bir nesne, bir koku, bir cümle,
  bir yüz. Duyguyu anlatma, göster. Her sahne yeni bir şey söylesin; tekrar yok.
- "ton": Sesli okuma duygusu, 1-3 İNGİLİZCE kelime (ör. "curious and excited", "tense", "warm and hopeful",
  "heartbroken", "proud", "shocked"). Anlatım DURAĞAN olmasın: heyecanlı ve sürükleyici; sorular, şaşkınlık,
  merak ve duygu değişimleri olsun. Sahneler arası tonu çeşitlendir.
- "gorsel": O sahnenin İNGİLİZCE çizim tarifi. Her tarifte ana kahraman (karakter) görünmeli;
  mekân, ışık ve yüz ifadesi net olsun. Zaman geçtikçe kahramanın yaşı, kıyafeti ve çevresi dönemine uysun.
  Düşünce balonu (hayalinde canlanan şey) kullanabilirsin. Resimde yazı, tabela metni, logo olmasın.
  Her sahne bir öncekinden görsel olarak farklı olsun (farklı mekân, açı veya an).

ÇIKTI ALANLARI
- "karakter": Kahramanın İNGİLİZCE dış görünüş tarifi (cinsiyet, yaklaşık yaş, saç, yüz, kıyafet). Tek kişi,
  tüm sahnelerde aynı kişi. Konu aile içi ise yan karakterleri sahnede tarif et.
- "ozet": Bölümü iki cümlede özetleyen Türkçe açıklama.
- "izleyici_sorusu": Sahne 60'ın ekranda görünecek KISA hali (en fazla 60 karakter, Türkçe).
- "kapak_gorsel": Küçük resim için İNGİLİZCE tarif: kahramanın iri, duygulu yüzü yakın planda;
  arkasında iki yolu hissettiren bir şey (ör. iki farklı ev ya da yol); üst üçte bir boş kalsın.
- "sahneler": 60 sahnelik dizi.

DİKKAT
- GERÇEK kişi adı uydurma; markalaşmış ürün, logo yok.
- Hassas konularda (deprem, kayıp, kriz) saygılı ol, duyguyu abartma.
- Dönem hakkında emin olmadığın bilgiyi yazma.
- Karanlık ve umutlu anları dengele."""


HIKAYE_SEMASI = {
    "type": "object",
    "properties": {
        "ozet": {"type": "string"},
        "karakter": {"type": "string"},
        "izleyici_sorusu": {"type": "string"},
        "kapak_gorsel": {"type": "string"},
        "sahneler": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metin": {"type": "string"},
                    "ton": {"type": "string"},
                    "gorsel": {"type": "string"},
                },
                "required": ["metin", "ton", "gorsel"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ozet", "karakter", "izleyici_sorusu", "kapak_gorsel", "sahneler"],
    "additionalProperties": False,
}


def hikaye_yaz(bolum):
    """Bir bölümün tam senaryosunu üretir.

    bolum: program.json'dan bir öğe. Beklenen alanlar: no, kanca, donem, konu, duygu.
    """
    import anthropic

    client = anthropic.Anthropic()
    girdi = {
        "bolum_no": bolum["no"],
        "kanca_sorusu": bolum["kanca"],
        "donem": bolum["donem"],
        "konu": bolum["konu"],
        "duygu": bolum.get("duygu", ""),
    }

    with client.messages.stream(
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"),
        max_tokens=24000,
        system=SISTEM_PROMPTU,
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": HIKAYE_SEMASI},
        },
        messages=[{
            "role": "user",
            "content": "Bölüm bilgisi:\n" + json.dumps(girdi, ensure_ascii=False, indent=2),
        }],
    ) as akis:
        yanit = akis.get_final_message()

    if yanit.stop_reason != "end_turn":
        raise ValueError(f"Beklenmeyen stop_reason: {yanit.stop_reason}")

    metin = next(b.text for b in yanit.content if b.type == "text")
    h = json.loads(metin)

    if not 50 <= len(h["sahneler"]) <= 70:
        raise ValueError(f"{len(h['sahneler'])} sahne üretildi (hedef 60)")

    return h


def kaydet(bolum_no, hikaye, klasor="uretim"):
    os.makedirs(klasor, exist_ok=True)
    yol = os.path.join(klasor, f"bolum{bolum_no:03d}.json")
    kayit = {
        "bolum_no": bolum_no,
        "uretim_tarihi": datetime.now(timezone.utc).isoformat(),
        **hikaye,
    }
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=2)
    return yol
