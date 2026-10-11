import duckdb
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from routers import input
import joblib
from fastapi.middleware.cors import CORSMiddleware
from src.models.rag_models import get_gem_model, get_hug_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = duckdb.connect("data/data.duckdb")
    app.state.model = joblib.load('src/models/sales_pred_model.joblib')
    app.state.gem_model = get_gem_model()
    app.state.hug_model = get_hug_model()
    yield
    del app.state.model # Clean up after
    app.state.db.close()

app = FastAPI(lifespan=lifespan)
app.include_router(input.router)

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5500"], 
                   allow_methods=["*"], allow_headers=["*"])
