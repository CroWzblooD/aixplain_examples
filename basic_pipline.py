import os, logging, requests
import aixplain as ap
from dotenv import load_dotenv

logging.getLogger().setLevel(logging.WARNING)
load_dotenv('.env')

api_key = os.getenv('TEAM_API_KEY')
if not api_key:
    raise ValueError("API key not found. Set it in the .api_keys file")

aix = ap.Aixplain(api_key=api_key)
pipeline_id = os.getenv('PL_ENGLISH_QUERY_HINDI_AUDIO')

def exec_pipeline(input_data):
    try:
        if not pipeline_id:
            return '[ERROR]: PL_ENGLISH_QUERY_HINDI_AUDIO not found in .env'
        else:
            pipeline = aix.Pipeline.get(id=pipeline_id)
            response = pipeline.run(input_data)
            return response
    except Exception as e:
        return f'[ERROR]: {e}'

if __name__ == '__main__':
    with open('prompts/001_prompt.txt', 'r', encoding='utf-8') as file:
        prompt = file.read()
    pl_out = exec_pipeline(prompt)

    url = pl_out.get('data', [{}])[0].get('segments', [{}])[0].get('response') #type: ignore
    output_file = 'audios/eqha.mp3'
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_file, 'wb') as file:
            file.write(response.content)
    else:
        print(f"[ERROR]: File failed to download. Status code: {response.status_code}")
    print(pl_out)
