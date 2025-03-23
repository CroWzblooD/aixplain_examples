import os
from dotenv import load_dotenv
import sys
import logging
import argparse
import json
import datetime
import re
import colorama
import time
from colorama import Fore, Style, Back

# Initialize colorama
colorama.init()

# Create logs directory if it doesn't exist
os.makedirs('./logs', exist_ok=True)

# Set up logging
logging.basicConfig(filename="./logs/summarizer.log", level=logging.INFO, format="%(asctime)s - %(message)s")

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

# Get API keys with fallbacks to environment variables
TEAM_API_KEY = os.getenv('TEAM_API_KEY')
GEMINI2_FLASH_ID = os.getenv('GEMINI2_FLASH_ID')

# Print API key status (for debugging)
print(f"TEAM_API_KEY loaded: {bool(TEAM_API_KEY)}")
print(f"GEMINI2_FLASH_ID loaded: {bool(GEMINI2_FLASH_ID)}")

# Define OutputFormat class for consistency
class OutputFormat:
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"

# Try to import the actual OutputFormat if available
try:
    from aixplain.modules.agent import OutputFormat as AIXOutputFormat
    # If import succeeds, replace our class with the imported one
    OutputFormat = AIXOutputFormat
    print(f"{Fore.GREEN}Successfully imported AIXplain OutputFormat{Style.RESET_ALL}")
except ImportError:
    # Keep using our custom OutputFormat class
    print(f"{Fore.YELLOW}Using custom OutputFormat class{Style.RESET_ALL}")

# Parse command line arguments
parser = argparse.ArgumentParser(description='AIXplain Summarizer Agent')
parser.add_argument('--server-mode', action='store_true', help='Run in server mode for API integration')
args = parser.parse_args()

# Helper function to extract content from AIXplain response
def extract_content(response):
    try:
        response_str = str(response)
        
        # Try different methods to extract the content
        if hasattr(response, 'output'):
            content = response.output
        elif hasattr(response, 'data') and hasattr(response.data, 'output'):
            content = response.data.output
        else:
            # Use regex to find the output
            output_match = re.search(r"output='([^']+)'", response_str)
            if output_match:
                content = output_match.group(1)
            else:
                # Try another pattern
                output_match = re.search(r"output=([^,]+),", response_str)
                if output_match:
                    content = output_match.group(1).strip("'")
                else:
                    # Extract content from the response string more aggressively
                    start_idx = response_str.find("output=")
                    if start_idx != -1:
                        end_idx = response_str.find(",", start_idx)
                        if end_idx != -1:
                            content = response_str[start_idx+7:end_idx].strip("'")
                        else:
                            content = response_str[start_idx+7:].strip("'")
                    else:
                        content = response_str
        
        # Clean up the content
        content = content.replace('\\n', '\n').replace('\\t', '\t')
        return content
        
    except Exception as e:
        logging.error(f"Error extracting content: {e}")
        return str(response)

# Import aixplain libraries
aixplain_available = False
gemini_model = None

try:
    # Set environment variables explicitly before importing
    os.environ['TEAM_API_KEY'] = TEAM_API_KEY
    os.environ['GEMINI2_FLASH_ID'] = GEMINI2_FLASH_ID
    
    # Import AIXplain libraries exactly like basic_agent.py does
    from aixplain.factories import AgentFactory
    try:
        from aixplain.modules.agent import OutputFormat
        print("Successfully imported aixplain libraries")
        aixplain_available = True
    except Exception as e:
        print(f"Error importing OutputFormat: {str(e)}")
        # We're already defining OutputFormat above as a fallback
    
    # Initialize the model using the approach from basic_agent.py
    if TEAM_API_KEY and GEMINI2_FLASH_ID and aixplain_available:
        try:
            # Create a simple agent with just the Gemini model
            agent = AgentFactory.create(
                name='Summarizer',
                description="A specialized summarizer that creates educational summaries.",
                tools=[
                    AgentFactory.create_model_tool(model=GEMINI2_FLASH_ID),
                ],
                api_key=TEAM_API_KEY  # Explicitly pass the API key
            )
            gemini_model = agent  # Use the agent as our model
            print(f"{Fore.GREEN}Created AIXplain agent for summarization{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error creating AIXplain agent: {str(e)}{Style.RESET_ALL}")
    
except Exception as e:
    print(f"Error importing aixplain libraries: {str(e)}")

# Create a mock model as fallback
if not aixplain_available or not gemini_model:
    class MockModel:
        def run(self, query, output_format=None, parameters=None):
            class MockResponse:
                def __init__(self, query):
                    self.output = f"This is a mock summary of your content. Since this is running in mock mode without API keys, I can't provide a real AI summary. Please make sure your API keys are properly set in the .env file."
            return MockResponse(query)
    
    gemini_model = MockModel()
    print("Using mock model due to error")

print("AIXplain summarizer agent is running. Waiting for input...")
sys.stdout.flush()  # Make sure the message is sent immediately

