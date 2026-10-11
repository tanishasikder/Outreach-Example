import duckdb
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from routers import input

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = duckdb.connect("data/data.duckdb")
    yield
    app.state.db.close()

app = FastAPI(lifespan=lifespan)
app.include_router(input.router)
