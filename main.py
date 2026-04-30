from fastapi import FastAPI, Query, Body


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}





@app.post("/captchas/verify/cf-turnstile")
async def explodeCFTurnstle(token:str):
    # this is NOT the right approach to get query and body lol
    # ig i need types and stuff, tmr
    # rn its just curl -X POST  "localhost:8000/captchas/verify/cf-turnstile?token=mrrp"
    print(token)
    return {"message": token}



















