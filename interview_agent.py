import os
from dotenv import load_dotenv
import sys
import logging
import argparse
import json
import datetime
import re
import colorama
from colorama import Fore, Style, Back

# Initialize colorama
colorama.init()

# Create logs directory if it doesn't exist
os.makedirs('./logs', exist_ok=True)
# Create prompts directory if it doesn't exist
os.makedirs('./prompts', exist_ok=True)

# Set up logging
logging.basicConfig(filename="./logs/interview_agent.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Load environment variables from .env file
# Try different paths for the .env file
possible_env_paths = ['.env', '../.env', '../../.env']
env_loaded = False

for env_path in possible_env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"Loaded environment from {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("Warning: Could not find .env file. Using environment variables directly.")

# Import Gemini after environment variables are loaded
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    print("Error: google-generativeai package not installed. Please install it with 'pip install google-generativeai'")
    sys.exit(1)

# Configure API key
api_key = os.getenv("GEMINI2_FLASH_ID")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)

# Set up the model
model_name = "gemini-1.5-flash"
model = genai.GenerativeModel(
    model_name,
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
)

def get_interview_questions(job_details, company_info, question_type="general"):
    logging.info(f"Generating {question_type} interview questions for job: {job_details[:50]}...")
    
    # Enhanced prompt requesting JSON output
    prompt = f"""
    You are an expert interviewer for {company_info}.
    
    Based on the following job details, generate 5 interview questions that would be asked during a job interview:
    
    Job Details:
    {job_details}
    
    Please format your response as a JSON array, where each element is an object with:
    {{
        "question": "The interview question",
        "explanation": "What the interviewer is looking for",
        "sample_answer": "A sample good answer"
    }}
    
    Ensure the response is valid JSON and contains exactly 5 questions. If the job details are insufficient, make reasonable assumptions based on the context.
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse the response as JSON
        questions_data = json.loads(response_text)
        if isinstance(questions_data, list) and len(questions_data) == 5 and all(
            isinstance(q, dict) and "question" in q and "explanation" in q and "sample_answer" in q 
            for q in questions_data
        ):
            return questions_data
        else:
            logging.error("Response does not match expected JSON format")
            return [{"question": "Error: Unexpected response format", "explanation": response_text, "sample_answer": ""}]
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return [{"question": "Error: Failed to parse response as JSON", "explanation": response_text, "sample_answer": ""}]
    except Exception as e:
        logging.error(f"Error generating interview questions: {str(e)}")
        return [{"question": "Error: Failed to generate questions", "explanation": str(e), "sample_answer": ""}]


if not args.interactive and args.job_details and args.company_info:
    question_type = args.question_type or "general"
    questions = get_interview_questions(args.job_details, args.company_info, question_type)
    response = {
        "questions": questions,
        "timestamp": datetime.datetime.now().isoformat()
    }
    print(json.dumps(response))
elif not args.interactive:
    # API mode via stdin
    try:
        input_data = json.loads(sys.stdin.read())
        job_details = input_data.get("job_details", "")
        company_info = input_data.get("company_info", "")
        question_type = input_data.get("question_type", "general")
        
        if not job_details or not company_info:
            print(json.dumps({"error": "Job details and company info are required"}))
        else:
            questions = get_interview_questions(job_details, company_info, question_type)
            response = {
                "questions": questions,
                "timestamp": datetime.datetime.now().isoformat()
            }
            print(json.dumps(response))
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()