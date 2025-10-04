from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.ingestion import router as ingestion_router
from api.routes.query import router as query_router
from api.routes.schema import router as schema_router

app = FastAPI(title="Employee NLP Query Engine", version="0.1.0")

# Allow local dev origins by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(schema_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "NLP Employee Query Engine running", "version": app.version}
