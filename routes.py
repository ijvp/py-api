import json
import google_auth_oauthlib.flow
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from bson import ObjectId, json_util
from flask import (Blueprint, request, url_for, jsonify)
import google.oauth2.credentials
from google.oauth2.credentials import Credentials
from google.protobuf import json_format
from extentions.database import mongo
from datetime import datetime
from pymongo import MongoClient
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import base64

load_dotenv()

routes = Blueprint("routes", __name__)

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="credentials.json"

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/adwords']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'

# g=Fernet.generate_key()
# print(g)

fernetKey = os.environ.get('FERNET_KEY')
fernet = Fernet(fernetKey)

@routes.route('/', methods=['GET'])
def index():
  return 'ok'

@routes.route('/google/authorize', methods=['GET'])
def google_authorize():
  state = request.args.get('state')

  flow = get_flow()

  authorization_url, state = flow.authorization_url(
    access_type='offline',
    approval_prompt="force",
    include_granted_scopes='true',
    state=state)

  return authorization_url

@routes.route('/google/callback', methods=['GET'])
def google_callback():
  state = request.args.get('state')
  id = '63e270c63fa2c1463717b406'

  flow = get_flow()

  authorization_response = request.url
  authorization_response = authorization_response.replace('http', 'https')

  flow.fetch_token(authorization_response=authorization_response)

  response = credentials_to_dict(flow.credentials)

  user = (u for u in mongo.db.users.find({"_id": ObjectId(id)}))
  
  user_json = json.loads(json_util.dumps(user))

  if len(user_json) == 0:
    return ({'error': 'User not found!'}), 404

  shop_index = None

  for i, shop in enumerate(user_json[0]['shops']):
    if shop['name'] == state:
      shop_index = i
      break

  if shop_index is not None:
    result = mongo.db.users.update_one(
      {'_id': ObjectId(id), 'shops.name': state},
      {'$set': {
          'shops.$.google_access_token': encrypt_token(response['token']), 
          'shops.$.google_refresh_token': encrypt_token(response['refresh_token'])
        }
      }
    )

    if result.raw_result['nModified'] == 0:
      return ({'error': 'Shop cannot be updated!'}), 400

    return ({'message': 'Shop updated!'}), 200
    
  return ({'error': 'shop not found!'}), 404

@routes.route('/google/accounts', methods=['get'])
def google_accounts():
  id = '63e270c63fa2c1463717b406'
  shop = request.args.get('shop')

  if not id or not shop:
    return ({'error': 'Missing required parameters.'}), 400

  user = (u for u in mongo.db.users.find({"_id": ObjectId(id)}))

  if not user:
    return ({'error': 'User not found.'}), 404

  user_json = json.loads(json_util.dumps(user))

  if len(user_json) == 0:
    return ({'error': 'User not found!'}), 404
  
  user_json = user_json[0]

  refreshToken = get_token(reqShops = user_json['shops'], shopName = shop, type = 'refresh')
  accessToken = get_token(reqShops = user_json['shops'], shopName = shop, type = 'access')

  print({'refreshToken': refreshToken, 'accessToken': accessToken})

  credentials = google.oauth2.credentials.Credentials(
    accessToken,
    refresh_token=refreshToken,
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
  )

  client = get_google_ads_client(
    credentials=credentials,
    developer_token=os.environ.get('GOOGLE_MANAGE_TOKEN')
  )

  try:
    customer_service = client.get_service(name='CustomerService', version='v12')
    response = customer_service.list_accessible_customers()
  except Exception as e:
    return({'error': str(e)}), 500

  customers = []

  for resource_name in response.resource_names:

    userId = resource_name.split('/')[-1]

    ga_service = client.get_service(name="GoogleAdsService")

    query = """
      SELECT
        customer.id,
        customer.resource_name,
        customer.descriptive_name
      FROM customer
    """
    
    req = client.get_type("SearchGoogleAdsRequest")
    req.customer_id = userId
    req.query = query
    resp = None

    try:
      resp = ga_service.search(request=req)
    except GoogleAdsException as e:
      print('error:', str(e))
      continue

    if resp:
      for row in resp:
        json_str = json_format.MessageToJson(row)
        customer = json.loads(json_str)
        customers.append(customer)

  return customers, 200

@routes.route('/google/account/connect', methods=['POST'])
def google_account_connect():
  data = json.loads(request.get_data())
  id = '63e270c63fa2c1463717b406'

  user = (u for u in mongo.db.users.find({"_id": ObjectId(id)}))

  user_json = json.loads(json_util.dumps(user))

  if len(user_json) == 0:
    return ({'error': 'User not found!'}), 404

  #print({'client': data['client'], 'store': data['store']})

  return user_json

def credentials_to_dict(credentials):
  return {'token': credentials.token,
    'refresh_token': credentials.refresh_token}

def get_token(reqShops, shopName, type="access"):
   
  selected_token = f"google_{type}_token"

  shopFound = None

  for shop in reqShops:
    if shop['name'] == shopName:
      shopFound = shop

  token = shopFound[selected_token]
  token = base64.b64decode(token['$binary']['base64'])
  token = fernet.decrypt(token)

  return token

def get_google_ads_client(credentials, developer_token):
  return GoogleAdsClient(credentials=credentials, developer_token=developer_token)

# def get_flow():
#   flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
#     CLIENT_SECRETS_FILE, scopes=SCOPES)
#   flow.redirect_uri = url_for('routes.google_callback', _external=True)

#   return flow

def get_flow():

  credentialsObj = {
    "installed": {
      "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
      "project_id": "turbo-dashboard",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
      "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
      "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URL"),
      "use_proto_plus": "True"
    }
  }

  flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config=credentialsObj,scopes=SCOPES)
  flow.redirect_uri = url_for('routes.google_callback', _external=True)

  return flow

def encrypt_token(token):
  return fernet.encrypt(token.encode())