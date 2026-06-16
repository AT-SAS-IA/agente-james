# 🤖 Agente RAG – Casa de Crédito

Agente conversacional basado en Retrieval-Augmented Generation (RAG) que permite
consultar documentación oficial en PDF de una casa de crédito (beneficios,
condiciones, tasas, vigencias), respondiendo únicamente con información verificable
y citando fuentes.

---

## 📌 Objetivo

Diseñar e implementar un agente RAG de bajo costo que permita consultar de forma
segura y trazable la documentación oficial en PDF, sin depender de plataformas
como Copilot Studio ni de licencias enterprise.

---

## 🏗️ Arquitectura

### Visión general

```

┌─────────────────────────────────────────────────────────┐
│                      USUARIO                            │
│                   (Chat / Web / API)                    │
└──────────────────────┬──────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                     │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │  /chat      │    │  /ingest     │    │  /health   │  │
│  └──────┬──────┘    └──────┬───────┘    └────────────┘  │
│         │                  │                            │
│         ▼                  ▼                            │
│  ┌─────────────┐    ┌──────────────┐                    │
│  │  Retrieval  │    │  Ingestion   │                    │
│  │  Pipeline   │    │  Pipeline    │                    │
│  └──────┬──────┘    └──────┬───────┘                    │
│         │                  │                            │
└─────────┼──────────────────┼────────────────────────────┘
│                  │
▼                  ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Qdrant     │    │ Azure OpenAI │    │    Blob      │
│ (Vector DB)  │    │  (LLM +      │    │  Storage     │
│              │    │  Embeddings)  │    │  (PDFs)      │
└──────────────┘    └──────────────┘    └──────────────┘

```

### Pipeline de ingesta (offline)

