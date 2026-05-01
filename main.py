from fastapi import FastAPI, Query, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import asyncio
import aiohttp

import os

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


challenge_pages = Jinja2Templates(directory= "src/captchas/challenges")

# @app.get("/captchas/challenge/cf-turnstile")
@app.get("/captchas/cf-turnstile")
async def serveTurnstile():
    # a
    #todo: serve htmls
    # return True
    return challenge_pages.TemplateResponse(
        request={},
        name="cf-turnstile.html"
    )


@app.post("/captchas/verify/cf-turnstile")
async def explodeCFTurnstle(token:str):
    # this is NOT the right approach to get query and body lol
    # ig i need types and stuff, tmr
    # rn its just curl -X POST  "localhost:8000/captchas/verify/cf-turnstile?token=mrrp"
    print(token)

    # fix body logic above

    # cf: POST https://challenges.cloudflare.com/turnstile/v0/siteverify
    return {"message": token}


async def validateCFTurnstile(token:str, session:aiohttp.ClientSession):
    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    data = {
        'secret': "asd",
        'response': token
    }
    async with session.post(url=url, data=data) as response:
        try:
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Turnstile validation error: {e}")
            return {'success': False, 'error-codes': ['internal-error']}

















