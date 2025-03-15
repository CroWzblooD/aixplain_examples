import os
from dotenv import load_dotenv
load_dotenv('.env')

_ = os.getenv('TEAM_API_KEY')

gemini2_id = os.getenv('GEMINI2_FLASH_ID')
translate_eng_hin_id = os.getenv('TRANSLATE_ENG_HIN')
speech_syn_hin_bmale = os.getenv('SPEECH_SYN_HIN_BMALE')
if not translate_eng_hin_id or not speech_syn_hin_bmale or not gemini2_id:
    raise ValueError('[ERROR]: Failed to read model id')

from aixplain.factories.pipeline_factory import PipelineFactory
from aixplain.modules.pipeline.designer import Input
from aixplain.enums.data_type import DataType
pipeline = PipelineFactory.init('English question to Hindi audio')

text_input_node = Input(data='text_input', data_types=[DataType.TEXT], pipeline=pipeline)

padding_node = pipeline.text_generation(asset_id=gemini2_id)
translation_node = pipeline.translation(asset_id=translate_eng_hin_id)
speech_syn_node = pipeline.speech_synthesis(asset_id=speech_syn_hin_bmale)

text_input_node.link(padding_node, 'input', 'text')

padding_node.link(translation_node, 'data', 'text')
padding_out = padding_node.use_output('data')

translation_node.link(speech_syn_node, 'data', 'text')
translation_out = translation_node.use_output('data')

speech_syn_out = speech_syn_node.use_output('data')

pipeline.save()

prompt: str | None
with open('./prompts/008_prompt.txt', 'r') as file:
    prompt = file.read()

outputs = pipeline.run(data=prompt, max_tokens=10_000)
print(outputs)
