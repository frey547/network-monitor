from fastapi import FastAPI
from app.metrics import get_metrics

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "monitor system running"}

@app.get("/metrics")
def metrics():
    return get_metrics()
