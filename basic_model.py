import os, logging
import aixplain as ap
from dotenv import load_dotenv

logging.getLogger().setLevel(logging.WARNING)
load_dotenv('.env')

api_key = os.getenv('TEAM_API_KEY')
if not api_key:
    raise ValueError("API key not found. Set it in the .api_keys file")

aix = ap.Aixplain(api_key=api_key)
model_id = os.getenv('GEMINI2_FLASH_ID')

def query_model(prompt):
    try:
        if not model_id:
            return '[ERROR]: Failed to get model id'
        else:
            model = aix.Model.get(id=model_id)
            response = model.run(prompt, max_tokens=5000)
            return response.data
    except Exception as e:
        return f"[ERROR]: {e}"


if __name__ == '__main__':
    with open('prompts/001_prompt.txt', 'r', encoding='utf-8') as file:
        prompt = file.read()
    model_out = query_model(prompt)
    # print(f"\033[32m{model_out}\033[0m")
    print(model_out)
