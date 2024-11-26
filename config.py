# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or "chave_secreta_padrao_para_desenvolvimento"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or "sqlite:///tasks.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_KEY = os.getenv("API_KEY")
