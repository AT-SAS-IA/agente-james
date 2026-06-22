# 🤖 Blueprint RAG – Agente Genérico de Consulta de Documentación

Este documento describe la arquitectura de referencia, buenas prácticas y hoja de ruta para la implementación de un agente conversacional basado en **Retrieval-Augmented Generation (RAG)** de nivel empresarial. Permite consultar de forma interactiva documentación oficial en PDF (especificaciones, reglamentos, catálogos, manuales o preguntas frecuentes), respondiendo únicamente con información verificable y citando fuentes y páginas.

---

## 📌 Objetivo

Diseñar e implementar un agente RAG seguro, eficiente y de bajo costo operativo que permita consultar de forma trazable y segura la documentación corporativa, sin depender de plataformas propietarias rígidas y garantizando cero alucinaciones.

---

## 🏗️ Arquitectura de Referencia

### Visión General

```
┌─────────────────────────────────────────────────────────┐
│                      USUARIO                            │
│               (Chat Web / App / API)                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼ HTTPS (Encriptado)
┌─────────────────────────────────────────────────────────┐
│               API GATEWAY / PROXY REVERSO               │
│        (Rate Limiting & Filtro Anti-Jailbreak)          │
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
          │   Qdrant     │    │ Azure OpenAI │    │  Almacén de  │
          │ (Vector DB)  │    │ (LLM & Embed)│    │ Documentos   │
          └──────────────┘    └──────────────┘    └──────────────┘
```

### Pipeline de Ingesta (Offline)

```
Documentos PDF (Repositorio Local / Cloud Storage)
│
▼
Extracción de Texto (PyMuPDF con procesamiento visual/layout-aware para doble columna)
│
▼
Limpieza + Normalización de caracteres
│
▼
Chunking Inteligente (ej: 500-800 caracteres con 100-150 de overlap)
│
▼
Asignación de Metadata Enriquecida
│   - tipo_doc (especificación / reglamento / beneficio / faq)
│   - categoría_producto (modelo, línea, segmento)
│   - vigencia_desde / vigencia_hasta (si aplica)
│   - versión, url_origen, página_fisica
│
▼
Generación de Embeddings (Azure OpenAI text-embedding-3-small o local)
│
▼
Upsert en Base de Datos Vectorial (Vectores + Payload de metadata)
│
▼
Actualización de registro de hashes para indexación incremental (registry.json)
```

### Pipeline de Consulta (Online)

```
Usuario envía pregunta
│
▼
Control de Rate Limiting (Heurística de IPs y cabeceras X-Forwarded-For)
│
▼
Filtro de Seguridad Local (Heurísticas contra Inyección de Prompts / Jailbreaks)
│
▼
Reescritura de Query (Query Expansion / Búsqueda por Categorías)
│
▼
Generación del Embedding de la consulta
│
▼
Búsqueda Semántica Híbrida en Base Vectorial (Similitud del vector + Filtros de Payload)
│   - Filtro por categoría o producto específico
│   - Filtro por vigencia de documentos
│   - Selección de Top-K chunks relevantes (score >= umbral mínimo)
│
▼
Construcción del Prompt (Contexto estructurado + Reglas de comportamiento + Pregunta)
│
▼
Llamada al LLM (Azure OpenAI gpt-4o-mini o superior con temperatura baja: 0.0 - 0.2)
│
▼
Post-procesamiento de la respuesta (Remoción de citas crudas, formateo de texto plano)
│
▼
Respuesta final + Fuentes estructuradas entregadas al usuario
│
▼
Logging y Auditoría (Pregunta, chunks recuperados, respuesta final, tokens consumidos, costo)
```

---

## 🔄 Demo vs. Producto Final (Entorno Corporativo)

| Aspecto | Demo / Piloto ✅ | Producto Final (Producción) 🎯 |
| :--- | :--- | :--- |
| **Documentos PDF** | 1-5 subidos de forma manual | Escala masiva con ingesta y syncing automatizado |
| **Vector DB** | Qdrant en-proceso (SQLite local / embebido) | Qdrant en la nube (Docker dedicado / Qdrant Cloud) |
| **Embeddings** | Locales en CPU (`sentence-transformers` gratis) | Azure OpenAI (`text-embedding-3-small` / `large`) |
| **Modelos de Chat (LLM)** | Azure OpenAI (`gpt-4o-mini` / `gpt-4o`) | Azure OpenAI (`gpt-4o-mini` / `gpt-4o` con despliegues dedicados) |
| **Seguridad de Entrada** | Regex básico local anti-jailbreak | Filtros avanzados AI (LlamaGuard) + Rate Limits en API Gateway |
| **Rate Limiting** | En memoria del contenedor backend | Redis distribuido o políticas nativas en Azure APIM |
| **Metadata** | Básica (fuente, página) | Rica (producto, categoría, vigencia, versión) |
| **Ingesta** | Manual ejecutando scripts en host | Incremental con hashes MD5 + Jobs de sincronización cron |
| **Detección de cambios** | No (recreación completa) | Comparación de hash MD5 por archivo |
| **Filtros en búsqueda** | Solo similitud semántica | Búsqueda híbrida (Semántica + Filtros de Payload específicos) |
| **Logging y Auditoría** | Consola local | Logging estructurado y observabilidad (OpenTelemetry / App Insights) |
| **Deployment** | Contenedor local / Servidor standalone | Orquestadores como Azure Container Apps / Kubernetes (AKS) |

