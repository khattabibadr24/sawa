from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from data_preparation import DataPreparation
from query_processor import QueryProcessor

app = FastAPI()

data_preparer = DataPreparation()
query_processor = QueryProcessor()

class QueryRequest(BaseModel):
    query: str

@app.on_event("startup")
async def load_data_on_startup():
    try:
        json_path = "/home/khattabi/Desktop/test/data/data.json"
        data_preparer.prepare_and_insert_data(json_path)
        print("[INFO] Données chargées et insérées avec succès.")
    except Exception as e:
        print(f"[ERREUR] Échec du chargement des données : {e}")

@app.post("/process_query/", response_class=StreamingResponse)
async def process_query(request: QueryRequest):
    try:
        print("[DEBUG] Requête reçue :", request.query)
        return StreamingResponse(
            query_processor.stream_response(request.query),
            media_type="text/plain"
        )
    except Exception as e:
        print("[ERREUR] Exception attrapée :", e)
        raise HTTPException(status_code=500, detail=str(e))