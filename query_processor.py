
import requests
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
            "understand_first": "Réponds uniquement en français. Avant de répondre, assure-toi d’avoir bien compris le sens de la question. Utilise uniquement le contexte fourni pour formuler une réponse claire et pertinente.",
            "greeting": "Réponds uniquement en français par un message de bienvenue poli et chaleureux. Exemple : Bonjour ! Comment puis-je vous aider aujourd’hui ?"
        }

        self.chat_history = []  
    def is_greeting(self, query):
        greetings = ["bonjour", "salut", "bonsoir", "hello", "coucou"]
        return any(query.lower().startswith(word) for word in greetings)
    def generate_query_embedding(self, query):
        return self.embedding_model.encode(query).tolist()

    def search_qdrant(self, query_embedding, top_k=3):
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        return results

    def stream_response(self, user_query, prompt_key="standard"):
        # 👋 Si le message commence par "bonjour", on répond immédiatement
        if user_query.strip().lower().startswith("bonjour"):
            yield "Bonjour ! Comment puis-je vous aider aujourd’hui ? 😊"
            return

        query_embedding = self.generate_query_embedding(user_query)
        search_results = self.search_qdrant(query_embedding)

        relevant_texts = []
        for hit in search_results:
            if hit.score >= self.score_threshold:
                relevant_texts.append(hit.payload['texte_nettoye'])

        if not relevant_texts:
            yield "Désolé, je n'ai pas trouvé d'informations pertinentes pour votre question."
            return

        context = "\n---\n".join(relevant_texts)
        prompt_instruction = self.prompts_presets.get(prompt_key, prompt_key)
        prompt = (
            f"{prompt_instruction}\n\n"
            f"Contexte : {context}\n\n"
            f"Question : {user_query}\n\nRéponse :"
        )

        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.mistral_model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant expert qui répond de manière claire et concise."},
                {"role": "user", "content": prompt}
            ],
            "stream": True
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, stream=True)
            for line in response.iter_lines():
                if line and line.startswith(b"data: "):
                    chunk = line.decode("utf-8").replace("data: ", "")
                    if chunk.strip() == "[DONE]":
                        break
                    yield chunk + "\n"
        except Exception as e:
            yield f"[ERREUR STREAMING MISTRAL] {str(e)}\n"
    def call_mistral_api_with_messages(self, messages):  # ✅ AJOUT ICI
        url = "https://api.mistral.ai/v1/chat/completions"
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
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"[Erreur Mistral API] {response.status_code} - {response.text}"
        except Exception as e:
            return f"[Exception Mistral API] {str(e)}" 
    def process_query(self, user_query):
        print(f"[DEBUG] Requête utilisateur : {user_query}")

    # Générer l'embedding
        query_embedding = self.generate_query_embedding(user_query)
        print(f"[DEBUG] Embedding généré (5 premiers) : {query_embedding[:5]}")

        # Rechercher les textes pertinents dans Qdrant
        search_results = self.search_qdrant(query_embedding)

        relevant_texts = []
        for hit in search_results:
            print(f"[DEBUG] → score = {hit.score}")
            if hit.score >= self.score_threshold:
                texte = hit.payload.get('texte_nettoye', '')
                if texte:
                    relevant_texts.append(texte)

        # Si rien de pertinent n’est trouvé
        if not relevant_texts:
            print("[DEBUG] Aucun contexte pertinent trouvé dans Qdrant.")
            return "Désolé, je n'ai pas trouvé d'informations pertinentes pour votre question."

        # Contexte récupéré
        context = " ".join(relevant_texts)

        # Construction des messages pour le modèle Mistral
        messages = [{"role": "system", "content": "Tu es un assistant expert qui répond de manière claire, concise et utile."}]

        # Ajoute l’historique (Q&A précédentes)
        for msg in self.chat_history:
            messages.append({"role": "user", "content": msg["user"]})
            messages.append({"role": "assistant", "content": msg["assistant"]})

        # Ajoute la nouvelle question avec le contexte trouvé
        messages.append({"role": "user", "content": f"(Contexte : {context})\n\n{user_query}"})

        # DEBUG
        print(f"[DEBUG] Prompt envoyé à Mistral (dernier message) : {messages[-1]['content'][:300]}...")

        # Appel à Mistral API avec tout le fil de conversation
        response = self.call_mistral_api_with_messages(messages)

        # Ajout dans l’historique pour les futures requêtes
        self.chat_history.append({
            "user": user_query,
            "assistant": response
        })

        return response
