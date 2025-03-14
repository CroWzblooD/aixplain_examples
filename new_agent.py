import os
from dotenv import load_dotenv
load_dotenv('.env')

import logging
logging.basicConfig(filename="./logs/gemini2.log", level=logging.INFO, format="%(asctime)s - %(message)s")

_ = os.getenv('TEAM_API_KEY')
gemini2_id = os.getenv('GEMINI2_FLASH_ID')
if not gemini2_id:
    raise ValueError('[ERROR]: gemini2_id failed to get')

from aixplain.factories import AgentFactory
from aixplain.modules.agent import OutputFormat

agent_description: str | None
with open('prompts/001_agent_desc.txt', 'r') as file:
    agent_description = file.read()

agent = AgentFactory.create(
    name='Personalized Teacher',
    description=agent_description,
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
