# YouTube Transcript Extraction

## Requirements

### `requirements.txt`
```txt
pandas
numpy
matplotlib
youtube_transcript_api
openai-whisper
yt-dlp
```

## Installation Instructions

Since `ffmpeg` is required for audio processing, install it separately before installing the Python dependencies.

### Install `ffmpeg`
#### For Linux (Ubuntu/Debian)
```sh
sudo apt update && sudo apt install ffmpeg
```

#### For macOS (using Homebrew)
```sh
brew install ffmpeg
```

#### For Windows (using Chocolatey)
```powershell
choco install ffmpeg
```

Or manually download it from [FFmpeg official site](https://ffmpeg.org/download.html).

## Installing Python Dependencies
Once `ffmpeg` is installed, run:
```sh
pip install -r requirements.txt
```

This ensures all required libraries are properly installed for video transcription.

