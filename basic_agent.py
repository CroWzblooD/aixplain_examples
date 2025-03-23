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
logging.basicConfig(filename="./logs/gemini2.log", level=logging.INFO, format="%(asctime)s - %(message)s")

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
STABLE_DIFFUSION_ID = os.getenv('STABLE_DIFFUSION_ID')
SPEECH_TO_TEXT_ID = os.getenv('SPEECH_TO_TEXT_ID', '6610617ff1278441b6482530')  # Add speech-to-text model ID

# Print API key status (for debugging)
print(f"TEAM_API_KEY loaded: {bool(TEAM_API_KEY)}")
print(f"GEMINI2_FLASH_ID loaded: {bool(GEMINI2_FLASH_ID)}")
print(f"STABLE_DIFFUSION_ID loaded: {bool(STABLE_DIFFUSION_ID)}")
print(f"SPEECH_TO_TEXT_ID loaded: {bool(SPEECH_TO_TEXT_ID)}")

# Define OutputFormat class for mock agent
class OutputFormat:
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"

# Parse command line arguments
parser = argparse.ArgumentParser(description='AIXplain Agent')
parser.add_argument('--server-mode', action='store_true', help='Run in server mode for API integration')
args = parser.parse_args()

# Check if agent description file exists, create it if it doesn't
agent_desc_path = 'prompts/001_agent_desc.txt'
if not os.path.exists(agent_desc_path):
    with open(agent_desc_path, 'w') as file:
        file.write("You are a helpful AI assistant that can teach various subjects to students of all ages. Format your responses with proper paragraphs, bullet points using '•' instead of '*', and numbered lists where appropriate. Remember previous parts of the conversation and refer back to them when relevant.")

with open(agent_desc_path, 'r') as file:
    agent_description = file.read()

# Create a conversation history file if it doesn't exist
history_dir = './conversation_history'
os.makedirs(history_dir, exist_ok=True)

# Function to load conversation history
def load_conversation_history():
    try:
        history_files = sorted([f for f in os.listdir(history_dir) if f.endswith('.json')])
        if not history_files:
            return []
        
        latest_file = os.path.join(history_dir, history_files[-1])
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading conversation history: {e}")
        return []