```

PDFs (Blob Storage / URLs)
│
▼
Descarga + Cache
│
▼
Extracción de texto (PyMuPDF)
│
▼
Limpieza + Normalización
│
▼
Chunking (800 chars, 150 overlap)
│
▼
Asignación de metadata
│   - tipo\_doc (beneficio / reglamento / condiciones / promo)
│   - producto (tarjeta X, préstamo Y)
│   - vigencia\_desde / vigencia\_hasta
│   - version, url\_pdf, página
│
▼
Generación de embeddings (text-embedding-3-small)
│
▼
Upsert en Qdrant (vector + payload)
│
▼
Actualización del registro de hashes (registry.json)



### Pipeline de consulta (online)


Usuario envía pregunta
│
▼
Embedding de la pregunta
│
▼
Búsqueda semántica en Qdrant
│   - Top-K (5-8 chunks)
│   - Filtros: vigencia >= hoy, producto si aplica
│
▼
Construcción del prompt (contexto + reglas + pregunta)
│
▼
Generación de respuesta (Azure OpenAI / gpt-4o-mini)
│
▼
Respuesta + fuentes citadas (PDF, página)
│
▼
Logging (pregunta, chunks, respuesta, costo)



---

## 🔄 Demo vs. Producto final

La demo es un subconjunto funcional del producto final. La arquitectura
es la misma; lo que cambia es profundidad y robustez.

| Aspecto                  | Demo ✅               | Producto final 🎯              |
|--------------------------|----------------------|-------------------------------|
| **PDFs**                 | 1-3 manuales         | ~500, ingesta automatizada    |
| **Vector DB**            | Qdrant (Docker)      | Qdrant (Docker / Cloud)       |
| **Embeddings**           | sentence-transformers (local, gratis) | Azure OpenAI text-embedding-3-small |
| **LLM**                  | Gemini (gratis) | Azure OpenAI gpt-4o-mini     |
| **Metadata**             | Básica (source, page) | Rica (producto, vigencia, tipo_doc, version) |
| **Ingesta**              | Manual (script)      | Incremental con hash + cron   |
| **Detección de cambios** | No                   | Hash MD5 por PDF              |
| **Filtros en búsqueda**  | Solo semántica       | Semántica + metadata (vigencia, producto) |
| **Prompts**              | Genérico             | Refinado para dominio crédito |
| **Logging**              | No                   | Consultas, fuentes, costos    |
| **Auth**                 | No                   | Entra ID / API Key            |
| **Frontend**             | Swagger / Postman    | Chat web                      |
| **Deployment**           | Docker local         | Azure VM + Docker Compose     |
| **Tests**                | Manual               | Automatizados                 |

### Lo que se reutiliza de la demo



✅ Estructura del proyecto (FastAPI + Qdrant + Docker)
✅ Pipeline de ingesta (extracción → chunking → embedding → store)
✅ Pipeline de consulta (embedding → search → prompt → LLM)
✅ Lógica del endpoint /chat
✅ System prompt (base)

### Lo que se agrega para producción


🔧 Metadata rica y filtros en retrieval
🔧 Ingesta incremental (hash + registry.json)
🔧 Azure OpenAI (embeddings + chat)
🔧 Logging y monitoreo
🔧 Error handling robusto
🔧 Autenticación
🔧 Frontend de chat
🔧 CI/CD


## 🛠️ Stack tecnológico (producto final)

| Capa             | Tecnología                            | Costo estimado   |
|------------------|---------------------------------------|------------------|
| Extracción PDF   | PyMuPDF                               | $0               |
| Chunking         | LangChain RecursiveCharacterTextSplitter | $0            |
| Embeddings       | Azure OpenAI `text-embedding-3-small` | ~$0.10/indexado  |
| Vector DB        | Qdrant (self-hosted, Docker)          | $0               |
| LLM Chat         | Azure OpenAI `gpt-4o-mini`            | ~$10-30/mes      |
| Backend          | FastAPI + Uvicorn                     | $0               |
| Infra            | Azure VM B2s + Docker Compose         | ~$35/mes         |
| Storage          | Azure Blob Storage                    | ~$1-3/mes        |
| Logging          | Python logging + App Insights         | ~$0-5/mes        |
| **Total**        |                                       | **~$50-75/mes**  |

---

## 📁 Estructura del proyecto

rag-credito/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   │
│   ├── api/
│   │   ├── **init**.py
│   │   ├── chat.py             # POST /chat
│   │   └── ingest.py           # POST /ingest
│   │
│   ├── core/
│   │   ├── **init**.py
│   │   ├── config.py           # Variables de entorno
│   │   ├── embeddings.py       # Cliente de embeddings
│   │   ├── llm.py              # Cliente Azure OpenAI
│   │   └── prompts.py          # System prompt + reglas
│   │
│   ├── ingestion/
│   │   ├── **init**.py
│   │   ├── pdf\_loader.py       # Descarga + extracción
│   │   ├── cleaner.py          # Limpieza de texto
│   │   ├── chunker.py          # Chunking
│   │   ├── metadata.py         # Asignación de metadata
│   │   └── registry.py         # Control de hashes
│   │
│   ├── retrieval/
│   │   ├── **init**.py
│   │   ├── vector\_store.py     # Cliente Qdrant
│   │   └── search.py           # Búsqueda + filtros
│   │
│   └── utils/
│       ├── **init**.py
│       └── logger.py
│
├── data/
│   ├── pdfs/
│   └── registry.json
│
└── tests/
├── test\_ingestion.py
├── test\_retrieval.py
└── test\_chat.py

---

## 📋 Etapas del proyecto

1. **Ingesta de PDFs y preprocesamiento**
   - Extracción, limpieza, chunking

2. **Modelado de metadata**
   - Atributos por chunk (producto, vigencia, tipo_doc)

3. **Base de datos vectorial y búsqueda indexada**
   - Embeddings, indexación, búsqueda semántica + filtros

4. **Implementación del agente RAG**
   - Integración retrieval + LLM, reglas de respuesta, prompts

5. **Ajustes finales del modelo**
   - Refinamiento de respuestas, tono, manejo de errores

6. **Testeo del agente**
   - Consultas reales, casos borde, evaluación de precisión

7. **Documentación, logs y monitoreo**
   - Registro de consultas, métricas, documentación técnica

---

## 🔒 Reglas del agente

1. **No inventar.** Si no hay contexto suficiente → "No cuento con
   información sobre este tema en la documentación disponible."
2. **Citar siempre.** Cada respuesta incluye documento fuente y página.
3. **Respetar vigencias.** Si el documento tiene fecha, mencionarla.
4. **Disclaimer.** "Esta información surge de la documentación disponible.
   Ante dudas, consulte canales oficiales."
5. **No opinar.** No recomendar, comparar ni emitir juicios.

---

## 🚀 Evolución futura

| Mejora                    | Cuándo              | Esfuerzo |
|---------------------------|---------------------|----------|
| LangGraph (agente iterativo) | Si se necesita más precisión | Medio |
| Auth (Entra ID)           | Exposición externa  | Bajo     |
| Analytics (qué preguntan más) | Post-lanzamiento | Bajo     |
| Migrar a Azure AI Search  | Si lo pide compliance | Bajo   |
| Frontend dedicado         | Cuando se defina UX | Variable |

---

## 📄 Licencias

- **Qdrant**: Apache 2.0
- **PyMuPDF**: GNU AGPL v3
- **sentence-transformers**: Apache 2.0
- **FastAPI**: MIT

***

Listo para subirlo al repo. ¿Querés que te lo genere como **archivo descargable**, o con esto lo copiás directo? 🚀
