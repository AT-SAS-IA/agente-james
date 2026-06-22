import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance

async def test():
    try:
        client = AsyncQdrantClient(path="./qdrant_db")
        print("AsyncQdrantClient initialized with local path successfully!")
        
        # Test collection creation
        await client.recreate_collection(
            collection_name="test_col",
            vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )
        print("Local collection created successfully!")
        
        # Close client
        await client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
