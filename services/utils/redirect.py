"""
Simple redirect to decommission nest bts
"""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from get_ip import get_ip

app = FastAPI()


TARGET_DOMAIN = "https://botme.idk.dunkirk.sh"


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
)
async def catch_all_and_redirect(request: Request, path: str):
    redirect_url = f"{TARGET_DOMAIN}/{path}"

    if request.url.query:
        redirect_url += f"?{request.url.query}"
    print(get_ip(request))  # debugging
    return RedirectResponse(url=redirect_url, status_code=307)
