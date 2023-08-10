from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ShopifyAccount(Base):
    __tablename__ = 'shopify_accounts'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    access_token = Column(String)
    scope = Column(String)
    store_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now())

    def __repr__(self):
        return f"<ShopifyAccount(id={self.id}, store_id={self.store_id})>"