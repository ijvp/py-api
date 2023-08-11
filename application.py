# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from app.routes.ads import google_ads_bp
from app.routes.analytics import google_analytics_bp
from flask import jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from extensions.config import Config
import logging
import sys
from extensions.database.postgresql import db, init_app
from app.models.Stores import Stores
import json

load_dotenv()

application = Flask(__name__)
application.config.from_object(Config)

init_app(application)

# db = SQLAlchemy(application)

CORS(application, resources={r"*": {"origins": "*"}})
application.register_blueprint(google_ads_bp)
application.register_blueprint(google_analytics_bp)
application.logger.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == '__main__':
  if os.environ.get('ENV') == 'development':
    application.run(host=os.environ.get('HOST'), port=os.environ.get('PORT'), debug=os.environ.get('DEBUG'))
  else:
    application.run(host=os.environ.get('HOST'), port=os.environ.get('PORT'), debug=os.environ.get('DEBUG'), server='gunicorn')