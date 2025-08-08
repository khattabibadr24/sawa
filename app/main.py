from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.data_preparation import DataPreparation
from app.query_processor import QueryProcessor

app = FastAPI()

data_preparer = DataPreparation()
query_processor = QueryProcessor()

class QueryRequest(BaseModel):
    query: str

@app.on_event("startup")
async def load_data_on_startup():
    try:
        json_path = "/home/khattabi/Desktop/sawa/app/data/data.json"
        data_preparer.prepare_and_insert_data(json_path)
        print("[INFO] Données chargées et insérées avec succès.")
    except Exception as e:
        print(f"[ERREUR] Échec du chargement des données : {e}")

@app.post("/process_query/")
async def process_query(request: QueryRequest):
    try:
        print("[DEBUG] Requête reçue :", request.query)
        response_text = query_processor.get_response(request.query)
        return JSONResponse(content={"response": response_text})
    except Exception as e:
        print("[ERREUR] Exception attrapée :", e)
        raise HTTPException(status_code=500, detail=str(e))
