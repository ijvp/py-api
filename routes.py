import json
import google_auth_oauthlib.flow
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from bson import ObjectId, json_util
from flask import (Blueprint, session, request, url_for, jsonify)
import google.oauth2.credentials
from google.oauth2.credentials import Credentials
from google.protobuf import json_format
from extentions.database import mongo
from datetime import datetime
from pymongo import MongoClient
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime, timedelta
import pickle
import base64

load_dotenv()

routes = Blueprint("routes", __name__)

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/adwords']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'

# g=Fernet.generate_key()
# print(g)

fernetKey = os.environ.get('FERNET_KEY')

if fernetKey is None:
  raise ValueError("FERNET_KEY environment variable is not set.")

fernet = Fernet(fernetKey)

@routes.route('/', methods=['GET'])
def index():
  return 'ok', 200

@routes.route('/google/authorize', methods=['GET'])
def google_authorize():
  store = request.args.get('store')
  id = request.args.get('id')

  state = json.dumps({
    'store': store,
    'id': id
  })

  flow = get_flow()

  authorization_url, store = flow.authorization_url(
    access_type='offline',
    approval_prompt="force",
    include_granted_scopes='true',
    state=state
)

  return authorization_url

@routes.route('/google/callback', methods=['GET'])
def google_callback():
  state_str = request.args.get('state')
  state = json.loads(state_str)

  print('state', state)

  print({'state': state['store'], 'id': state['id']})

  flow = get_flow()

  print('flow', flow)

  if os.environ.get('ENV') == 'development':
    authorization_response = request.url.replace('http', 'https')
  else:
    authorization_response = request.url

    print('authorization_response', authorization_response)

  flow.fetch_token(authorization_response=authorization_response)

  response = credentials_to_dict(flow.credentials)

  print('response', response)

  try:
    user = (u for u in mongo.db.users.find({"_id": ObjectId(state['id'])}))
  except Exception as e:
    return({'error': str(e)}), 500
  
  print('user', user)
  
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
      {'_id': ObjectId(id), 'shops.name': state['store']},
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
  id = session.get('id')
  shop = request.args.get('shop')

  if not id or not shop:
    return ({'error': 'Missing required parameters.'}), 400

  print(id)

  try:
    user = (u for u in mongo.db.users.find({"_id": ObjectId(id)}))
  except Exception as e:
    return({'error': str(e)}), 500

  if not user:
    return ({'error': 'User not found.'}), 404

  user_json = json.loads(json_util.dumps(user))

  if len(user_json) == 0:
    return ({'error': 'User not found!'}), 404
  
  user_json = user_json[0]

  refreshToken = get_token(reqShops = user_json['shops'], shopName = shop, type = 'refresh')
  accessToken = get_token(reqShops = user_json['shops'], shopName = shop, type = 'access')

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
      WHERE customer.test_account != TRUE PARAMETERS include_drafts=false
    """
    
    req = client.get_type("SearchGoogleAdsRequest")
    req.customer_id = userId
    req.query = query
    resp = None

    try:
      resp = ga_service.search(request=req)
    except:
      continue
    # except GoogleAdsException as e:
    #   print('error:', str(e))
    #   continue

    if resp:
      for row in resp:
        json_str = json_format.MessageToJson(row)
        customer = json.loads(json_str)
        customers.append(customer)

  return customers, 200

@routes.route('/google/account/connect', methods=['POST'])
def google_account_connect():
  id = request.args.get('id')
  data = json.loads(request.get_data())

  user = json.loads(json_util.dumps((u for u in mongo.db.users.find({"_id": ObjectId(id)}))))[0]

  shopExists = None

  for shop in user['shops']:
    if shop['name'] == data['store']:
      shopExists = shop

  if shopExists is None:
    return ({'error': 'Shop not found.'}), 404
  
  client = data['client']

  result = mongo.db.users.update_one(
    {'_id': ObjectId(id), 'shops.name': data['store']},
    {'$set': {
        'shops.$.google_client.id': client['id'], 
        'shops.$.google_client.name': client['descriptive_name']
      }
    }
  )

  if result.modified_count <= 0:
    response = { 
      "success": False, 
      "message": "Update failed or did not modify any documents."
    }

    return json.dumps(response)
  
  response = { 
    "success": True, 
    "message": f"Google Ads account {client['descriptive_name']} added to {data['store']}"
  }

  return json.dumps(response)

@routes.route('/google/account/disconnect', methods=['GET'])
def google_account_disconnect():
  shop = request.args.get('shop')
  id = request.args.get('id')

  result = mongo.db.users.update_one(
    {'_id': ObjectId(id), 'shops.name': shop},
    {'$unset': {
        "shops.$.google_client": 1,
        "shops.$.google_access_token": 1,
        "shops.$.google_refresh_token": 1
      }
    }
  )

  if result.modified_count <= 0:
    response = { 
      "success": False, 
      "message": "Update failed or did not modify any documents."
    }

    return json.dumps(response)
  
  response = { 
    "success": True, 
    "message": f"Removed Google Ads account from ${shop}"
  }

  return json.dumps(response)

@routes.route('/google/ads', methods=['post'])
def google_ads():
  start = request.args.get('start')
  end = request.args.get('end')
  shop = request.args.get('store')
  id = request.args.get('id')
  access_token = request.args.get('access_token')
  refresh_token = request.args.get('refresh_token')

  print(start, end, shop, id)

  if not shop:
    return ({'error': 'Missing store!'}), 400
  
  if not start or not end: 
    return ({'error': 'Start date and end date must be set!'}), 400
  
  start_date = datetime.strptime(start, "%Y-%m-%d")
  end_date = datetime.strptime(end, "%Y-%m-%d")

  if start_date > end_date:
    return ({'error': 'Start date cannot occur after the end date!'}), 400
  
  user = (u for u in mongo.db.users.find({"_id": ObjectId(id)}))

  if not user:
    return ({'error': 'User not found!'}), 404

  
  user_json = json.loads(json_util.dumps(user))

  if len(user_json) == 0:
    return ({'error': 'User not found!'}), 404
  
  user_json = user_json[0]

  shopFound = next((obj for obj in user_json['shops'] if obj["name"] == shop), None)

  if(shopFound == None):
    return ({'error': 'Store not found'}), 404
  
  # if not shopFound['google_client']:
  #   return ({'error': 'No client associated with this store'}), 404
  
  # credentials = google.oauth2.credentials.Credentials(
  #   get_token(reqShops = user_json['shops'], shopName = shop, type = 'access'),
  #   refresh_token=get_token(reqShops = user_json['shops'], shopName = shop, type = 'refresh'),
  #   token_uri='https://oauth2.googleapis.com/token',
  #   client_id=os.environ.get('GOOGLE_CLIENT_ID'),
  #   client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
  # )

  credentials = google.oauth2.credentials.Credentials(
    access_token,
    refresh_token=refresh_token,
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
  )

  client = get_google_ads_client(
    credentials=credentials,
    developer_token=os.environ.get('GOOGLE_MANAGE_TOKEN')
  )

  difference = end_date - start_date

  if difference < timedelta(days=1):
    is_single_day = True
  else:
    is_single_day = False

  query = f"""
    SELECT
      metrics.cost_micros,
      {"segments.hour" if is_single_day == True else "segments.date"}
    FROM
      campaign
    WHERE
      segments.date >= '{start_date.strftime('%Y%m%d')}' AND
      segments.date <= '{end_date.strftime('%Y%m%d')}'
  """
  
  ga_service = client.get_service(name="GoogleAdsService")
  
  req = client.get_type("SearchGoogleAdsRequest")
  req.customer_id = shopFound['google_client']['id']
  req.query = query
  
  try:
    response = ga_service.search(request=req)
    
    metrics = {
      "id": "google-ads.ads-metrics",
      "metricsBreakdown": []
    }

    for row in response:
      json_str = json_format.MessageToJson(row)
      campaign = json.loads(json_str)
      dateKey = None

      if is_single_day:
        dateKey = "0" + str(campaign["segments"]["hour"]) if campaign["segments"]["hour"] < 10 else str(campaign["segments"]["hour"])
        datetime_obj = datetime.strptime(str(start_date), '%Y-%m-%d %H:%M:%S')
        date_only = datetime_obj.date()
        dateKey = str(date_only) + "T" + dateKey
      else:
        dateKey = campaign["segments"]["date"]

      dateExists = next((obj for obj in metrics["metricsBreakdown"] if obj["date"] == dateKey), None)

      if (dateExists):
        dateExists["metrics"]["spend"] += int(campaign["metrics"]["costMicros"]) / 1000000
        
      else:
        dataPoint = {
          "date": dateKey,
          "metrics": {
            "spend": int(campaign["metrics"]["costMicros"]) / 1000000
          }
        }

        metrics["metricsBreakdown"].append(dataPoint)
      
    return metrics, 200
  
  except:
    return "Something went wrong", 500

def credentials_to_dict(credentials):
  return {
    'token': credentials.token,
    'refresh_token': credentials.refresh_token
  }

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

def is_valid_object_id(id_str):
    try:
        ObjectId(id_str)
        return True
    except (ValueError):
        return False