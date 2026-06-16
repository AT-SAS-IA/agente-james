import os
import asyncio
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

load_dotenv()

# Config
QDRANT_HOST = "localhost"  # En el contenedor es "qdrant", pero desde fuera o en red local
QDRANT_PORT = 6333
COLLECTION = "james-demo"

endpoint = os.getenv("ENDPOINT")
deployment = os.getenv("DEPLOYMENT")
subscription_key = os.getenv("SUBSCRIPTION_KEY")
api_version = os.getenv("API_VERSION")

azure_client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key
)

async def test():
    print("Testing Azure OpenAI Connection and JSON mode...")
    
    system_prompt = (
        "Sos un experto en reescritura de consultas y clasificación para un sistema RAG de electrodomésticos JAMES Uruguay.\n"
        "Tu tarea es analizar la pregunta actual del usuario y el historial de chat para devolver un JSON con dos campos:\n"
        "1. 'category': La categoría del catálogo de JAMES a la que pertenece la consulta. Debe ser exactamente una de las siguientes:\n"
        "   - TELEVISORES LED SMART TV\n"
        "   - ACONDICIONADORES DE AIRE SPLIT\n"
        "   - DESHUMIDIFICADORES\n"
        "   - REFRIGERADORES\n"
        "   - FREEZERS\n"
        "   - LAVADO Y SECADO\n"
        "   - COCINAS\n"
        "   - ANAFES\n"
        "   - HORNOS DE EMPOTRAR\n"
        "   - CAMPANAS EXTRACTORAS\n"
        "   - PURIFICADORES DE AIRE\n"
        "   - EXTRACTORES DE AIRE PARA BAÑO\n"
        "   - HORNOS ELÉCTRICOS\n"
        "   - HORNOS MICROONDAS\n"
        "   - ASPIRADORAS\n"
        "   - PEQUEÑOS ELECTRODOMÉSTICOS\n"
        "   - ESTUFAS\n"
        "   - VENTILADORES\n"
        "   - TERMOTANQUES\n"
        "   - PLANTA DE PRODUCCIÓN\n"
        "   - NINGUNA (para showroom, horarios, service técnico o preguntas de contacto general)\n\n"
        "Regla crítica de categoría: Si la consulta del usuario es una continuación/pregunta contextual (ej: 'más chico', 'grande', 'barato', 'con freezer', 'de acero') o usa pronombres de referencia, DEBES conservar la categoría anterior del historial. NUNCA cambies de categoría a menos que el usuario mencione explícitamente otro producto o categoría de forma obvia.\n\n"
        "2. 'rewritten_query': Una consulta de búsqueda semántica optimizada en español. Si la pregunta actual es vaga o contextual (ej: 'más chico'), incorpórale el nombre de la categoría del historial para que sea una consulta de búsqueda semántica completa (ej: si venían hablando de heladeras/refrigeradores, reescribe 'más chico' a 'refrigeradores compactos pequeños').\n\n"
        "Responde ÚNICAMENTE con el objeto JSON estructurado, sin markdown, sin explicaciones ni caracteres extra. Ejemplo de salida:\n"
        "{\"category\": \"REFRIGERADORES\", \"rewritten_query\": \"refrigeradores chicos compactos\"}"
    )

    history = [
        {"role": "user", "content": "Que heladeras tenes"},
        {"role": "assistant", "content": "Tenemos varias opciones de heladeras según el espacio que tengas. 🧊 Modelos grandes tipo French Door, 🧊 Línea combi o frío seco, 🧊 Opciones más chicas."}
    ]
    
    question = "mas chico"
    
    history_str = ""
    for msg in history:
        role_label = "Usuario" if msg["role"] == "user" else "Asistente"
        history_str += f"{role_label}: {msg['content']}\n"
        
    user_prompt = f"HISTORIAL DE CONVERSACIÓN:\n{history_str}\nPREGUNTA ACTUAL:\n{question}"
    
    response = azure_client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
        max_tokens=256
    )
    
    result = json.loads(response.choices[0].message.content)
    print("JSON Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
