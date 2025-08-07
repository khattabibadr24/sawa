import requests
import json
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

class QueryProcessor:
    def __init__(self, qdrant_host='localhost', qdrant_port=6333, collection_name='my_collection', score_threshold=0.3):
        self.qdrant_client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port,
            check_compatibility=False
        )
        self.collection_name = collection_name
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.score_threshold = score_threshold
        self.mistral_api_key = "a4urlm2FhhZLdxi7nz3iYTU0E80vHg22"
        self.mistral_model = "mistral-small"
        self.api_url = "https://api.mistral.ai/v1/chat/completions"

        self.prompts_presets = {
            "standard": "Réponds uniquement en français. En utilisant uniquement le contexte ci-dessous, réponds de façon claire à la question suivante.",
            "bullet_points": "Réponds uniquement en français et uniquement avec des bullet points clairs et synthétiques.",
            "friendly": "Réponds uniquement en français. Sois chaleureux et professionnel. Utilise uniquement les informations du contexte.",
            "understand_first": "Réponds uniquement en français. Avant de répondre, assure-toi d'avoir bien compris le sens de la question. Utilise uniquement le contexte fourni pour formuler une réponse claire et pertinente.",
            "greeting": "Bonjour ! Comment puis-je vous aider aujourd'hui ? "
        }

        self.chat_history = []

    def is_greeting(self, query):
        greetings = ["bonjour", "salut", "bonsoir", "hello", "coucou", "hi", "hey"]
        return any(query.strip().lower().startswith(g) for g in greetings)

    def generate_query_embedding(self, query):
        return self.embedding_model.encode(query).tolist()

    def search_qdrant(self, query_embedding, top_k=3):
        return self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )

    def build_messages_with_history(self, user_query, context=None):
        messages = [{"role": "system", "content": "Tu es un assistant expert qui répond de manière claire, concise et utile."}]
        
        for msg in self.chat_history:
            messages.append({"role": "user", "content": msg["user"]})
            messages.append({"role": "assistant", "content": msg["assistant"]})
        
        user_content = f"(Contexte : {context})\n\n{user_query}" if context else user_query
        messages.append({"role": "user", "content": user_content})
        
        return messages

    def call_mistral_api_with_messages(self, messages):
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.mistral_model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"[Erreur Mistral API] {response.status_code} - {response.text}"
        except Exception as e:
            return f"[Exception Mistral API] {str(e)}"

    def get_response(self, user_query, prompt_key="standard") -> str:
        print(f"[DEBUG] Requête utilisateur (non-stream) : {user_query}")

        if self.is_greeting(user_query):
            response = self.prompts_presets.get("greeting", "Bonjour ! Comment puis-je vous aider ?")
            self.chat_history.append({"user": user_query, "assistant": response})
            return response

        query_embedding = self.generate_query_embedding(user_query)
        search_results = self.search_qdrant(query_embedding)

        relevant_texts = [
            hit.payload.get("texte_nettoye", "")
            for hit in search_results
            if hit.score >= self.score_threshold and hit.payload.get("texte_nettoye", "")
        ]

        if not relevant_texts:
            response = "Désolé, je n'ai pas trouvé d'informations pertinentes pour votre question."
            self.chat_history.append({"user": user_query, "assistant": response})
            return response

        context = "\n---\n".join(relevant_texts)
        messages = self.build_messages_with_history(user_query, context)
        response_text = self.call_mistral_api_with_messages(messages)

        self.chat_history.append({"user": user_query, "assistant": response_text})
        return response_text

    def get_chat_history(self):
        return self.chat_history

    def clear_chat_history(self):
        self.chat_history = []

    def set_chat_history(self, history):
        self.chat_history = history
