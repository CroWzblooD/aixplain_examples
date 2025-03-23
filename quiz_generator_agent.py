# Import modules needed for loading environment variables first
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file in the same directory as this script
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print(f"Loaded environment from {env_path}", file=sys.stderr)
else:
    print(f"Warning: Could not find .env file at {env_path}. Using environment variables directly.", file=sys.stderr)

# Retrieve required environment variables
TEAM_API_KEY = os.getenv("TEAM_API_KEY")
GEMINI2_FLASH_ID = os.getenv("GEMINI2_FLASH_ID")

# Debug: Print the value of TEAM_API_KEY (partially masked for security)
if TEAM_API_KEY:
    print(f"TEAM_API_KEY loaded: {TEAM_API_KEY[:5]}... (hidden for security)", file=sys.stderr)
else:
    print("TEAM_API_KEY not found in environment variables.", file=sys.stderr)

# Validate that the necessary environment variables are set
if not TEAM_API_KEY:
    print("Error: TEAM_API_KEY not set.", file=sys.stderr)
    sys.exit(1)

if not GEMINI2_FLASH_ID:
    print("Error: GEMINI2_FLASH_ID not set.", file=sys.stderr)
    sys.exit(1)

# Import remaining modules after environment variables are loaded
import json
import logging
from colorama import Fore, Style, init
from aixplain.factories import AgentFactory
from aixplain.modules.agent import OutputFormat

# Configure logging to file and stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quiz_generator.log"),
        logging.StreamHandler(sys.stderr)
    ]
)

# Initialize colorama for colored terminal output
init()

# Print startup messages
print(f"{Fore.CYAN}Quiz Generator Agent Starting...{Style.RESET_ALL}", file=sys.stderr)
print(f"{Fore.CYAN}==========================={Style.RESET_ALL}", file=sys.stderr)

# Create the AIXplain agent
try:
    agent = AgentFactory.create(
        name='QuizGenerator',
        description="A specialized quiz generator that creates quiz questions.",
        tools=[
            AgentFactory.create_model_tool(model=GEMINI2_FLASH_ID),
        ],
        api_key=TEAM_API_KEY
    )
    print(f"{Fore.GREEN}+ AIXplain agent created successfully{Style.RESET_ALL}", file=sys.stderr)
except Exception as e:
    print(f"{Fore.RED}x Error creating AIXplain agent: {str(e)}{Style.RESET_ALL}", file=sys.stderr)
    sys.exit(1)

