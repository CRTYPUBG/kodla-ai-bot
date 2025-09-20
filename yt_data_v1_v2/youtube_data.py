"""
Adım 2: YouTube Verilerini Çekme
YouTube API ile video başlık, açıklama, altyazı çeker
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import pandas as pd
import json
import re
import isodate
from typing import List, Dict, Optional, Tuple
import time
import logging
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API anahtarını .env dosyasından al
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

class YouTubeDataCollector:
    def __init__(self, api_key: str = None):
        if not api_key:
            raise ValueError("YouTube API anahtarı gerekli!")
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.request_delay = 0.1  # Delay between API requests to avoid quota issues
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """YouTube URL'den video ID'sini çıkar"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_metadata(self, video_ids: List[str]) -> List[Dict]:
        """Video metadata'larını topla"""
        videos_data = []
        
        # API limiti nedeniyle 50'şer parça halinde işle
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            
            try:
                request = self.youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=','.join(batch)
                )
                response = request.execute()
                
                for item in response['items']:
                    # Parse ISO 8601 duration to seconds
                    duration = isodate.parse_duration(item['contentDetails']['duration']).total_seconds()
                    
                    video_data = {
                        'video_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'channel_title': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'duration_seconds': duration,
                        'view_count': int(item['statistics'].get('viewCount', 0)),
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'comment_count': int(item['statistics'].get('commentCount', 0)),
                        'url': f"https://www.youtube.com/watch?v={item['id']}"
                    }
                    videos_data.append(video_data)
                
                # Avoid hitting API quota limits
                time.sleep(self.request_delay)
                
            except HttpError as e:
                logger.error(f"API error for batch {i//50}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error for batch {i//50}: {e}")
                continue
        
        return videos_data
    
    def get_video_transcript(self, video_id: str, languages: List[str] = ['tr', 'en']) -> Optional[str]:
        """Video altyazısını çek"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Önce Türkçe, sonra İngilizce dene
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    transcript_data = transcript.fetch()
                    
                    # Altyazı metinlerini birleştir
                    full_text = ' '.join([entry['text'] for entry in transcript_data])
                    return full_text
                except NoTranscriptFound:
                    continue
                    
        except NoTranscriptFound:
            logger.info(f"No transcript found for video {video_id}")
        except TranscriptsDisabled:
            logger.info(f"Transcripts disabled for video {video_id}")
        except Exception as e:
            logger.error(f"Error getting transcript for {video_id}: {e}")
            
        return None
    
    def search_videos(self, query: str, max_results: int = 50) -> List[str]:
        """Belirli bir sorgu ile video ara"""
        video_ids = []
        next_page_token = None
        
        try:
            # YouTube API only returns up to 50 results per page
            while len(video_ids) < max_results:
                request = self.youtube.search().list(
                    part='id',
                    q=query,
                    type='video',
                    maxResults=min(50, max_results - len(video_ids)),
                    order='relevance',
                    pageToken=next_page_token
                )
                response = request.execute()
                
                video_ids.extend([item['id']['videoId'] for item in response['items']])
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
                time.sleep(self.request_delay)
                
        except HttpError as e:
            logger.error(f"Search API error for query '{query}': {e}")
        except Exception as e:
            logger.error(f"Unexpected search error for query '{query}': {e}")
        
        return video_ids[:max_results]
    
    def process_video_urls(self, urls: List[str]) -> List[Dict]:
        """URL listesinden video verilerini işle"""
        video_ids = []
        invalid_urls = []
        
        for url in urls:
            video_id = self.extract_video_id(url)
            if video_id:
                video_ids.append(video_id)
            else:
                invalid_urls.append(url)
                logger.warning(f"Invalid YouTube URL: {url}")
        
        if invalid_urls:
            logger.info(f"Skipped {len(invalid_urls)} invalid URLs")
        
        # Metadata'ları al
        videos_data = self.get_video_metadata(video_ids)
        
        # Her video için altyazı ekle
        for video_data in videos_data:
            transcript = self.get_video_transcript(video_data['video_id'])
            video_data['transcript'] = transcript
            
            # RAG için text chunks oluştur
            video_data['text_chunks'] = self.create_text_chunks(
                video_data['title'], 
                video_data['description'], 
                transcript
            )
        
        return videos_data
    
    def create_text_chunks(self, title: str, description: str, 
                          transcript: Optional[str], chunk_size: int = 512) -> List[Dict]:
        """RAG için text parçaları oluştur"""
        chunks = []
        
        # Başlık chunk'ı
        if title and title.strip():
            chunks.append({
                'type': 'title',
                'text': title.strip(),
                'metadata': {'section': 'title'}
            })
        
        # Açıklama chunk'ları
        if description and description.strip():
            # Clean and normalize description
            clean_description = ' '.join(description.strip().split())
            desc_chunks = [clean_description[i:i+chunk_size] for i in range(0, len(clean_description), chunk_size)]
            for i, chunk in enumerate(desc_chunks):
                chunks.append({
                    'type': 'description',
                    'text': chunk,
                    'metadata': {'section': 'description', 'chunk_id': i}
                })
        
        # Altyazı chunk'ları
        if transcript and transcript.strip():
            # Clean and normalize transcript
            clean_transcript = ' '.join(transcript.strip().split())
            transcript_chunks = [clean_transcript[i:i+chunk_size] for i in range(0, len(clean_transcript), chunk_size)]
            for i, chunk in enumerate(transcript_chunks):
                chunks.append({
                    'type': 'transcript',
                    'text': chunk,
                    'metadata': {'section': 'transcript', 'chunk_id': i}
                })
        
        return chunks
    
    def save_data(self, videos_data: List[Dict], output_dir: str = "./data"):
        """YouTube verilerini kaydet"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Video metadata'ları
        if videos_data:
            df_videos = pd.DataFrame(videos_data)
            
            # Remove text_chunks column before saving to CSV/Parquet
            df_videos_to_save = df_videos.drop(columns=['text_chunks'], errors='ignore')
            
            df_videos_to_save.to_csv(f"{output_dir}/youtube_videos.csv", index=False, encoding='utf-8-sig')
            df_videos_to_save.to_parquet(f"{output_dir}/youtube_videos.parquet")
            
            # RAG için text chunks
            all_chunks = []
            for video in videos_data:
                for chunk in video.get('text_chunks', []):
                    chunk_data = {
                        'video_id': video['video_id'],
                        'video_title': video['title'],
                        'video_url': video['url'],
                        'chunk_type': chunk['type'],
                        'text': chunk['text'],
                        'metadata': json.dumps(chunk['metadata'])
                    }
                    all_chunks.append(chunk_data)
            
            if all_chunks:
                df_chunks = pd.DataFrame(all_chunks)
                df_chunks.to_csv(f"{output_dir}/youtube_text_chunks.csv", index=False, encoding='utf-8-sig')
                df_chunks.to_parquet(f"{output_dir}/youtube_text_chunks.parquet")
            
            logger.info(f"Toplam {len(videos_data)} video ve {len(all_chunks)} text chunk kaydedildi")
        else:
            logger.warning("No video data to save")

def main():
    """Test fonksiyonu"""
    try:
        # API anahtarını doğrudan .env'den al
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            logger.error("YouTube API anahtarı bulunamadı. Lütfen .env dosyasını kontrol edin.")
            return
        
        collector = YouTubeDataCollector(api_key)
        
        # Örnek video URL'leri
        sample_urls = [
            "https://youtu.be/yGmlodQTv-4?si=abU08_oyh62h8BE_",  # 
        ]
        
        # Video verilerini işle
        videos_data = collector.process_video_urls(sample_urls)
        
        # Verileri kaydet
        collector.save_data(videos_data)
        
        logger.info("İşlem tamamlandı! Veriler 'data' klasörüne kaydedildi.")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()