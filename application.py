# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from routes import routes
from extentions import database
from flask_cors import CORS

load_dotenv()

application = Flask(__name__)
CORS(application, resources={r"*": {"origins": "*"}})
application.config["MONGO_URI"] = os.environ.get('DB_CONNECT')
application.secret_key = os.environ.get('FLASK_SECRET_KEY')
application.register_blueprint(routes)

database.init_app(application)

if __name__ == '__main__':
  application.run(host=os.environ.get('HOST'), port=os.environ.get('PORT'), debug=os.environ.get('DEBUG'))