def generate_quiz(prompt, category, language, question_count, question_type):
    """
    Generate quiz questions based on the provided parameters using the AIXplain agent.

    Args:
        prompt (str): Topic of the quiz.
        category (str): Category of the quiz (e.g., "Computer Science").
        language (str): Language for the quiz questions.
        question_count (int): Number of questions to generate.
        question_type (str): Type of questions (e.g., "multiple-choice").

    Returns:
        dict: Dictionary containing success status and generated questions or error details.
    """
    try:
        structured_prompt = f"""Generate {question_count} {question_type} questions about {prompt} for a {category} quiz in {language} language. 
        For each question, provide:
        1. The question text
        2. Four answer options (for multiple choice) or true/false options
        3. The correct answer index (0-based)
        4. A difficulty level (easy, medium, or hard)
        5. Points value (between 5-15 based on difficulty)
        
        Format the response as a JSON array of question objects with the following structure:
        [
          {{
            "question": "Question text here",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "correctAnswerIndex": 0,
            "difficulty": "medium",
            "points": 10
          }}
        ]"""
        
        # Run the agent with the structured prompt
        result = agent.run(
            query=structured_prompt,
            output_format=OutputFormat.TEXT,
            parameters={'max_tokens': 2048, 'temperature': 0.7}
        )
        
        # Log the full result for debugging
        logging.info(f"Agent response: {result}")
        
        # Extract generated text from the response
        if hasattr(result, 'data') and hasattr(result.data, 'output'):
            generated_text = result.data.output
        else:
            logging.error(f"Unexpected response structure: {result}")
            raise ValueError("Agent response does not contain accessible 'output' attribute")
        
        # If the final output is invalid, check intermediate steps
        if "Agent stopped" in generated_text or not generated_text.strip():
            logging.warning("Final output invalid, checking intermediate steps")
            if hasattr(result.data, 'intermediate_steps'):
                for step in result.data.intermediate_steps:
                    if isinstance(step, dict) and 'tool_steps' in step:
                        for tool_step in step['tool_steps']:
                            if tool_step.get('tool') == 'text-generation' and '```json' in tool_step.get('output', ''):
                                # Extract JSON from the output
                                output_text = tool_step['output']
                                start = output_text.find('```json') + 7
                                end = output_text.rfind('```')
                                if start > 6 and end > start:
                                    generated_text = output_text[start:end].strip()
                                    break
                        else:
                            continue  # Continue to next step if no match in tool_steps
                        break  # Exit outer loop if JSON is found
                else:
                    raise ValueError("No valid quiz output found in intermediate steps")
            else:
                raise ValueError("No intermediate steps available to extract quiz data")
        
        # Attempt to parse the generated text as JSON
        try:
            quiz_questions = json.loads(generated_text)
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing failed: {e}")
            # Fallback: Extract JSON array using regex
            import re
            json_match = re.search(r'$$ [\s\S]* $$', generated_text)
            if json_match:
                quiz_questions = json.loads(json_match.group(0))
            else:
                raise ValueError("Failed to extract valid JSON from the response")
        
        # Ensure the parsed output matches the expected key names
        for q in quiz_questions:
            if "correct_answer" in q:
                q["correctAnswerIndex"] = q.pop("correct_answer")
        
        return {
            "success": True,
            "questions": quiz_questions
        }
            
    except Exception as e:
        logging.error(f"Error generating quiz: {e}")
        return {
            "success": False,
            "error": str(e),
            "questions": []
        }
# Main execution block
# Main execution block
if __name__ == "__main__":
    # Print instructions for input
    print(f"\n{Fore.YELLOW}Waiting for input from stdin...{Style.RESET_ALL}", file=sys.stderr)
    print(f"{Fore.YELLOW}(If running directly in terminal, type JSON input and press Enter){Style.RESET_ALL}", file=sys.stderr)
    print(f"{Fore.YELLOW}Example: {{'prompt': 'Python programming', 'category': 'Computer Science', 'language': 'English', 'questionCount': 3, 'questionType': 'multiple-choice'}}{Style.RESET_ALL}\n", file=sys.stderr)
    
    try:
        # Read input from stdin
        input_data = sys.stdin.readline().strip()
        
        # Log the raw input data
        logging.info(f"Received raw input: {input_data}")
        
        try:
            # Parse JSON input
            request_data = json.loads(input_data)
            
            # Log the parsed data
            logging.info(f"Parsed request data: {request_data}")
            
            # Extract parameters with defaults
            prompt = request_data.get("prompt", "")
            category = request_data.get("category", "General Knowledge")
            language = request_data.get("language", "English")
            question_count = request_data.get("questionCount", 5)
            question_type = request_data.get("questionType", "multiple-choice")
            
            # Log the extracted parameters
            logging.info(f"Extracted parameters: prompt='{prompt}', category='{category}', language='{language}', question_count={question_count}, question_type='{question_type}'")
            
            # Generate quiz and output result
            result = generate_quiz(prompt, category, language, question_count, question_type)
            print(json.dumps(result))
            sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON received: {e}")
            print(json.dumps({
                "success": False,
                "error": "Invalid JSON format",
                "message": "The request format is invalid. Please send a valid JSON object."
            }))
            sys.stdout.flush()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            print(json.dumps({
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "message": "An unexpected error occurred while processing your request."
            }))
            sys.stdout.flush()
            
    except Exception as e:
        logging.error(f"Error reading input: {e}")
        print(json.dumps({
            "success": False,
            "error": f"Error reading input: {str(e)}",
            "message": "Failed to read input data."
        }))
        sys.stdout.flush()