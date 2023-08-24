import os

host = 'dashboard_postgres_db'
user = 'turbodash'
password = 'turbodash'
database = 'turbodash'
database_uri = f"postgresql://{user}:{password }@{host}/{database}"

class Config:
    SQLALCHEMY_DATABASE_URI = database_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')