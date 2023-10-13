from sqlalchemy.orm import sessionmaker
from controller.db import engine
from controller.db_models import User

Session = sessionmaker(bind=engine)

async def get_first_4_users():
    session = Session()
    p = session.query(User.full_name, User.phone, User.verified).filter(User.id.between(1,4)).all()
    session.close()
    return p

def verify_phone(phone: str):
    session = Session()
    if session.query(User).filter(User.phone == phone).count() != 0:
        verified = session.query(User.verified).filter(User.phone == phone).all()[0][0]
        session.close()
        return (True, verified)
    session.close()
    return (False, False)
    