---

## 🛠️ Stack Tecnológico de Referencia

| Capa | Tecnología Recomendada | Razón de elección |
| :--- | :--- | :--- |
| **Extracción PDF** | PyMuPDF | Rápido, ligero y con soporte para coordenadas y lectura de bloques nativa. |
| **Chunking** | LangChain TextSplitters | Permite división recursiva por oraciones manteniendo semántica intacta. |
| **Embeddings** | Azure OpenAI `text-embedding-3-small` | Alta dimensionalidad y bajo costo transaccional. |
| **Vector DB** | Qdrant | Excelente rendimiento en filtros híbridos y opción en-proceso para bajo costo. |
| **LLM Chat** | Azure OpenAI `gpt-4o-mini` | La mejor relación calidad-precio y velocidad para generación de respuestas RAG. |
| **Backend API** | FastAPI + Uvicorn | Asíncrono, de alto rendimiento y documentación automática (OpenAPI). |
| **Pipeline de CI/CD** | GitHub Actions | Automatización de builds, pruebas unitarias y análisis estático de seguridad (SAST). |
| **Seguridad SAST** | Bandit + Trivy | Herramientas open-source líderes para escanear vulnerabilidades en código y empaquetado. |

---

## 📁 Estructura del Proyecto Recomendada

```
rag-proyecto/
│
├── .github/workflows/
│   └── sast.yml                 # Integración continua (Scans automáticos)
│
├── .dockerignore                # Exclusiones del build de Docker
├── Dockerfile                   # Build de producción
├── docker-compose.yml           # Orquestación local de desarrollo
├── requirements.txt             # Dependencias del backend
├── main.py                      # Punto de entrada de la API
│
├── app/
│   ├── api/
│   │   ├── chat.py              # Endpoint principal de consulta (/chat)
│   │   └── ingest.py            # Endpoint para administración de ingesta (/ingest)
│   │
│   ├── core/
│   │   ├── config.py            # Gestión de variables de entorno y secrets
│   │   ├── security.py          # Validaciones anti-jailbreak y sanitización
│   │   └── prompts.py           # Estructura del prompt y reglas de negocio
│   │
│   ├── ingestion/
│   │   ├── parser.py            # Extracción y estructuración de PDF
│   │   ├── chunker.py           # Estrategias de chunking
│   │   └── registry.py          # Comparación de hashes para ingesta incremental
│   │
│   └── retrieval/
│       ├── vector_store.py      # Cliente de conexión a la Base de Datos Vectorial
│       └── search.py            # Búsqueda semántica y lógica de filtros
│
├── data/
│   ├── source_pdfs/             # Archivos PDF originales
│   └── registry.json            # Tabla de hashes e historial de indexación
│
└── tests/
    ├── test_ingestion.py        # Cobertura de tests de extracción
    └── test_chat.py             # Pruebas automatizadas de conversación RAG
```

---

## 🔒 Reglas Invariables del Agente Conversacional

1. **No inventar (Factualidad):** Si la información recuperada del contexto es insuficiente, responder con una plantilla neutra: *"No cuento con información sobre este tema en la documentación disponible."*
2. **Citar siempre (Trazabilidad):** Cada fragmento de información proporcionado en la respuesta debe ir acompañado de su fuente formal (nombre de documento y página física).
3. **Respetar vigencias:** Si la información recuperada tiene condiciones temporales explícitas en su metadata, el agente debe advertir al usuario sobre su período de validez.
4. **Mantener neutralidad profesional:** El agente no debe dar opiniones personales, consejos comerciales subjetivos ni hacer juicios de valor. Se limita a reportar objetivamente lo que indica la documentación.
5. **Alineación con el Dominio:** Rechazar amablemente cualquier consulta fuera de tema y redirigir la conversación de manera fluida y educada hacia la documentación oficial del proyecto.
