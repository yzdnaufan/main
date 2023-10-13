import os
import dotenv
from fastapi import FastAPI, Request

from models.post_body import Phone
from controller.query import (get_first_4_users, 
                              verify_phone
                              )         
from src.agent.agent import AgentFactory          

dotenv.load_dotenv(".env")

app = FastAPI()

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
