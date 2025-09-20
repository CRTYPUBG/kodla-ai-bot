from googleapiclient.discovery import build
import json

# Buraya kendi API anahtarını yaz
API_KEY = "AIxxx" # YOUTUBE_API_KEY= APİ KEY ALIN # https://console.cloud.google.com/apis/dashboard?hl=tr
burdan git youtube data v1 aç mage de api key yaz

CHANNEL_ID = "UCmTwp5YyPLP4fbVns3hsrBg"  # hedef kanalın ID'si : https://www.youtube.com/account_advanced Burdaki : Kanal Kimliği Al

youtube = build("youtube", "v3", developerKey=API_KEY)

# Kanalın videolarını al
request = youtube.search().list(
    part="snippet",
    channelId=CHANNEL_ID,
    maxResults=10,   # ilk 10 video
    order="date"     # en son yüklenenlerden başla
)
response = request.execute()

# Çıktı verilerini hazırla
videos = []
for item in response.get("items", []):
    video_data = {
        "videoId": item["id"].get("videoId"),
        "başlık": item["snippet"]["title"],
        "açıklama": item["snippet"]["description"],
        "yayın_tarihi": item["snippet"]["publishedAt"]
    }
    videos.append(video_data)

# JSON olarak kaydet (Türkçe karakterler bozulmaz)
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=4)

print("✅ Veriler output.json dosyasına kaydedildi.")
