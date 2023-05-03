# -*- coding: utf-8 -*-

import os
from flask import Flask
from dotenv import load_dotenv
from routes import routes
from extentions import database
from commands.googleCommands import googleCommands, register_commands

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.environ.get('DB_CONNECT')
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.register_blueprint(routes)
app.register_blueprint(googleCommands)

database.init_app(app)
register_commands(app)

if __name__ == '__main__':
  app.run('localhost', 8080, debug=True)