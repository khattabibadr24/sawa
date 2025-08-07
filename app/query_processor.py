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
        """Détecte si la requête est une salutation"""
        greetings = ["bonjour", "salut", "bonsoir", "hello", "coucou", "hi", "hey"]
        query_lower = query.strip().lower()
        return any(query_lower.startswith(word) for word in greetings)

    def generate_query_embedding(self, query):
        """Génère l'embedding pour une requête"""
        return self.embedding_model.encode(query).tolist()

    def search_qdrant(self, query_embedding, top_k=3):
        """Recherche dans Qdrant avec l'embedding"""
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        return results

    def build_messages_with_history(self, user_query, context=None):
        """Construit les messages pour l'API Mistral en incluant l'historique"""
        messages = [{"role": "system", "content": "Tu es un assistant expert qui répond de manière claire, concise et utile."}]
        
        # Ajouter l'historique des conversations précédentes
        for msg in self.chat_history:
            messages.append({"role": "user", "content": msg["user"]})
            messages.append({"role": "assistant", "content": msg["assistant"]})
        
        # Ajouter la nouvelle question avec le contexte si disponible
        if context:
            user_content = f"(Contexte : {context})\n\n{user_query}"
        else:
            user_content = user_query
            
        messages.append({"role": "user", "content": user_content})
        
        return messages

    def stream_response(self, user_query, prompt_key="standard"):
        """
        Méthode principale pour traiter une requête avec streaming.
        Gère les salutations, la recherche Qdrant, et la continuité de conversation.
        """
        print(f"[DEBUG] Requête utilisateur : {user_query}")
        
        # 1. Gérer les salutations
        if self.is_greeting(user_query):
            polite_response = self.prompts_presets.get("greeting", "Bonjour ! Comment puis-je vous aider aujourd'hui ? 😊")
            
            # Stream la réponse caractère par caractère pour simuler le streaming
            for char in polite_response:
                yield char
            
            # Mettre à jour l'historique pour la salutation
            self.chat_history.append({
                "user": user_query,
                "assistant": polite_response
            })
            return

        # 2. Recherche dans Qdrant pour les requêtes non-salutations
        query_embedding = self.generate_query_embedding(user_query)
        print(f"[DEBUG] Embedding généré (5 premiers) : {query_embedding[:5]}")
        
        search_results = self.search_qdrant(query_embedding)
        
        relevant_texts = []
        for hit in search_results:
            print(f"[DEBUG] → score = {hit.score}")
            if hit.score >= self.score_threshold:
                texte = hit.payload.get('texte_nettoye', '')
                if texte:
                    relevant_texts.append(texte)

        # 3. Si aucun contexte pertinent n'est trouvé
        if not relevant_texts:
            print("[DEBUG] Aucun contexte pertinent trouvé dans Qdrant.")
            no_context_response = "Désolé, je n'ai pas trouvé d'informations pertinentes pour votre question."
            
            for char in no_context_response:
                yield char
                
            # Mettre à jour l'historique
            self.chat_history.append({
                "user": user_query,
                "assistant": no_context_response
            })
            return

        # 4. Construire le contexte et les messages avec historique
        context = "\\n---\\n".join(relevant_texts)
        messages = self.build_messages_with_history(user_query, context)
        
        print(f"[DEBUG] Messages envoyés à Mistral (nombre de messages) : {len(messages)}")
        print(f"[DEBUG] Dernier message : {messages[-1]['content'][:300]}...")

        # 5. Appel streaming à l'API Mistral
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.mistral_model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7
        }

        full_response = ""  # Pour stocker la réponse complète
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line and line.startswith(b"data: "):
                    chunk_data = line.decode("utf-8").replace("data: ", "")
                    
                    if chunk_data.strip() == "[DONE]":
                        break
                    
                    try:
                        # Parser le JSON du chunk
                        chunk_json = json.loads(chunk_data)
                        if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                            delta = chunk_json["choices"][0].get("delta", {})
                            if "content" in delta:
                                content = delta["content"]
                                full_response += content
                                yield content
                    except json.JSONDecodeError:
                        # Ignorer les chunks malformés
                        continue
                        
        except Exception as e:
            error_msg = f"[ERREUR STREAMING MISTRAL] {str(e)}"
            print(f"[DEBUG] {error_msg}")
            yield error_msg
            full_response = error_msg

        # 6. Mettre à jour l'historique avec la réponse complète
        if full_response:
            self.chat_history.append({
                "user": user_query,
                "assistant": full_response
            })

    def call_mistral_api_with_messages(self, messages):
        """Appel non-streaming à l'API Mistral (conservé pour compatibilité)"""
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

    def process_query(self, user_query):
        """
        Méthode héritée pour compatibilité - utilise maintenant stream_response
        et retourne la réponse complète au lieu de streamer
        """
        print(f"[DEBUG] process_query appelé - redirection vers stream_response")
        
        # Collecter toute la réponse streamée
        full_response = ""
        for chunk in self.stream_response(user_query):
            full_response += chunk
            
        return full_response

    def get_chat_history(self):
        """Retourne l'historique des conversations"""
        return self.chat_history

    def clear_chat_history(self):
        """Efface l'historique des conversations"""
        self.chat_history = []

    def set_chat_history(self, history):
        """Définit l'historique des conversations"""
        self.chat_history = history
