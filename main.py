from fastapi import FastAPI, Query, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# validation via http request -> external
import asyncio
import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl
ssl_ctx = ssl.create_default_context(cafile=certifi.where())

# env vars
import os
from dotenv import load_dotenv
load_dotenv()

CF_SECRET_KEY = os.getenv("CF_SECRET_KEY")

app = FastAPI()

# app content

@app.get("/")
async def root():
    return {"message": "Hello World"}


challenge_pages = Jinja2Templates(directory= "src/captchas/challenges")

# @app.get("/captchas/challenge/cf-turnstile")
@app.get("/captchas/cf-turnstile")
async def serveTurnstile(request: Request):
    # a
    #todo: serve htmls
    # return True
    return challenge_pages.TemplateResponse(
        request=request,
        name="cf-turnstile.html"
    )


@app.post("/captchas/verify/cf-turnstile")
async def explodeCFTurnstle(data:dict):
    # this is NOT the right approach to get query and body lol
    # ig i need types and stuff, tmr
    # rn its just curl -X POST  "localhost:8000/captchas/verify/cf-turnstile?token=mrrp"
    token = data.get("token")
    print(token)

    # fix body logic above

    # cf: POST https://challenges.cloudflare.com/turnstile/v0/siteverify
    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    data = {
        'secret': CF_SECRET_KEY, # secret, i spent too long doing dotenv
        'response': token
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, data=data, ssl=ssl_ctx) as response:
            try:
                response.raise_for_status()
                response_json = await response.json()
                print(response_json)
                return  response_json
            except Exception as e:
                print(f"Turnstile validation error: {e}")
                return {'success': False, 'error-codes': ['internal-error']}