# Function to save conversation history
def save_conversation_history(history):
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(history_dir, f"conversation_{timestamp}.json")
        with open(filename, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving conversation history: {e}")

# Function to extract and format content from response
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
try:
    # Set environment variables explicitly before importing
    os.environ['TEAM_API_KEY'] = TEAM_API_KEY
    os.environ['GEMINI2_FLASH_ID'] = GEMINI2_FLASH_ID
    os.environ['STABLE_DIFFUSION_ID'] = STABLE_DIFFUSION_ID
    os.environ['SPEECH_TO_TEXT_ID'] = SPEECH_TO_TEXT_ID
    
    from aixplain.factories import AgentFactory
    from aixplain.modules.agent import OutputFormat
    print("Successfully imported aixplain libraries")
except Exception as e:
    print(f"Error importing aixplain libraries: {str(e)}")
    # We're already defining OutputFormat above as a fallback

# Create the agent
try:
    if TEAM_API_KEY and GEMINI2_FLASH_ID and STABLE_DIFFUSION_ID:
        from aixplain.factories import AgentFactory
        
        # Create the agent with explicit API key and add speech-to-text tool
        agent = AgentFactory.create(
            name='Personalized Teacher',
            description=agent_description,
            tools=[
                AgentFactory.create_model_tool(model=GEMINI2_FLASH_ID),
                AgentFactory.create_model_tool(model=STABLE_DIFFUSION_ID),
                AgentFactory.create_model_tool(model=SPEECH_TO_TEXT_ID),  # Add speech-to-text model
            ],
            api_key=TEAM_API_KEY  # Explicitly pass the API key
        )
        print("Created real AIXplain agent")
    else:
        raise ValueError(f"Missing required API keys: TEAM_API_KEY={bool(TEAM_API_KEY)}, GEMINI2_FLASH_ID={bool(GEMINI2_FLASH_ID)}, STABLE_DIFFUSION_ID={bool(STABLE_DIFFUSION_ID)}")
except Exception as e:
    print(f"Error creating AIXplain agent: {str(e)}")
    # Create a mock agent as fallback
    class MockAgent:
        def run(self, query, output_format=None, parameters=None):
            class MockResponse:
                def __init__(self, query):
                    self.output = f"This is a response to your query: '{query}'\n\nSince this is running in mock mode without API keys, I can't provide a real AI response. Please make sure your API keys are properly set in the .env file."
            return MockResponse(query)
    
    agent = MockAgent()
    print("Using mock agent due to error")

# Load conversation history
conversation_history = load_conversation_history()

# Print server mode message
print("AIXplain agent server is running. Waiting for input...")
sys.stdout.flush()  # Make sure the message is sent immediately

# Process input from stdin (API requests)
for line in sys.stdin:
    try:
        # Parse the JSON request
        request = json.loads(line.strip())
        prompt = request.get('prompt', '')
        request_id = request.get('requestId', 'unknown')
        language = request.get('language', 'English')
        is_voice_input = request.get('isVoiceInput', False)  # Check if this is voice input
        audio_data = request.get('audioData', None)  # Get audio data if available
        
        logging.info(f"Received request {request_id}: {prompt[:100]}...")
        logging.info(f"Is voice input: {is_voice_input}")
        
        if not prompt and not audio_data:
            print("Error: Empty prompt and no audio data received" + "RESPONSE_COMPLETE")
            sys.stdout.flush()
            continue
            
        # Process the request
        try:
            # Handle voice input if present
            if is_voice_input and audio_data:
                try:
                    logging.info("Processing voice input...")
                    # Use the speech-to-text model to transcribe the audio
                    transcription_response = agent.run(
                        query=audio_data,
                        output_format=OutputFormat.TEXT,
                        parameters={'model_id': SPEECH_TO_TEXT_ID}
                    )
                    
                    # Extract the transcribed text
                    transcribed_text = extract_content(transcription_response)
                    logging.info(f"Transcribed text: {transcribed_text}")
                    
                    # Use the transcribed text as the prompt
                    prompt = transcribed_text if transcribed_text else prompt
                    
                    # Add a note about the transcription
                    prompt = f"[Transcribed from voice] {prompt}"
                    
                except Exception as e:
                    logging.error(f"Error processing voice input: {e}")
                    # Continue with the original prompt if available
                    if not prompt:
                        print(f"Error processing voice input: {str(e)}" + "RESPONSE_COMPLETE")
                        sys.stdout.flush()
                        continue
            
            # Check if this is an image generation request
            is_image_request = any(keyword in prompt.lower() for keyword in 
                                ['image', 'picture', 'photo', 'generate', 'create', 'draw'])
            
            if is_image_request:
                # Add specific instructions for image generation
                formatted_prompt = f"""
                Generate an image based on this description: {prompt}
                
                When returning the image, please format your response as follows:
                1. A brief description of what was generated
                2. The image URL clearly marked with [IMAGE_URL: <a href="URL_HERE">Image Link</a>]
                """
                
                # Log that we're generating an image
                logging.info(f"Generating image for prompt: {prompt[:100]}...")
                print(f"Generating image for: {prompt[:100]}...")
                
                # Use the agent to generate the image
                response = agent.run(
                    query=formatted_prompt,
                    output_format=OutputFormat.TEXT,
                    parameters={'max_tokens': 8192}
                )
                
                # Extract the content
                content = extract_content(response)
                
                # Make sure the image URL is properly formatted
                # No additional processing needed as we'll handle this in the route.js file
                
            else:
                # Regular text response formatting
                formatted_prompt = f"""
                Please respond to the following prompt with well-formatted content.
                Format your response with:
                - Use proper HTML formatting: <strong>for bold text</strong> instead of **text**
                - Use bullet points with • symbol
                - Proper paragraph spacing
                - If the response should be in {language}, please ensure the entire response is in {language}
                
                Here is the prompt: {prompt}
                """
                
                response = agent.run(
                    query=formatted_prompt,
                    output_format=OutputFormat.TEXT,
                    parameters={'max_tokens': 8192}
                )
                
                # Extract the content
                content = extract_content(response)
                
                # Format the content for better display
                content = content.replace('\\n', '\n').replace('\\t', '\t')
                
                # Clean up any processing messages or artifacts
                content = re.sub(r'Processing request.*?\.\.\.', '', content)
                content = re.sub(r'This is a dummy response.*?\.', '', content)
                
                # Ensure consistent formatting for bullet points
                content = re.sub(r'^[-*•]\s+', '• ', content, flags=re.MULTILINE)
                
                # Convert markdown bold to HTML bold
                content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
                
                # Ensure proper paragraph spacing
                content = re.sub(r'\n{3,}', '\n\n', content)
            
        except Exception as e:
            logging.error(f"Error running agent: {e}")
            content = f"I'm sorry, I encountered an error processing your request: {str(e)}"
        
        # Add to conversation history
        conversation_history.append({
            "user": prompt,
            "assistant": content,
            "timestamp": datetime.datetime.now().isoformat(),
            "request_id": request_id,
            "language": language
        })
        
        # Save conversation history
        if len(conversation_history) % 3 == 0:
            save_conversation_history(conversation_history)
        
        # Send the response back to the API - Fix encoding issues
        try:
            # Use utf-8 encoding explicitly when printing
            print(content + "RESPONSE_COMPLETE")
            sys.stdout.flush()
        except UnicodeEncodeError:
            # If there's an encoding error, try to encode to utf-8 and then decode with 'replace' strategy
            encoded_content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            print(encoded_content + "RESPONSE_COMPLETE")
            sys.stdout.flush()
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logging.error(error_msg)
        print(f"An error occurred: {error_msg}RESPONSE_COMPLETE")
        sys.stdout.flush()

# Save conversation history before exiting
save_conversation_history(conversation_history)

# Add this code to the server mode section of the Python script

# In the server mode section, update the request handling:
if args.server_mode:
    print(f"{Fore.GREEN}Starting AIXplain agent in server mode...{Style.RESET_ALL}")
    
    # Import required libraries for AIXplain
    try:
        import aixplain
        from aixplain.factories import PipelineFactory
        from aixplain.utils import OutputFormat
        print(f"{Fore.GREEN}AIXplain library imported successfully{Style.RESET_ALL}")
    except ImportError:
        print(f"{Fore.RED}Error: AIXplain library not found. Using mock responses.{Style.RESET_ALL}")
        aixplain_available = False
    else:
        aixplain_available = True
        
    # Initialize AIXplain client if available
    if aixplain_available and TEAM_API_KEY:
        try:
            aixplain.client.init(api_key=TEAM_API_KEY)
            print(f"{Fore.GREEN}AIXplain client initialized successfully{Style.RESET_ALL}")
            
            # Initialize models
            gemini_model = None
            stable_diffusion_model = None
            
            if GEMINI2_FLASH_ID:
                try:
                    gemini_model = PipelineFactory.get_pipeline(GEMINI2_FLASH_ID)
                    print(f"{Fore.GREEN}Gemini model loaded successfully{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error loading Gemini model: {e}{Style.RESET_ALL}")
            
            if STABLE_DIFFUSION_ID:
                try:
                    stable_diffusion_model = PipelineFactory.get_pipeline(STABLE_DIFFUSION_ID)
                    print(f"{Fore.GREEN}Stable Diffusion model loaded successfully{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error loading Stable Diffusion model: {e}{Style.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}Error initializing AIXplain client: {e}{Style.RESET_ALL}")
            aixplain_available = False
    
    print(f"{Fore.GREEN}AIXplain agent server is running{Style.RESET_ALL}")
    
    # Process requests from stdin
    while True:
        try:
            # Read request from stdin
            request_json = sys.stdin.readline().strip()
            if not request_json:
                continue
                
            request = json.loads(request_json)
            prompt = request.get('prompt', '')
            request_id = request.get('requestId', '')
            language = request.get('language', 'English')
            feature = request.get('feature', 'text')
            
            print(f"Processing request {request_id}...")
            
            # Process the request based on the feature
            if aixplain_available and gemini_model:
                try:
                    if "image" in prompt.lower() and stable_diffusion_model:
                        # Extract the image description
                        image_prompt = re.search(r"Generate an image about: (.*?)(?:\.|$)", prompt)
                        if image_prompt:
                            image_prompt = image_prompt.group(1)
                        else:
                            image_prompt = prompt
                            
                        # Generate image
                        image_response = stable_diffusion_model.run(
                            input=image_prompt,
                            output_format=OutputFormat.HTML
                        )
                        
                        # Extract the image URL from the response
                        response_content = extract_content(image_response)
                        print(f"Generated image response: {response_content[:100]}...")
                        
                        # Send the response
                        print(response_content + "\nRESPONSE_COMPLETE")
                        sys.stdout.flush()
                        continue
                    
                    # For text-based responses (summaries, quizzes, etc.)
                    if feature == 'summary':
                        # Add specific instructions for summary
                        enhanced_prompt = f"Create a comprehensive educational summary in {language}. {prompt}"
                    elif feature == 'quiz':
                        # Add specific instructions for quiz
                        enhanced_prompt = f"Create a 5-question multiple-choice quiz in {language} with 4 options per question. Clearly mark the correct answer for each question. {prompt}"
                    else:
                        enhanced_prompt = prompt
                    
                    # Run the model
                    response = gemini_model.run(
                        input=enhanced_prompt,
                        output_format=OutputFormat.TEXT
                    )
                    
                    # Extract content from response
                    response_content = extract_content(response)
                    print(f"Generated response: {response_content[:100]}...")
                    
                    # Send the response
                    print(response_content + "\nRESPONSE_COMPLETE")
                    sys.stdout.flush()
                
                except Exception as e:
                    error_message = f"Error processing request: {str(e)}"
                    print(error_message + "\nRESPONSE_COMPLETE")
                    sys.stdout.flush()
            else:
                # Mock response for testing when AIXplain is not available
                mock_responses = {
                    'summary': f"This is a mock summary in {language} language. The summary would explain the key concepts in a {feature} format.",
                    'quiz': """<p class="font-medium mt-4">1. What is the capital of France?</p>
                            <p class="ml-4">A) London</p>
                            <p class="ml-4">B) Berlin</p>
                            <p class="ml-4">C) Paris</p>
                            <p class="ml-4">D) Madrid</p>
                            <p class="text-green-600 font-medium mt-2">Correct Answer: C) Paris</p>""",
                    'translation': f"This is a mock translation to {language}.",
                    'text': "This is a mock text response."
                }
                
                # Get appropriate mock response based on feature
                response_content = mock_responses.get(feature, mock_responses['text'])
                
                # Add delay to simulate processing
                time.sleep(2)
                
                # Send the mock response
                print(response_content + "\nRESPONSE_COMPLETE")
                sys.stdout.flush()
        except json.JSONDecodeError:
            print("Error: Invalid JSON request\nRESPONSE_COMPLETE")
            sys.stdout.flush()
        except Exception as e:
            print(f"Unexpected error: {str(e)}\nRESPONSE_COMPLETE")
            sys.stdout.flush()

# Helper function to extract content from AIXplain response
def extract_content(response):
    if isinstance(response, dict):
        return response.get('output', str(response))
    return str(response)
