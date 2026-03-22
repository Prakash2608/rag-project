from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
client.delete_collection("documents")
print("Qdrant collection deleted successfully")