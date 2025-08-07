
import json
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

class DataPreparation:
    def __init__(self, qdrant_host='localhost', qdrant_port=6333, collection_name='my_collection'):
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    def clean_text(self, text):
        # Nettoyage du texte (prétraitement : lowercasing, suppression des caractères spéciaux, etc.)
        text = text.lower()
        text = ''.join(char for char in text if char.isalnum() or char.isspace())
        return text

    def chunk_text(self, text, chunk_size=500, overlap=50):
        # Découpage en chunks si nécessaire (selon le token limit de Mistral).
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks

    def generate_embeddings(self, texts):        
        return self.embedding_model.encode(texts).tolist()

    def prepare_and_insert_data(self, data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        cleaned_text = self.clean_text(raw_text)
        chunks = self.chunk_text(cleaned_text)
        embeddings = self.generate_embeddings(chunks)

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            points.append(
                models.PointStruct(
                    id=i,
                    vector=embedding,
                    payload={'texte_nettoye': chunk}
                )
            )
        
        # Ensure collection exists
        self.qdrant_client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=len(embeddings[0]), distance=models.Distance.COSINE),
        )

        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True
        )
        print(f"Données insérées dans Qdrant, collection: {self.collection_name}")
        print("Points insérés dans la collection :", len(points))  


if __name__ == '__main__':
    # Exemple d'utilisation
    data_preparer = DataPreparation()
    # Créez un fichier data.json dans le dossier data/ pour tester
    # Exemple de contenu pour data.json: "Ceci est un texte brut pour tester la préparation des données."
    data_preparer.prepare_and_insert_data('/home/khattabi/Desktop/test/data/data.json')
    


