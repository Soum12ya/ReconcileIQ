from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class CaseState(Base):
    __tablename__ = "case_state"

    case_id = Column(String, primary_key=True)
    invoice_id = Column(String, nullable=False)
    vendor = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    route = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    po_total = Column(Float, nullable=True) 
    status = Column(String, nullable=False, default="received")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    sku = Column(String, nullable=True)
    invoiced_unit_price = Column(Float, nullable=True)
    po_unit_price = Column(Float, nullable=True)
    qty = Column(Float, nullable=True)
    corrected_total = Column(Float, nullable=True)
    vendor_query_sent_at = Column(DateTime, nullable=True)