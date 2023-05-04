# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from routes import routes
from extentions import database
from commands.googleCommands import googleCommands, register_commands

load_dotenv()

application = Flask(__name__)
application.config["MONGO_URI"] = os.environ.get('DB_CONNECT')
application.secret_key = os.environ.get('FLASK_SECRET_KEY')
application.register_blueprint(routes)
application.register_blueprint(googleCommands)

database.init_app(application)
register_commands(application)

if __name__ == '__main__':
  application.run(port=8080, debug=True)