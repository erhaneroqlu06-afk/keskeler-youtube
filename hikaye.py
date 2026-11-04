"""
hikaye.py — Keşkeler bölümleri için Claude ile iki senaryolu hikaye yazımı.

Her bölüm:
- Bir "karar anı" (örn. 1999 depreminden önce evini satıp satmama)
- İki paralel senaryo (karar verdin → şöyle oldu / vermeseydin → şöyle oldu)
- 10 dakikalık video için ~25 sahne, yaklaşık 1500 kelime
- Her sahnenin bir çizim tarifi var
- Her sahnenin anlatıcı metni var
- İlk sahne kanca (0-10 sn)
- Son sahne izleyiciye "senin keşken?" sorusu
"""

import json
import os
from datetime import datetime, timezone


SISTEM_PROMPTU = """Sen "Keşkeler" adlı Türk YouTube kanalının senaryo yazarısın.
İzleyici kitlen yetişkinler (30-60 yaş), özellikle emekliler ve orta yaşlılar. Nostaljik, duygulu
ama abartısız bir dil kullanıyorsun.

Her bölüm bir "ya olsaydı?" sorusunu iki paralel senaryo olarak anlatır:
- SENARYO A: "Bu kararı verdin, 20 yıl sonra şöyle bir yerdesin"
- SENARYO B: "Vermeseydin şöyle olurdu"

Her iki senaryoyu da sakin, nesnel, duygulu anlat. Hiçbirini "doğru" ya da "yanlış" olarak yargılamıyoruz.
İzleyici kendi hayatıyla eşleştirsin.

BİÇİM KURALLARI
- Tam 25 sahne, yaklaşık 10 dakika anlatım süresi.
- Kanca sahnesi (sahne 1): 0-10 saniye arası, siyah ekranda "Bir karar. İki hayat." cümlesinden sonra
  izleyiciyi hikayeye çeken kısa açılış. Konuyu bir soruyla açar.
- Sahneler 2-3: Bağlam (yılı, mekânı, karakteri tanıtır — sen izleyiciye "sen" diye anlatıyorsun).
- Sahneler 4-13: SENARYO A — kararı verdiğinde başına gelenler.
- Sahne 14: Geçiş — "Peki ya başka bir yolu seçseydin?"
- Sahneler 15-23: SENARYO B — kararı vermeseydin başına gelenler.
- Sahne 24: Kapanış yorum — iki hayatın da kendi güzelliği ve kaybı var, yargı yok.
- Sahne 25: İZLEYİCİ SORUSU — konuya özel bir "senin keşken?" sorusu.
  Ör. Bitcoin konusu için: "Senin de pişman olduğun bir yatırım kararın var mı? Keşkeni yoruma yaz."

HER SAHNE
- "metin": Anlatıcı tarafından sesli okunacak metin. 3-5 cümle, günlük ve sıcak Türkçe. 2. tekil şahıs
  ("sen"). Kanca ve kapanış sahneleri daha kısa olabilir (1-2 cümle).
- "gorsel": O sahnenin İNGİLİZCE çizim tarifi. Sepia + kırmızı aksanlı gazete illüstrasyonu stiliyle
  uyumlu olsun. İnsan yüzü varsa ifadesi nazik ve nostaljik olsun; markalaşmış kıyafet, telif
  işareti, gerçek markalar yok. (Resimde yazı olmasın.)

ÇIKTI
- "ozet": Bölümü iki cümlede özetleyen Türkçe metin (açıklama alanı için).
- "sahneler": 25 sahnelik dizi (metin + gorsel).
- "kapak_gorsel": Küçük resim için İNGİLİZCE tarif. İki yolu aynı karede gösteren (ör. yol çatallanması
  karakterin arkasında), sepia + kırmızı aksan stili. Üst üçte bir kısmı başlık yazısı için boş kalsın.

DİKKAT
- GERÇEK isim uydurma (karakter "sen"sin, tarafsız anlatım).
- HASSAS konularda (deprem, kayıp, ekonomik kriz) duyguyu ağırlaştırmadan, saygıyla anlat.
- DOLDURULMUŞ bilgi uydurma; dönem hakkında emin olmadığın şeyi atla.
- NEŞELİ ve kasvetli yanları dengele, tek yönlü karanlık olmasın."""


HIKAYE_SEMASI = {
    "type": "object",
    "properties": {
        "ozet": {"type": "string"},
        "kapak_gorsel": {"type": "string"},
        "sahneler": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metin": {"type": "string"},
                    "gorsel": {"type": "string"},
                },
                "required": ["metin", "gorsel"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ozet", "kapak_gorsel", "sahneler"],
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

    yanit = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"),
        max_tokens=16000,
        system=SISTEM_PROMPTU,
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": HIKAYE_SEMASI},
        },
        messages=[{
            "role": "user",
            "content": "Bölüm bilgisi:\n" + json.dumps(girdi, ensure_ascii=False, indent=2),
        }],
    )

    if yanit.stop_reason != "end_turn":
        raise ValueError(f"Beklenmeyen stop_reason: {yanit.stop_reason}")

    metin = next(b.text for b in yanit.content if b.type == "text")
    h = json.loads(metin)

    if not 20 <= len(h["sahneler"]) <= 30:
        raise ValueError(f"{len(h['sahneler'])} sahne üretildi (hedef 25)")

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
