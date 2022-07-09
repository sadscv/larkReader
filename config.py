# -*- coding: UTF-8 -*-
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# load from env
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
LARK_HOST = os.getenv("LARK_HOST")


