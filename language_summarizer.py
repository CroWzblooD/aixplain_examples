import json
import sys
import os
import re
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
TEAM_API_KEY = os.getenv('TEAM_API_KEY')
GEMINI2_FLASH_ID = os.getenv('GEMINI2_FLASH_ID')

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Check if aixplain library is available
try:
    from aixplain.factories import AgentFactory
    from aixplain.modules.agent import OutputFormat
    aixplain_available = True
except ImportError:
    aixplain_available = False
    logging.warning("aixplain library not found. Install it with 'pip install aixplain'.")

# Initialize the agent
if aixplain_available and TEAM_API_KEY and GEMINI2_FLASH_ID:
    try:
        agent = AgentFactory.create(
            name='Summarizer',
            description="A specialized summarizer for educational content.",
            tools=[AgentFactory.create_model_tool(model=GEMINI2_FLASH_ID)],
            api_key=TEAM_API_KEY
        )
        logging.info("Successfully created AIxplain agent.")
    except Exception as e:
        logging.error(f"Error creating AIxplain agent: {e}")
        agent = None
else:
    agent = None
    logging.warning("Agent not created due to missing API key, model ID, or library.")

# Fallback to a mock agent if necessary
if not agent:
    class MockAgent:
        def run(self, query, output_format=None, parameters=None):
            return "Mock summary: This is a placeholder due to missing API keys or library."
    agent = MockAgent()
    logging.info("Using mock agent as fallback.")

# Function to extract content from the response
def extract_content(response):
    try:
        response_str = str(response)
        if hasattr(response, 'output'):
            content = response.output
        elif hasattr(response, 'data') and hasattr(response.data, 'output'):
            content = response.data.output
        else:
            output_match = re.search(r"output='([^']+)'", response_str)
            if output_match:
                content = output_match.group(1)
            else:
                content = response_str
        return content.replace('\\n', '\n').replace('\\t', '\t')
    except Exception as e:
        logging.error(f"Error extracting content: {e}")
        return str(response)

# Summarize text function
def summarize_text(text, language, summary_level):
    # Map language codes to full names
    lang_map = {
        "en": "English",
        "hi": "Hindi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "mr": "Marathi",
        "gu": "Gujarati"
    }
    lang_name = lang_map.get(language, "English")

    # Construct a detailed prompt
    prompt = f"""
    SYSTEM INSTRUCTION: You are a specialized educational summarizer that creates text-only summaries.

    USER REQUEST: Create a {summary_level} educational summary in {lang_name} language of the following content.

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
    {text}
    """

    try:
        response = agent.run(
            query=prompt,
            output_format=OutputFormat.TEXT,
            parameters={'max_tokens': 8192}
        )
        summary = extract_content(response)
        return {"success": True, "summary": summary}
    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return {"success": False, "error": str(e)}

# Main loop to process input from stdin
if __name__ == "__main__":
    print("Language summarizer agent is running")
    sys.stdout.flush()

    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            prompt = request.get("prompt")  # Text from OCR or frontend input
            language = request.get("language", "en")  # User-requested language
            summary_level = request.get("summaryLevel", "detailed")  # Summary level

            if not prompt:
                result = {"success": False, "error": "Empty content received"}
            else:
                result = summarize_text(prompt, language, summary_level)

            # Output result in JSON format with delimiter
            print(json.dumps(result) + "\nRESPONSE_COMPLETE")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON received: {e}")
            print(json.dumps({"success": False, "error": "Invalid JSON format"}) + "\nRESPONSE_COMPLETE")
            sys.stdout.flush()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            print(json.dumps({"success": False, "error": str(e)}) + "\nRESPONSE_COMPLETE")
            sys.stdout.flush()