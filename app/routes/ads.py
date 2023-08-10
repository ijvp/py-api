import json
import google_auth_oauthlib.flow
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from bson import ObjectId, json_util
from flask import (Blueprint, request, url_for)
import google.oauth2.credentials
from google.protobuf import json_format
from extensions.database import mongo
from datetime import datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime, timedelta
import base64
import redis
from rediscluster import RedisCluster
import requests
from application import db
from app.models.Store import Store
load_dotenv()     

redis_host = os.environ.get('REDIS_HOST')
redis_port = os.environ.get('REDIS_PORT')

startup_nodes=[{ "host": redis_host, "port": redis_port, "db": 0}]

if os.environ.get('ENV') == 'development':
  print("dev")
  r = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)
else:
  print("prod")
  r = RedisCluster(startup_nodes=startup_nodes, decode_responses=True, ssl=True, ssl_cert_reqs=None, skip_full_coverage_check=True)

if r.ping():
  print('Redis Connected')

google_ads_bp = Blueprint('ads', __name__)

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/adwords']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'

@google_ads_bp.route('/', methods=['GET'])
def index():
  storeFound = db.Query((Store).filter_by(name='dev-insta-plugin.myshopify.com').filter())

  return { "online": 'True', "data": storeFound}, 200

@google_ads_bp.route('/google-ads/callback', methods=['GET'])
def google_callback():
  state_str = str(request.args.get('state'))
  state = json.loads(state_str)

  #flow = get_flow()

  return state, 200

  # if os.environ.get('ENV') == 'development':
  #   authorization_response = request.url.replace('http', 'https')
  # else:
  #   authorization_response = request.url

  # flow.fetch_token(authorization_response=authorization_response)

  # response = credentials_to_dict(flow.credentials)

  # try:
  #   user = (u for u in mongo.db.users.find({"_id": ObjectId(state['id'])}))
  # except Exception:
  #   return 'error', 500
  
  # user_json = json.loads(json_util.dumps(user))

  # if len(user_json) == 0:
  #   return ({'error': 'User not found!'}), 404

  # shop_index = None
  # for i, shop in enumerate(user_json[0]['shops']):

  #   if shop['name'] == state['store']:
  #     shop_index = i
  #     break

  # if shop_index is not None:
  #   result = mongo.db.users.update_one(
  #     {'_id': ObjectId(state['id']), 'shops.name': state['store']},
  #     {'$set': {
  #         'shops.$.google_access_token': encrypt_token(response['token']), 
  #         'shops.$.google_refresh_token': encrypt_token(response['refresh_token'])
  #       }
  #     }
  #   )

  #   if result.raw_result['nModified'] == 0:
  #     return ({'error': 'Shop cannot be updated!'}), 400

  #   return ({'message': 'Shop updated!'}), 200
    
  # return ({'error': 'shop not found!'}), 404

