import os
import json
from collections import OrderedDict

from typing import Any, Dict, List

from sqlalchemy.orm import Session
from controller.db_models import User
from src.agent.neo_conversational_chat.prompt import PREFIX, PREFIX_TEMPLATE_INDONESIA

from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain.vectorstores import Qdrant

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.vectorstores import Chroma

from langchain.agents import Tool, initialize_agent, AgentType, AgentExecutor
from langchain.prompts import MessagesPlaceholder
from langchain.schema.messages import SystemMessage
from langchain.schema import LLMResult
from langchain.chains.conversation.memory import ConversationBufferMemory
from src.agent.vectorstore import ConversationVectorStoreRetrieverMemory
from langchain.docstore.document import Document
from langchain import OpenAI
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSerperAPIWrapper
from langchain.tools.google_serper.tool import GoogleSerperRun
from langchain.memory.chat_message_histories import RedisChatMessageHistory
from langchain.chains import ConversationalRetrievalChain
from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler

# qdrant vectorstore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff, HnswConfigDiff, PayloadSchemaType, Filter, FieldCondition, MatchValue


# embeddings = HuggingFaceEmbeddings(model_name=HUGGINGFACE_EMBEDDING_MODEL)
embeddings = OpenAIEmbeddings()

def get_or_create_vectorstore(id, data_src, embeddings):
    persist_directory = f"db_{id}"
    if not os.path.exists(persist_directory):
        return Chroma.from_documents(split_texts(data_src), embeddings, persist_directory=persist_directory,collection_name=f"{id}-col")
    else: 
        return Chroma(persist_directory=persist_directory, embedding_function=embeddings, collection_name=f"{id}-col")

def split_texts(text_name):
  loader = TextLoader(text_name, encoding="utf-8")
  documents = loader.load()
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
  texts = text_splitter.split_documents(documents)
  return texts



# with open('data/course_text.json', 'r') as f:
#     raw_texts = json.load(f)

# docsearch = Qdrant.from_texts(raw_texts, embeddings, collection_name="future-skills-courses", url="http://qdrant:6333")

# llm = OpenAI(temperature=0.0) # default to gpt-3.5-turbo
llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0.0)

# future_skills_courses = RetrievalQA.from_chain_type(llm=OpenAI(temperature=0.0), chain_type="stuff", retriever=docsearch.as_retriever())

tools = [
    # Tool(
    #     name='Pijar-Courses',
    #     func=future_skills_courses.run,
    #     coroutine=future_skills_courses.arun,
    #     description="A document list of course and their description. You must always use this when you need to answer question related to capacity building programs, "
    #                 "courses, or learning resources. Input should be as clear as possible with detailed context using the same language. "
    #                 "Example input 'Do you have any recommendation for the following topics: Leadership, Fintech, and Marketing?', "
    #                 "'Give me a course recommendation for the following topics: Sustainability, Socialpreneur!'",
    # ),
    GoogleSerperRun(
        api_wrapper=GoogleSerperAPIWrapper(gl='id', hl='id'),
        description= (
              "API untuk penelusuran Google berbiaya rendah khusus untuk informasi seputar dunia perkuliahan. "
              "NEO bisa menggunakan alat ini saat NEO perlu mencari informasi yang akurat khusus untuk menjawab pertanyaan berkaitan dengan topik yang berkaitan dengan universitas, kampus, perkuliahan, karir, dan pengembangan diri, tidak untuk topik-topik di luar itu. "
              "Masukan harus seringkas dan sejelas mungkin dan diformat sebagai istilah pencarian tunggal untuk Google. "
        ),
    )
]

class DebugCallback(AsyncCallbackHandler):
    """Async callback handler that can be used to handle callbacks from langchain."""

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        print("Debug Prompts".center(50, "-"))
        print(prompts[0])
    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        print("Debug Response".center(50, "-"))
        print(response)


