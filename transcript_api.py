import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from youtube_transcript_api import YouTubeTranscriptApi
import whisper
import os
from yt_dlp import YoutubeDL

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
    
def download_video_and_extract_transcript(link):
    """
    Downloads an audio file from the youtube video and extracts the transcript

    Parameters
    ----------
    link : str
        The youtube video link

    Returns
    -------
    str
        The transcript of the video
    """
    try:
        # Download audio
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl' : 'audios/%(title)s.%(ext)s',
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            print(filename)
        # Extract transcript
        model = whisper.load_model("base")
        result = model.transcribe(filename)
        transcript = result['text']
        return transcript
    except Exception as e:
        print(e)
        return None