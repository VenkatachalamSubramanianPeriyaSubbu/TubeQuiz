import re
import yt_dlp
import boto3
from youtube_transcript_api import YouTubeTranscriptApi

# AWS Configuration
S3_BUCKET_NAME = "tubequiz-bucket"
S3_REGION = "us-west-1"
TRANSCRIBE_REGION = "us-west-1"

# Initialize AWS clients
s3_client = boto3.client("s3", region_name=S3_REGION)
transcribe_client = boto3.client("transcribe", region_name=TRANSCRIBE_REGION)

def extract_video_id(youtube_url: str) -> str:
    """
    Extracts the video ID from a YouTube URL.
    """
    regex = (r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|"
             r"(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})")
    match = re.search(regex, youtube_url)
    return match.group(1) if match else None

def get_transcript(video_id):
    """
    Gets the transcript of a youtube video

    Parameters
    ----------
    video_id : str
        The video id

    Returns
    -------
    str
        The transcript of the video
    """
    try:
        full_transcript = " "
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        for line in transcript:
            full_transcript += line['text'] + " "
        return full_transcript
    except Exception as e:
        print(e)
        return None

def download_audio(link: str) -> str:
    """
    Downloads the audio from a YouTube video as an MP3 file.
    """
    video_id = extract_video_id(link)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    
    output_path = f"{video_id}_audio.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{video_id}_audio",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    return output_path

def upload_s3(file_path: str) -> str:
    """
    Uploads a file to AWS S3 and returns the S3 URI.
    """
    s3_key = f"audio/{file_path}"
    s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
    return f"s3://{S3_BUCKET_NAME}/{s3_key}"

def transcribe_audio(s3_uri: str, job_name: str) -> str:
    """
    Transcribes an audio file using AWS Transcribe and returns the transcript URI.
    """
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': s3_uri},
        MediaFormat='mp3',
        LanguageCode='en-US'
    )
    
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        state = status['TranscriptionJob']['TranscriptionJobStatus']
        if state in ['COMPLETED', 'FAILED']:
            break
    
    if state == 'COMPLETED':
        return status['TranscriptionJob']['Transcript']['TranscriptFileUri']
    else:
        raise RuntimeError("Transcription job failed")
    

