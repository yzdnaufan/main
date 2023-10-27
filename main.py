import os
import dotenv

from fastapi import FastAPI, Request
from pydantic import BaseModel

from models.post_body import Phone
from controller.query import (get_first_4_users, 
                              verify_phone
                              )         
from src.agent.agent import AgentFactory   

from agent.agent import (get_chat_response,
                         get_llm_response,
                         get_agent_response)

dotenv.load_dotenv(".env")

app = FastAPI()

class Message(BaseModel):
    message: str

def get_data():
    p = os.getenv("FS_DATABASE_URL")
    return {"message": "Hello World",
            "FS_DATABASE_URL": p}

a = AgentFactory()

# 
# Start of POST route
# code
#

@app.post("/ask")
async def answer(request: Request):
    try:
        req = await request.json()
        question = req['question']
        # return {"message":question}
        return {"message":a.async_generate(question)}
    except Exception as e:
        return {"error", str(e)}
 
@app.post("/phone")
def root(phone: Phone):
    isinDB, isVerified = verify_phone(phone.phone)
    
    # check if phone is verified or not
    getStatus= lambda x: "and verified" if x else "but not verified"
    
    if isinDB:
        return {"message": "Your phone is on our database "+ getStatus(isVerified)}
    else:
        return {"message": "Your phone is not on our database"}


@app.post("/chat")
def root(message: Message):
    t = message.message
    return {"message": str(get_chat_response(t))}

@app.post("/llm")
def root(message: Message):
    t = message.message
    return {"message": str(get_llm_response(t))}

@app.post("/hello")
def root(message: Message):
    return {"message": "Hello " + message.message}


@app.post("/agent")
def root(message: Message):
    t = message.message
    return {"message": get_agent_response(t) }

#
# Start of GET route
# code
# 

@app.get("/")
def root():
    return get_data()

@app.get("/items/{item_id}")
def root(item_id: int):
    return {"item_id": item_id, "message": "Hello World"}

@app.get("/first-user")
async def root():
    return await get_first_4_users()


