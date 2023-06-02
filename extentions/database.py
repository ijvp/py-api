# from flask_pymongo import PyMongo
# from pymongo.errors import ConnectionFailure
# import certifi

# mongo = PyMongo()

# def init_app(app):
#     app.config["MONGO_TLS_CA_FILE"] = certifi.where()
#     mongo.init_app(app)

from flask import Flask
from extentions.database import mongo

app = Flask(__name__)
mongo.init_app(app)
