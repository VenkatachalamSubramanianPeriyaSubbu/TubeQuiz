import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter
import whisper
import os
import yt_dlp
from yt_dlp import YoutubeDL
import boto3
import requests

s3_client = boto3.client("s3")
BUCKET_NAME = "tubequiz-bucket"
transcribe_client = boto3.client("transcribe")

def extract_video_id(youtube_url):
    """
    Extracts the video id from a youtube url

    Parameters
    ----------
    youtube_url : str
        The youtube url

    Returns
    -------
    str
        The video id
    """
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, youtube_url)
    return match.group(1) if match else None

def download_audio(link):
    video_id = extract_video_id(link)
    output_path = f"{video_id}_audio"
    ydl_opts = {
        'format':'bestaudio/best',
        'outtmpl':output_path,
        'postprocessors':[{
            'key':'FFmpegExtractAudio',
            'preferredcodec':'mp3',
            'preferredquality':'192'
        }],

    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])

    return output_path+'.mp3'

def upload_s3(file_path):
    s3_key = f"audio/{file_path}"
    s3_client.upload_file(file_path, BUCKET_NAME, s3_key)
    return f"s3://{BUCKET_NAME}/{s3_key}"

def transcribe_audio(s3_uri, job_name):

    """Transcribes an audio file using AWS Transcribe."""
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': s3_uri},
        MediaFormat='mp3',
        LanguageCode='en-US'
    )

    # Wait for the job to complete
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break

    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        return transcript_uri
    
