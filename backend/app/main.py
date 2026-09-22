from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import samples, variants, qc, cohorts, pipelines, reports, audit, annotate

app = FastAPI(title="Genomics Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(samples.router)
app.include_router(variants.router)
app.include_router(qc.router)
app.include_router(cohorts.router)
app.include_router(pipelines.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(annotate.router)

@app.get("/health")
def health():
    return {"status": "ok"}
