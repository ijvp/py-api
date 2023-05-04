from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure
import certifi

mongo = PyMongo()

def init_app(app):
    mongo.init_app(app, tlsCAFile=certifi.where())