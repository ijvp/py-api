# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from app.routes.routes import routes
from flask_cors import CORS
import logging
import sys

load_dotenv()

application = Flask(__name__)

CORS(application, resources={r"*": {"origins": "*"}})
application.secret_key = os.environ.get('FLASK_SECRET_KEY')
application.register_blueprint(routes)
application.logger.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == '__main__':
  if os.environ.get('ENV') == 'development':
    application.run(host='0.0.0.0', port=os.environ.get('PORT'), debug=os.environ.get('DEBUG'))
  else:
    application.run(host='0.0.0.0', port=os.environ.get('PORT'), debug=os.environ.get('DEBUG'), server='gunicorn')