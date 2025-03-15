import os
from dotenv import load_dotenv
load_dotenv('.env')

_ = os.getenv('TEAM_API_KEY')
gemini2_id = os.getenv('GEMINI2_FLASH_ID')

from aixplain.factories import ModelFactory

class ModelAccessException(Exception):
    def __init__(self, message, model_id):
        super().__init__(message)
        self.model_id = model_id

def query_model(prompt: str, model_id: str) -> str :
    if model_id:
        gemini2 = ModelFactory.get(model_id=model_id)
        result = gemini2.run(data=prompt, parameters={"max_tokens": 4096})
        return result.data
    else:
        raise ModelAccessException("Cannot access model", model_id)

prompt: str | None = None
try:
    with open('./prompts/005_prompt.txt', 'r') as file:
        prompt = file.read()
    if prompt and gemini2_id:
        gemini2_output = query_model(prompt, gemini2_id)
        print(gemini2_output)
except ModelAccessException as e:
    print(f'[ERROR]: {e}')
    print(f'model_id: {e.model_id}')
