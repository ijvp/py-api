from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from datetime import datetime

db = SQLAlchemy()

class GoogleAccount(db.Model):
    __tablename__ = 'google_accounts'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    store_id = Column(String, nullable=False)
    google_account_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expire_date = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, access_token, refresh_token, store_id, google_account_id, expire_date):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.store_id = store_id
        self.google_account_id = google_account_id
        self.expire_date = expire_date

    def __repr__(self):
        return f"<GoogleAccount(id={self.id}, store_id='{self.store_id}')>"