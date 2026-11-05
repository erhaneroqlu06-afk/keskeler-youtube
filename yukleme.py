"""
yukleme.py — YouTube Data API ile video yükleme.

Env değişkenleri:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN: Keşkeler kanalı için OAuth token.
"""

import os


def youtube_servisi():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    kimlik = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=kimlik)


def yukle(yt, dosya, meta, gizlilik, yayin_zamani=None, kapak=None):
    """Video yükle. gizlilik: private/unlisted/public. yayin_zamani: datetime veya None."""
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": meta["baslik"],
            "description": meta["aciklama"],
            "tags": meta.get("etiketler", []),
            "categoryId": "22",  # People & Blogs
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": {
            "privacyStatus": gizlilik,
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        },
    }

    if yayin_zamani:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = yayin_zamani.isoformat().replace("+00:00", "Z")

    medya = MediaFileUpload(dosya, mimetype="video/mp4", resumable=True, chunksize=-1)
    istek = yt.videos().insert(part="snippet,status", body=body, media_body=medya)

    yanit = None
    while yanit is None:
        _, yanit = istek.next_chunk()

    vid = yanit["id"]

    if kapak:
        try:
            yt.thumbnails().set(videoId=vid,
                                media_body=MediaFileUpload(kapak, mimetype="image/jpeg")).execute()
        except Exception as e:
            print("[UYARI] Küçük resim yüklenemedi (kanal telefonla doğrulanmamış olabilir):", str(e)[:200], flush=True)

    return vid