class PijarAgent(object):
    def __init__(self, id, user_name, user_biodata):
        self.memory = None
        self.agent_chain = None

        self.id = id
        self.user_name = user_name
        self.user_biodata = user_biodata

        self.initialize_agent()
        self.state = 'gpt'

        # self.quiz = Quiz()
        # self.dummy_project = DummyProject()
        # self.dummy_mentor = DummyMentor()

    def initialize_agent(self):
        # Check if collection exists, if not create it
        self.chat_vectorstore = Qdrant(qdrant_client, collection_name='chat_messages', embeddings=embeddings)
        self.chat_retriever = self.chat_vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                'k' : 12,
                'fetch_k' : 36,
                'lambda_mult' : 0.75,
                'filter' : Filter(
                    must=[
                        FieldCondition(
                            key="metadata.user_id",
                            match=MatchValue(value=str(self.id))
                        )
                    ]
                ),
            }
        )
        
        self.chat_memory = RedisChatMessageHistory(url='redis://redis:6379/0', ttl=600, session_id=f"chat_memory_{self.id}")
        # self.memory = ConversationBufferMemory(memory_key="chat_history", chat_memory=self.message_history, return_messages=True)
        self.memory = ConversationVectorStoreRetrieverMemory(retriever=self.chat_retriever, memory_key="chat_history", chat_memory=self.chat_memory, return_messages=True)

        agent_kwargs = {
            "system_message" : SystemMessage(content=PREFIX_TEMPLATE_INDONESIA.format(name=self.user_name, biodata=self.user_biodata)),
            "extra_prompt_messages": [
                SystemMessage(content=f"Berikut adalah riwayat obrolan NEO dengan {self.user_name} yang mungkin relevan dan dapat membantu NEO memahami konteks percakapan saat ini."),
                MessagesPlaceholder(variable_name="chat_history"),
                SystemMessage(content=f"Perlu diingat, NEO sedang melakukan interaksi dengan mahasiswa bernama {self.user_name}, NEO akan selalu mengingat nama ini dalam setiap percakapan dan menyebutkan atau menyapa namanya setiap memberikan jawaban. Penting untuk dipahami, NEO tidak dapat menjawab pertanyaan yang berada di luar domain kehidupan kampus, universitas, perkuliahan, karir, atau pengembangan diri. Dalam kasus seperti itu yang di luar ranah NEO, NEO akan selalu menolak dan mengarahkan pengguna dengan sopan, menekankan keahliannya dalam hal-hal yang hanya berkaitan dengan kehidupan kampus. Terakhir, NEO Chatbot diprogram untuk merespons hanya dalam bahasa Indonesia, tanpa memandang bahasa yang digunakan dalam masukan pengguna, termasuk bahasa Inggris dan lainnya. Sehingga apapun bahasa yang digunakan oleh pengguna, NEO akan selalu memberikan jawaban dalam bahasa Indonesia, bukan bahasa lainnya.")
                ],
        }

        self.agent_chain = initialize_agent(
                                tools, 
                                llm, 
                                agent=AgentType.OPENAI_FUNCTIONS, 
                                verbose=True, 
                                agent_kwargs=agent_kwargs, 
                                memory=self.memory
                            )
        
    def clear_memory(self):
        qdrant_client.delete(
            collection_name='chat_messages',
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="metadata.user_id",
                        match=MatchValue(value=str(self.id))
                    )
                ]
            )
        )
        self.chat_memory.clear()
    
    async def async_generate(self, text):
        
        # if ENVIRONMENT_TYPE == 'development':
        #     resp = await self.agent_chain.arun(input=text, user_id = self.id, callbacks=[DebugCallback(),])
        # else:
        #     resp = await self.agent_chain.arun(input=text, user_id = self.id)
        resp = await self.agent_chain.arun(input=text, user_id = self.id, callbacks=[DebugCallback(),])
        return resp

    async def get_response(self, answer):
        print(f"State -> {self.state}")
 
        if self.state == 'gpt':
            try:
                response = await self.async_generate(answer)
            except Exception as e:
                print(e)
                
                response = "Telah terjadi galat. Silakan coba lagi."
            return response


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    
class AgentFactory(metaclass=Singleton):
    def __init__(self, max_agents=500):
        self.max_agents = max_agents
        self.agents = OrderedDict()

    def get_agent(self, user_id, db: Session):
        if user_id not in self.agents:
            if len(self.agents) >= self.max_agents:
                self.agents.popitem(last=False)
            user = db.query(User).filter(User.id == user_id).first()
            user_name = user.name
            user_bio = user.biodata
            self.agents[user_id] = PijarAgent(id=user_id, user_name=user_name, user_biodata=user_bio)
        else:
            # Move the recently accessed agent to the end of the dictionary
            self.agents.move_to_end(user_id)
        return self.agents[user_id]