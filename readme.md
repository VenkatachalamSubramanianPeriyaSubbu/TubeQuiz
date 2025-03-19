# YouTube Quiz Generator

## Overview
The YouTube Quiz Generator is a Streamlit web application that allows users to generate quizzes from YouTube videos. It transcribes the video, extracts key points, and creates multiple-choice and short-answer questions using AI.

## Features
- Extracts transcripts from YouTube videos
- Uses AWS Transcribe if no transcript is available
- Generates quizzes using Claude 3.5 (via AWS Bedrock)
- Supports MCQs and short-answer questions
- Evaluates text-based answers with AI feedback

## Installation
1. Clone the repository:
   ```sh
   git clone <repo-url>
   cd youtube-quiz-generator
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Set up AWS credentials for `boto3`:
   - Ensure you have an AWS account.
   - Configure your credentials using:
     ```sh
     aws configure
     ```

## Dependencies
The application requires the following Python packages:
- `streamlit` – Web UI framework
- `boto3` – AWS SDK for Python
- `yt-dlp` – Download YouTube audio/video
- `youtube-transcript-api` – Fetch video transcripts
- `requests` – Handling HTTP requests
- `json` – JSON data parsing
- `os` – OS-related functions
- `time` – Time-related functions
- `re` – Regular expressions for pattern matching

## Usage
1. Run the Streamlit app:
   ```sh
   streamlit run app.py
   ```
2. Enter a YouTube video URL to generate a quiz.
3. Answer the quiz questions and submit for evaluation.

## Technologies Used
- **Streamlit** – for the UI
- **YouTube Transcript API** – for retrieving transcripts
- **yt-dlp** – for downloading video audio
- **AWS S3 & Transcribe** – for audio transcription
- **Claude AI (AWS Bedrock)** – for quiz generation and answer evaluation

## Tech Stack
### Backend
- **Python** – Core programming language
- **Boto3** – AWS SDK for interacting with cloud services
- **AWS Bedrock** – For AI-based quiz generation and evaluation
- **AWS Transcribe** – Converts audio to text for transcript generation

### Frontend
- **Streamlit** – Web-based UI framework for interaction
- **HTML/CSS** – Embedded in Streamlit for UI customization

## Future Enhancements
- Support for more languages
- Improved UI design
- Advanced quiz customization options

## License
MIT License
