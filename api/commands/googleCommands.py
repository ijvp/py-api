import click
import os
from extentions.database import mongo
from flask import Blueprint, Flask
from pymongo import MongoClient

googleCommands = Blueprint('user', __name__)

@googleCommands.cli.command("getUser")
@click.argument("name")
def get_google(name):
    userCollection = mongo.db.users
    user = [u for u in userCollection.find({"username": name})]
    print(user) 

def register_commands(app: Flask):
    app.cli.add_command(googleCommands.cli)
