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
# application.secret_key = os.environ.get('FLASK_SECRET_KEY')
application.secret_key = "testesail"
application.register_blueprint(routes)
application.logger.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == '__main__':
  application.run(host='0.0.0.0', port=8080, debug=False, server='gunicorn')