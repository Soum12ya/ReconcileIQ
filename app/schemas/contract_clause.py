from sqlalchemy import Column, String, Integer
from pgvector.sqlalchemy import Vector
from app.schemas.case_state import Base

class ContractClause(Base):
    __tablename__ = "contract_clauses"
    id = Column(Integer, primary_key=True)
    vendor = Column(String, nullable=False)
    text = Column(String, nullable=False)
    embedding = Column(Vector(1536))