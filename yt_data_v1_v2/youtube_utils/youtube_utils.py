from googleapiclient.discovery import build

API_KEY = "YOUR_YOUTUBE_API_KEY"

def fetch_youtube_videos(channel_id: str, max_results=5):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=max_results,
        order="date"
    )
    response = request.execute()
    videos = []
    for item in response.get("items", []):
        if "videoId" in item["id"]:
            videos.append({
                "videoId": item["id"]["videoId"],
                "başlık": item["snippet"]["title"],
                "açıklama": item["snippet"]["description"]
            })
    return videos