# Process input from stdin (API requests)
for line in sys.stdin:
    try:
        # Parse the JSON request
        request = json.loads(line.strip())
        prompt = request.get('prompt', '')
        language = request.get('language', 'English')
        summary_level = request.get('summaryLevel', 'simple')
        
        logging.info(f"Received summarization request: Language={language}, Level={summary_level}")
        logging.info(f"Content to summarize (first 100 chars): {prompt[:100]}...")
        
        if not prompt:
            print(json.dumps({
                "error": "Empty content received",
                "response": "Please provide content to summarize."
            }) + "\nRESPONSE_COMPLETE")
            sys.stdout.flush()
            continue
            
        # Process the summarization request
        try:
            # Create a specialized prompt for summarization
            enhanced_prompt = f"""
            SYSTEM INSTRUCTION: You are a specialized educational summarizer that creates text-only summaries.
            
            USER REQUEST: Create a {summary_level} educational summary in {language} language of the following content.
            
            IMPORTANT CONSTRAINTS:
            - DO NOT generate or include any images
            - DO NOT include any image URLs or HTML img tags
            - DO NOT include any markdown image syntax
            - Focus ONLY on creating a TEXT summary
            - Format with clear paragraphs and bullet points
            - If the summary level is 'simple', use simpler language and shorter sentences
            - If the summary level is 'detailed', provide more comprehensive information
            - If the summary level is 'advanced', include technical terms and deeper analysis
            
            CONTENT TO SUMMARIZE:
            {prompt}
            """
            
            print(f"{Fore.BLUE}Generating {summary_level} summary in {language}...{Style.RESET_ALL}", file=sys.stderr)
            
            # Run the model with text-only output format
            try:
                response = gemini_model.run(
                    query=enhanced_prompt,
                    output_format=OutputFormat.TEXT,
                    parameters={'max_tokens': 8192}
                )
                
                # Extract content from response
                response_content = extract_content(response)
                
                # Aggressively remove any image-related content
                response_content = re.sub(r'\[IMAGE_URL:.*?\]', '', response_content)
                response_content = re.sub(r'<img[^>]*>', '', response_content)
                response_content = re.sub(r'<a href="https://aixplain-modelserving-data.*?</a>', '', response_content)
                response_content = re.sub(r'!\[.*?\]\(.*?\)', '', response_content)  # Remove markdown images
                response_content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\.(?:jpg|jpeg|png|gif|webp)', '', response_content)
                
                print(f"{Fore.GREEN}Generated summary (first 100 chars): {response_content[:100]}...{Style.RESET_ALL}", file=sys.stderr)
            except Exception as model_error:
                print(f"{Fore.RED}Error running model: {model_error}{Style.RESET_ALL}", file=sys.stderr)
                # Provide a more helpful error message
                response_content = f"Error generating summary: {str(model_error)}. Please check your API keys and network connection."
                
                # Log the error for debugging
                logging.error(f"Model error: {model_error}")
                
                # Raise the error to be caught by the outer try-except
                raise model_error
            
            # Format the response as JSON and print to stdout
            result = {
                "response": response_content,
                "language": language,
                "summaryLevel": summary_level
            }
            
            # Print the JSON response to stdout (for the Node.js process to read)
            print(json.dumps(result) + "\nRESPONSE_COMPLETE")
            sys.stdout.flush()
            
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            print(json.dumps({
                "error": f"Error processing request: {str(e)}",
                "response": "Failed to generate summary due to an error."
            }) + "\nRESPONSE_COMPLETE")
            sys.stdout.flush()
            
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON received: {e}")
        print(json.dumps({
            "error": "Invalid JSON format",
            "response": "The request format is invalid. Please send a valid JSON object."
        }) + "\nRESPONSE_COMPLETE")
        sys.stdout.flush()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "response": "An unexpected error occurred while processing your request."
        }) + "\nRESPONSE_COMPLETE")
        sys.stdout.flush()

# Add this function after the imports and before the main code
def test_aixplain_connection():
    """Test the connection to AIXplain API"""
    if not TEAM_API_KEY:
        print(f"{Fore.RED}No API key provided{Style.RESET_ALL}")
        return False
        
    try:
        import requests
        response = requests.get(
            "https://api.aixplain.com/health",
            headers={"Authorization": f"Bearer {TEAM_API_KEY}"}
        )
        if response.status_code == 200:
            print(f"{Fore.GREEN}AIXplain API connection successful{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}AIXplain API connection failed: {response.status_code} {response.text}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error testing AIXplain connection: {e}{Style.RESET_ALL}")
        return False

# Call the test function after loading the API keys
if TEAM_API_KEY:
    api_connection_ok = test_aixplain_connection()
    print(f"API connection test result: {api_connection_ok}")
else:
    print(f"{Fore.YELLOW}Skipping API connection test - no API key provided{Style.RESET_ALL}")