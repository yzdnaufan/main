import os

from dotenv import load_dotenv

from langchain.llms import OpenAI
from langchain.chains.router import MultiRetrievalQAChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder
from langchain.schema import (
    BaseOutputParser,
    SystemMessage,
    HumanMessage
)
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor
from langchain.agents.agent_toolkits import (
    create_retriever_tool,
    create_conversational_retrieval_agent,
)
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import AgentTokenBufferMemory
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent

from .retriever.MarketingRetriever import retriever_infos
from .retriever.BrandingRetriever import brand_retriever

load_dotenv()

llm = ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"))


system_message = SystemMessage(
        content=(
            "Do your best to answer the questions. "
            "Feel free to use any tools available to look up "
            "relevant information, only if necessary"
            "And answer ONLY in Bahasa Indonesia"
            "if related question was outside of bussiness, economics, or marketing, "
            "answer with 'Maaf pertanyaan diluar konteks yang saya pahami' or 'Saya tidak tahu'"
        )
)

# Agent Memory
# memory_key = "history"
# memory = AgentTokenBufferMemory(memory_key=memory_key, llm=llm)

prompt = OpenAIFunctionsAgent.create_prompt(
        system_message=system_message,
        extra_prompt_messages=[SystemMessage(content="Ingat, jawab dengan bahasa indonesia dan JANGAN pernah memberikan jawaban diluar konteks bisnis, ekonomi, ataupun marketing")]
    )

tools = [
    create_retriever_tool(
        retriever_infos['marketing'],
        "marketing",
        "Agent yang dibuat HARUS menggunakan tools ini bila pertanyaan yang dibuat adalah tentang marketing secara umum dan HARUS menjawab menggunakan bahasa indonesia"
    ),
    create_retriever_tool(
        retriever_infos['coke'],
        "coke",
        "Agent yang dibuat HARUS menggunakan tools ini bila pertanyaan yang dibuat adalah tentang contoh marketing dan branding pada kasus coca cola dan HARUS menjawab menggunakan bahasa indonesia"
    ),
    create_retriever_tool(
        brand_retriever['branding'],
        "branding",
        "Agent yang dibuat HARUS menggunakan tools ini bila pertanyaan yang dibuat adalah tentang branding dan HARUS menjawab menggunakan bahasa indonesia"
    ),
]


chat_model = ChatOpenAI()

def get_llm_response(message):
    return llm.predict(message)

def get_chat_response(message):
    return chat_model.predict(message)

async def get_agent_response(message):
    agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools,  verbose=True,
                                   return_intermediate_steps=True)

    result =  agent_executor({"input": message}, include_run_info=True)
    return result['output']

