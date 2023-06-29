import json
import google_auth_oauthlib.flow
import os
from dotenv import load_dotenv
from flask import (Blueprint, request, url_for)
from extensions.database import mongo
load_dotenv()

google_auth_bp = Blueprint('auth', __name__)

@google_auth_bp.route('/google/authorize', methods=['GET'])
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


@google_auth_bp.route('/google/callback', methods=['GET'])
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
  flow.redirect_uri = url_for('google_auth_bp.google_callback', _external=True)

  return flow
