# env vars
import os
from dotenv import load_dotenv

load_dotenv()

CF_SECRET_KEY = os.getenv("CF_SECRET_KEY")
CF_SITE_KEY = os.getenv("CF_SITE_KEY")
import certifi
import ssl

ssl_ctx = ssl.create_default_context(cafile=certifi.where())
