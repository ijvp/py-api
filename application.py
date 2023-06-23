# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from routes import routes
from extentions import database
from flask_cors import CORS
import logging
import sys

load_dotenv()

application = Flask(__name__)

CORS(application, resources={r"*": {"origins": "*"}})
application.config["MONGO_URI"] = os.environ.get('DB_CONNECT')
application.config['MONGO_DBNAME'] = os.environ.get('DB_NAME')
application.secret_key = os.environ.get('FLASK_SECRET_KEY')
application.register_blueprint(routes)
application.logger.addHandler(logging.StreamHandler(sys.stdout))
database.init_app(application)
print('REDIS_PORT', os.environ.get('REDIS_PORT'))

if __name__ == '__main__':
  application.run(application.run(host='0.0.0.0', port=os.environ.get('PORT'), debug=os.environ.get('DEBUG')))