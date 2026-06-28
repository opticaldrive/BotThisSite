from fastapi import Request
def get_ip(request: Request):
    xff = request.headers.get("X-Forwarded-For") # caddy revprox does this
    ip = xff.split(",")[0].strip() if xff else request.client.host
    return ip