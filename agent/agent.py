import os

from dotenv import load_dotenv

from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.schema import (
    BaseOutputParser,
    SystemMessage,
    HumanMessage
)

load_dotenv()

system_prompt = "You are a helpful AI assistant that ALWAYS answer in Bahasa Indonesia. That only talks about economy ONLY."
human_input ="{text}"

template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", human_input),
    ])

llm = OpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"))

chat_model = ChatOpenAI()

def get_llm_response(message):
    return llm.predict(message)

def get_chat_response(message):
    return chat_model.predict(message)

def get_basic_economy_response(message):

    chain = template.format_messages(text=message)
    return llm.predict_messages(chain)