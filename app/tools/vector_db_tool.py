import os
from openai import OpenAI
from app.schemas.contract_clause import ContractClause

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def embed(text: str) -> list[float]:
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding

def search_contract_clauses(db, vendor: str, query: str, top_k: int = 3):
    query_vec = embed(query)
    return (
        db.query(ContractClause)
        .filter_by(vendor=vendor)
        .order_by(ContractClause.embedding.cosine_distance(query_vec))
        .limit(top_k)
        .all()
    )