from fastapi import FastAPI

app = FastAPI(title="OpenChemIE API")

@app.get("/")
def read_root():
    return {"message": "Welcome to OpenChemIE API"}

# 后续将在此处添加更多路由 
