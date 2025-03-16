import json
import boto3

bedrock_client = boto3.client("bedrock-runtime")

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
                "content": f"Generate a quiz from this transcript:\n{transcript}\n"
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
        return response_body.get('content', [{}])[0].get('text', '')
    
    except Exception as e:
        print(f"Error invoking model: {e}")
        return None

# Example Usage
if __name__ == "__main__":
    
    quiz_result = generate_quiz(transcript)
    print(quiz_result)