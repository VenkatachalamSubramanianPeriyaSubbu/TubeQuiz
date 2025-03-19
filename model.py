import json
import boto3
import re

bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")

def generate_quiz(transcript, model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"):
    """
    Uses AWS Bedrock with Claude models to generate quiz questions.

    Parameters
    ----------
    transcript : str
        The text transcript from which to generate the quiz.
    model_id : str, optional
        The Claude model ID to use. Default is Claude 3.5 Sonnet v2.

    Returns
    -------
    str
        The generated quiz in JSON format.
    """
    # Initialize the Bedrock runtime client
    bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")

    # Claude models use the Messages API format
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": f"Generate a quiz using this transcript as reference:\n{transcript}\n"
                          "The questions should point to video instead of transcript.\n"
                          "The quiz should include:\n"
                          "- 5 Multiple Choice Questions (MCQs)\n"
                          "- 3 Short Answer Questions\n"
                          "- Format the output in JSON.\n"
                          "Example Output:\n"
                          "{\n"
                          "  \"mcqs\": [\n"
                          "    {\"question\": \"What is AI?\", \"options\": [\"Artificial Intelligence\", \"Automated Input\", \"None\"], \"answer\": \"Artificial Intelligence\"}\n"
                          "  ],\n"
                          "  \"text_questions\": [\n"
                          "    {\"question\": \"Explain how AI models learn?\"}\n"
                          "  ]\n"
                          "}"
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

        # Read and parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        # Extract the response text from the Claude message structure
        quiz_text = response_body.get('content', [{}])[0].get('text', '')
        
        # Try to parse the quiz as JSON
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
                
                # Ensure that reference answers are available for text questions
                if 'text_questions' in quiz_json:
                    for question in quiz_json['text_questions']:
                        if 'answer' not in question:
                            # Generate a reference answer if missing
                            question['answer'] = generate_reference_answer(transcript, question['question'], model_id)
                
                return quiz_json
            else:
                return quiz_text
        except Exception as e:
            print(f"Error parsing quiz JSON: {e}")
            return quiz_text
    
    except Exception as e:
        print(f"Error invoking model: {e}")
        return None

def generate_reference_answer(transcript, question, model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"):
    """
    Generate a reference answer for a text question.
    """
    # Initialize the Bedrock runtime client
    bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
    
    # Claude models use the Messages API format
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": f"Provide a detailed reference answer to this question:\n\nQuestion: {question}\n\n \n\nTranscipt: {transcript}\n\n"
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

        # Read and parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Extract the response text from the Claude message structure
        return response_body.get('content', [{}])[0].get('text', '')
    
    except Exception as e:
        print(f"Error generating reference answer: {e}")
        return "No reference answer available."
