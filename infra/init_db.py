# infra/init_db.py
from sqlalchemy import create_engine
from app.schemas.case_state import Base   # your SQLAlchemy models
from app.schemas.purchase_order import PurchaseOrder
from app.schemas.contract_clause import ContractClause
from app.harness.db import engine
import os
from dotenv import load_dotenv
load_dotenv()

Base.metadata.create_all(engine)
print("Tables created.")