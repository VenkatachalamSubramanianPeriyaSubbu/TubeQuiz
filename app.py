import streamlit as st
import json
import os
import time
import re
import boto3
from transcript import extract_video_id, download_audio, upload_s3, transcribe_audio, get_transcript
from model import generate_quiz

#AWS 
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]

# Set page configuration
st.set_page_config(
    page_title="YouTube Quiz Generator",
    page_icon="🎬",
    layout="wide",
)

# Dark mode CSS
st.markdown("""
<style>
    .main {
        background-color: #121212;
        color: #E0E0E0;
    }
    .stApp {
        max-width: 1000px;
        margin: 0 auto;
    }
    h1, h2, h3 {
        color: #BB86FC;
    }
    .stButton>button {
        background-color: #BB86FC;
        color: #121212;
        border-radius: 4px;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #A66EFC;
    }
    .card {
        background-color: #1E1E1E;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
    }
    .mcq {
        background-color: #2D2D2D;
        border-radius: 4px;
        padding: 10px;
        margin: 8px 0;
    }
    .mcq.correct {
        border-left: 4px solid #03DAC6;
    }
    .mcq.incorrect {
        border-left: 4px solid #CF6679;
    }
    .stTextInput>div>div>input {
        background-color: #2D2D2D;
        color: #E0E0E0;
    }
    .result-card {
        background-color: #2D2D2D;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
    }
    .score-display {
        font-size: 1.4rem;
        font-weight: bold;
        text-align: center;
    }
    .feedback {
        margin-top: 10px;
        padding: 10px;
        border-radius: 4px;
    }
    .feedback.good {
        background-color: rgba(3, 218, 198, 0.2);
    }
    .feedback.average {
        background-color: rgba(251, 192, 45, 0.2);
    }
    .feedback.poor {
        background-color: rgba(207, 102, 121, 0.2);
    }
    footer {
        color: #888888;
        font-size: 0.8rem;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("🎬 YouTube Quiz Generator")

# Description
st.markdown("""
<div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; margin: 20px 0;">
    Generate quizzes from YouTube videos in just a few clicks.
</div>
""", unsafe_allow_html=True)

# URL input
video_url = st.text_input("Enter YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

# Generate button
generate_button = st.button("Generate Quiz", use_container_width=True)

# Session state variables
if 'quiz' not in st.session_state:
    st.session_state.quiz = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'error' not in st.session_state:
    st.session_state.error = None
if 'show_answers' not in st.session_state:
    st.session_state.show_answers = False
if 'mcq_responses' not in st.session_state:
    st.session_state.mcq_responses = {}
if 'text_responses' not in st.session_state:
    st.session_state.text_responses = {}
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False
if 'quiz_score' not in st.session_state:
    st.session_state.quiz_score = None
if 'text_feedback' not in st.session_state:
    st.session_state.text_feedback = {}

# Function to evaluate text answers
def evaluate_text_answer(user_answer, question, model_answer, model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"):
    """
    Evaluates a user's text answer compared to the model answer
    
    Parameters
    ----------
    user_answer : str
        The user's submitted answer
    question : str
        The quiz question
    model_answer : str
        The reference answer from the model
    model_id : str, optional
        The Claude model ID to use
        
    Returns
    -------
    dict
        A dictionary containing the score and feedback
    """
    # Initialize the Bedrock runtime client
    bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
    
    # Create prompt for evaluating the answer
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": f"""Evaluate this student answer to a quiz question. 

Question: {question}

Reference Answer: {model_answer}

Student Answer: {user_answer}

Grade the answer based on general evaluation, don't use reference answer as a metric and scale it from 0-10, where:
- 0-3: Poor (missing key information or incorrect)
- 4-6: Average (partially correct but incomplete)
- 7-10: Good (correct and comprehensive)

Provide a short feedback explaining the score and what could be improved.
Format your response as a JSON object with two keys: "score" (integer) and "feedback" (string).
Example: {{"score": 8, "feedback": "Good job mentioning X. Could be improved by including Y."}}
"""
            }
        ]
    })

    try:
        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )

        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        content = response_body.get('content', [{}])[0].get('text', '')
        
        # Extract JSON from the response
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            feedback_json = json.loads(json_match.group(1))
            return feedback_json
        else:
            return {"score": 0, "feedback": "Error evaluating answer"}
    
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return {"score": 0, "feedback": f"Error: {e}"}

# Process the video when button is clicked
if generate_button and video_url:
    st.session_state.processing = True
    st.session_state.error = None
    st.session_state.quiz = None
    st.session_state.mcq_responses = {}
    st.session_state.text_responses = {}
    st.session_state.quiz_submitted = False
    st.session_state.quiz_score = None
    st.session_state.text_feedback = {}
    
    try:
        # Status message and progress
        status = st.empty()
        progress = st.progress(0)
        
        # Extract video ID
        status.text("Analyzing video URL...")
        progress.progress(10)
        video_id = extract_video_id(video_url)
        
        if not video_id:
            st.session_state.error = "Invalid YouTube URL. Please check and try again."
        else:
            # Try to get transcript
            status.text("Retrieving transcript...")
            progress.progress(30)
            
            try:
                transcript = get_transcript(video_id)
                transcript_found = True
            except Exception:
                transcript_found = False
                transcript = None
            
            # If no transcript, download audio and transcribe
            if not transcript_found:
                status.text("No transcript found. Downloading audio...")
                progress.progress(40)
                audio_path = download_audio(video_url)
                
                status.text("Uploading to AWS S3...")
                progress.progress(60)
                s3_uri = upload_s3(audio_path)
                
                status.text("Transcribing audio (this may take a few minutes)...")
                progress.progress(70)
                transcript_uri = transcribe_audio(s3_uri, f"transcription-{video_id}")
                
                # Fetch transcript from AWS Transcribe
                import requests
                transcript_data = requests.get(transcript_uri).json()
                transcript = transcript_data['results']['transcripts'][0]['transcript']
            
            # Generate quiz
            status.text("Generating quiz questions...")
            progress.progress(90)
            
            quiz_text = generate_quiz(transcript)
            
            # Parse quiz JSON
            try:
                if isinstance(quiz_text, str):
                    # Try to extract JSON from the text if wrapped in markdown
                    json_match = re.search(r'```json\s*(.*?)\s*```', quiz_text, re.DOTALL)
                    if json_match:
                        quiz_text = json_match.group(1)
                    
                    # Another attempt to find JSON in the text
                    json_match = re.search(r'(\{.*\})', quiz_text, re.DOTALL)
                    if json_match:
                        quiz_text = json_match.group(1)
                    
                    quiz_json = json.loads(quiz_text)
                else:
                    quiz_json = quiz_text
                
                st.session_state.quiz = quiz_json
                
            except Exception as e:
                st.session_state.error = f"Error parsing quiz output: {str(e)}"
            
            progress.progress(100)
            status.text("Quiz generated successfully!")
            time.sleep(1)
            
            # Clean up temporary files
            if 'audio_path' in locals() and os.path.exists(audio_path):
                os.remove(audio_path)
            
            status.empty()
            progress.empty()
            
    except Exception as e:
        st.session_state.error = f"An error occurred: {str(e)}"
    
    st.session_state.processing = False

# Display processing status
if st.session_state.processing:
    st.info("Processing your request. This may take a minute...")

# Display error if any
if st.session_state.error:
    st.error(st.session_state.error)

# Handle quiz submission
def submit_quiz():
    st.session_state.quiz_submitted = True
    
    # Calculate MCQ score
    mcq_correct = 0
    mcq_total = len(st.session_state.quiz['mcqs'])
    
    for q_id, answer in st.session_state.mcq_responses.items():
        correct_answer = st.session_state.quiz['mcqs'][int(q_id)]['answer']
        if answer == correct_answer:
            mcq_correct += 1
    
    # Calculate MCQ score - 50% of total score
    mcq_score = (mcq_correct / mcq_total) * 50 if mcq_total > 0 else 0
    
    # Evaluate text answers
    text_scores = []
    text_total = len(st.session_state.quiz['text_questions'])
    
    # Create a progress bar for text evaluation
    if text_total > 0:
        eval_progress = st.progress(0)
        eval_status = st.empty()
        eval_status.info("Evaluating your text answers...")
    
    for idx, (q_id, answer) in enumerate(st.session_state.text_responses.items()):
        question = st.session_state.quiz['text_questions'][int(q_id)]['question']
        
        # Get model answer if available, otherwise use empty string
        model_answer = ""
        if 'answer' in st.session_state.quiz['text_questions'][int(q_id)]:
            model_answer = st.session_state.quiz['text_questions'][int(q_id)]['answer']
        
        # Update progress
        if text_total > 0:
            eval_progress.progress((idx + 0.5) / text_total)
            eval_status.info(f"Evaluating question {int(q_id) + 1} of {text_total}...")
        
        # Evaluate the answer
        if answer.strip():  # Only evaluate non-empty answers
            feedback = evaluate_text_answer(answer, question, model_answer)
            st.session_state.text_feedback[q_id] = feedback
            text_scores.append(feedback['score'])
        else:
            st.session_state.text_feedback[q_id] = {"score": 0, "feedback": "No answer provided"}
        
        # Update progress again
        if text_total > 0:
            eval_progress.progress((idx + 1) / text_total)
    
    # Clear progress bar and status
    if text_total > 0:
        eval_progress.empty()
        eval_status.empty()
    
    # Calculate text score - 50% of total score (each question is worth up to 10 points)
    # Scale to get a score out of 50
    text_score = (sum(text_scores) / (text_total * 10)) * 50 if text_total > 0 and text_scores else 0
    
    # Calculate total score
    total_score = mcq_score + text_score
    
    st.session_state.quiz_score = {
        "mcq_correct": mcq_correct,
        "mcq_total": mcq_total,
        "mcq_score": mcq_score,
        "text_score": text_score,
        "total_score": total_score
    }

# Display quiz if available
if st.session_state.quiz and not st.session_state.processing:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    if not st.session_state.quiz_submitted:
        # Multiple Choice Questions
        st.subheader("Multiple Choice Questions")
        
        if 'mcqs' in st.session_state.quiz:
            for i, mcq in enumerate(st.session_state.quiz['mcqs']):
                st.markdown(f"**Q{i+1}. {mcq['question']}**")
                
                # Create radio buttons for options
                selected_option = st.radio(
                    f"Select your answer for question {i+1}",
                    mcq['options'],
                    key=f"mcq_{i}",
                    label_visibility="collapsed"
                )
                
                # Store the selected answer
                st.session_state.mcq_responses[str(i)] = selected_option
                
                st.write("")
        
        # Short Answer Questions
        st.subheader("Short Answer Questions")
        
        if 'text_questions' in st.session_state.quiz:
            for i, q in enumerate(st.session_state.quiz['text_questions']):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                
                # Text area for answer
                user_answer = st.text_area(
                    f"Your answer for question {i+1}",
                    key=f"text_{i}",
                    height=120
                )
                
                # Store the text answer
                st.session_state.text_responses[str(i)] = user_answer
                
                st.write("")
        
        # Submit button
        st.button("Submit Quiz", on_click=submit_quiz, use_container_width=True)
    
    else:
        # Display results after submission
        st.subheader("Quiz Results")
        
        # Display overall score
        score_percentage = int(st.session_state.quiz_score["total_score"])
        
        # Score card with color based on score
        score_color = "#03DAC6" if score_percentage >= 70 else "#FBBC05" if score_percentage >= 50 else "#CF6679"
        
        st.markdown(f"""
        <div class="result-card">
            <div class="score-display" style="color: {score_color}">
                Your Score: {score_percentage}/100
            </div>
            <div style="text-align: center; margin-top: 5px;">
                MCQ: {st.session_state.quiz_score["mcq_correct"]}/{st.session_state.quiz_score["mcq_total"]} correct
                | Text: {int(st.session_state.quiz_score["text_score"])} points
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # MCQ Review
        st.subheader("Multiple Choice Questions Review")
        
        if 'mcqs' in st.session_state.quiz:
            for i, mcq in enumerate(st.session_state.quiz['mcqs']):
                # Get user's answer
                user_answer = st.session_state.mcq_responses.get(str(i), "Not answered")
                correct_answer = mcq['answer']
                is_correct = user_answer == correct_answer
                
                # Display question
                st.markdown(f"**Q{i+1}. {mcq['question']}**")
                
                # Display each option with appropriate styling
                for option in mcq['options']:
                    if option == correct_answer:
                        st.markdown(f'<div class="mcq correct">✓ {option} (Correct Answer)</div>', unsafe_allow_html=True)
                    elif option == user_answer and not is_correct:
                        st.markdown(f'<div class="mcq incorrect">✗ {option} (Your Answer)</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="mcq">{option}</div>', unsafe_allow_html=True)
                
                st.write("")
        
        # Text Questions Review
        st.subheader("Short Answer Questions Review")
        
        if 'text_questions' in st.session_state.quiz:
            for i, q in enumerate(st.session_state.quiz['text_questions']):
                # Get user's answer
                user_answer = st.session_state.text_responses.get(str(i), "Not answered")
                feedback = st.session_state.text_feedback.get(str(i), {"score": 0, "feedback": "Not evaluated"})
                
                # Display question
                st.markdown(f"**Q{i+1}. {q['question']}**")
                
                # Display user's answer
                st.text_area("Your Answer", value=user_answer, height=100, disabled=True, key=f"answer_{i}")
                
                # Display reference answer if available
                if 'answer' in q:
                    with st.expander("Reference Answer"):
                        st.write(q['answer'])
                
                # Display feedback with color based on score
                feedback_class = "good" if feedback['score'] >= 7 else "average" if feedback['score'] >= 4 else "poor"
                
                st.markdown(f"""
                <div class="feedback {feedback_class}">
                    <strong>Score: {feedback['score']}/10</strong><br>
                    {feedback['feedback']}
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
        
        # Try Again button
        if st.button("Take Another Quiz", use_container_width=True):
            st.session_state.quiz = None
            st.session_state.mcq_responses = {}
            st.session_state.text_responses = {}
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = None
            st.session_state.text_feedback = {}
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<footer>
    YouTube Quiz Generator © 2025 | Powered by Claude 3.5 Sonnet
</footer>
""", unsafe_allow_html=True)