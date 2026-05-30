# everything-in-one-file until i fix this mess
from fastapi import FastAPI, Query, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, desc, func

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter
