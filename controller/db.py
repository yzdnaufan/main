import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

load_dotenv(".env")

db_url = os.getenv('FS_DATABASE_URL')

engine = create_engine(db_url)

Base = declarative_base()