@google_ads_bp.route('/google-ads/accounts', methods=['GET'])
def google_accounts():
  id = request.args.get('id')
  store = request.args.get('store')

  if not id or not store:
    return ({'error': 'Missing required parameters.'}), 400
  
  storeFound = r.hgetall(f"store:{store}")

  expiryDate = convert_timestamp_to_date(int(storeFound['expiryDate'])/ 1000)

  if expiryDate["isValid"] == True:
    accessToken = storeFound['googleAccessToken']
    print('same')
  else:
    print('new')
    accessToken = refresh_access_token(storeFound['googleRefreshToken'])

    if(accessToken == 'error'):
      return ({'error': 'error when authenticating store'}), 401
    
    r.hset(f"store:{store}", 'expiryDate', int(datetime.now().timestamp()*1000) + int(accessToken['expires_in'])*1000)

    accessToken = accessToken['new_access_token']

    r.hset(f"store:{store}", 'googleAccessToken', accessToken)

  credentials = google.oauth2.credentials.Credentials(
    accessToken,
    refresh_token=storeFound['googleRefreshToken'],
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
      SELECT customer.id, customer.resource_name, customer.descriptive_name FROM customer WHERE customer.status = 'ENABLED' LIMIT 250
    """
  
    req = client.get_type("SearchGoogleAdsRequest")
    req.customer_id = userId
    req.query = query
    resp = None

    try:
      resp = ga_service.search(request=req)
    except:
      continue

    if resp:
      for row in resp:
        json_str = json_format.MessageToJson(row)
        customer = json.loads(json_str)
        customers.append(customer)

  return customers, 200

@google_ads_bp.route('/google-ads/account/connect', methods=['POST'])
def google_account_connect():
  id = request.args.get('id')
  data = json.loads(request.get_data())

  return data, 200

  # user = json.loads(json_util.dumps((u for u in mongo.db.users.find({"_id": ObjectId(id)}))))[0]

  # shopExists = None

  # for shop in user['shops']:
  #   if shop['name'] == data['store']:
  #     shopExists = shop

  # if shopExists is None:
  #   return ({'error': 'Shop not found.'}), 404
  
  # client = data['client']

  # result = mongo.db.users.update_one(
  #   {'_id': ObjectId(id), 'shops.name': data['store']},
  #   {'$set': {
  #       'shops.$.google_client.id': client['id'], 
  #       'shops.$.google_client.name': client['descriptive_name']
  #     }
  #   }
  # )

  # if result.modified_count <= 0:
  #   response = { 
  #     "success": False, 
  #     "message": "Update failed or did not modify any documents."
  #   }

  #   return json.dumps(response)
  
  # response = { 
  #   "success": True, 
  #   "message": f"Google Ads account {client['descriptive_name']} added to {data['store']}"
  # }

  # return json.dumps(response)

@google_ads_bp.route('/google-ads/account/disconnect', methods=['GET'])
def google_account_disconnect():
  shop = request.args.get('shop')
  id = request.args.get('id')

  return 'ok', 200

  # result = mongo.db.users.update_one(
  #   {'_id': ObjectId(id), 'shops.name': shop},
  #   {'$unset': {
  #       "shops.$.google_client": 1,
  #       "shops.$.google_access_token": 1,
  #       "shops.$.google_refresh_token": 1
  #     }
  #   }
  # )

  # if result.modified_count <= 0:
  #   response = { 
  #     "success": False, 
  #     "message": "Update failed or did not modify any documents."
  #   }

  #   return json.dumps(response)
  
  # response = { 
  #   "success": True, 
  #   "message": f"Removed Google Ads account from ${shop}"
  # }

  # return json.dumps(response)

@google_ads_bp.route('/google-ads/ads', methods=['POST'])
def google_ads():
  data = json.loads(request.get_data())
  start = data['start']
  end = data['end']
  store = data['store']

  if not store:
    return ({'error': 'Missing store!'}), 400
  
  if not start or not end: 
    return ({'error': 'Start date and end date must be set!'}), 400
  
  start_date = datetime.strptime(start, "%Y-%m-%d")
  end_date = datetime.strptime(end, "%Y-%m-%d")

  if start_date > end_date:
    return ({'error': 'Start date cannot occur after the end date!'}), 400
  
  idFound = r.hget(f"google_ads_account:{store}", 'id')

  storeFound = r.hgetall(f"store:{store}")

  if(storeFound == None):
    return ({'error': 'Store not found'}), 404
  
  expiryDate = convert_timestamp_to_date(int(storeFound['googleAdsExpiryDate'])/ 1000)

  if expiryDate["isValid"] == True:
    accessToken = storeFound['googleAdsAccessToken']
  else:
    print('new')
    accessToken = refresh_access_token(storeFound['googleAdsRefreshToken'])

    if(accessToken == 'error'):
      return ({'error': 'error when authenticating store'}), 401
    
    r.hset(f"store:{store}", 'expiryDate', int(datetime.now().timestamp()*1000) + int(accessToken['expires_in'])*1000)

    accessToken = accessToken['new_access_token']

    r.hset(f"store:{store}", 'googleAdsAccessToken', accessToken)
  
  credentials = google.oauth2.credentials.Credentials(
    accessToken,
    refresh_token=storeFound['googleAdsRefreshToken'],
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
  req.customer_id = idFound
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
  flow.redirect_uri = url_for('google_ads_bp.google_callback', _external=True)

  return flow

def is_valid_object_id(id_str):
    try:
        ObjectId(id_str)
        return True
    except (ValueError):
        return False

def refresh_access_token(refresh_token):
    token_endpoint = 'https://oauth2.googleapis.com/token'
    payload = {
        'client_id': os.environ.get("GOOGLE_CLIENT_ID"),
        'client_secret': os.environ.get("GOOGLE_CLIENT_SECRET"),
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    response = requests.post(token_endpoint, data=payload)
    if response.status_code == 200:
        data = response.json()
        new_access_token = data['access_token']
        expires_in = data['expires_in']

        return {
          'new_access_token': new_access_token,
          'expires_in': expires_in
        }
    else:
        return 'error'

def convert_timestamp_to_date(timestamp):
    if isinstance(timestamp, str):
      timestamp = int(timestamp)

    date = datetime.fromtimestamp(timestamp)

    current_datetime = datetime.now()

    formatted_date = date.strftime('%Y-%m-%d %H:%M:%S')

    return ({"data": formatted_date, "isValid": current_datetime < date})