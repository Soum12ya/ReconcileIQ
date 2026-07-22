from sqlalchemy import Column, String, Float
from app.schemas.case_state import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_number = Column(String, primary_key=True)
    vendor = Column(String, nullable=False)
    sku = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    qty = Column(Float, nullable=False)