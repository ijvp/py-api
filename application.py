# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from app.routes.ads import google_ads_bp
from app.routes.analytics import google_analytics_bp
from extensions import database
from flask_cors import CORS
import logging
import sys

load_dotenv()

application = Flask(__name__)

CORS(application, resources={r"*": {"origins": "*"}})
# application.secret_key = os.environ.get('FLASK_SECRET_KEY')
application.secret_key = "testesail"
application.register_blueprint(google_ads_bp)
application.register_blueprint(google_analytics_bp)
application.logger.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == '__main__':
  application.run(application.run(host='127.0.0.1', port=os.environ.get('PORT'), debug=os.environ.get('DEBUG')))
