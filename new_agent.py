import os
from dotenv import load_dotenv
load_dotenv('.env')

import logging
logging.basicConfig(filename="./logs/gemini2.log", level=logging.WARNING, format="%(asctime)s - %(message)s")

_ = os.getenv('TEAM_API_KEY')
gemini2_id = os.getenv('GEMINI2_FLASH_ID')
if not gemini2_id:
    raise ValueError('[ERROR]: gemini2_id failed to get')

from aixplain.factories import AgentFactory
from aixplain.modules.agent import OutputFormat

agent = AgentFactory.create(
    name='Personalized Teacher',
    description="""
    You are a teacher of a 11 grade student studying in the Indian School
    Board of CBSE. You need to answer the students questions diligently,
    succinctly and in a simple and understandable manner.

    You need to terse with you answers and be to the point. Do not go off
    topic and blabber around too much. Stick extremely closely to the NCERT
    books as prescribed by the board. These are standard books in the board's
    curriculum and are also freely available online.

    If the student starts to question something outside of the syllabus or
    acts in a bad fashion then correct the student and focus on begin on track.
    """,
    tools=[
        AgentFactory.create_model_tool(model=gemini2_id),
    ],
)

prompt: str | None
with open('./prompts/006_prompt.txt', 'r') as file:
    prompt = file.read()

if prompt:
    response = agent.run(
        query=prompt,
        output_format=OutputFormat.MARKDOWN,
        parameters={'max_tokens': 8192}
    )
    os.system('clear')

    print(f'\033[34m{'-' * 100}\033[0m')
    print(response['data']['output'])
    print(f'\033[34m{'-' * 100}\033[0m')
    print(f'run_time: {response['run_time']}')
else:
    print('Agent failed to respond')
