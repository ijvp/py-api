import os
from flask import (Blueprint, request, url_for)
from googleapiclient.discovery import build
import httplib2
import google.oauth2.credentials
from oauth2client import client
from oauth2client import file
from oauth2client import tools
from oauth2client.service_account import ServiceAccountCredentials

google_analytics_bp = Blueprint('analytics', __name__)

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
CLIENT_SECRETS_FILE = "../credentials.json"
VIEW_ID = ""

def init_client():	
	# Set the path to the client_secrets.json file you downloaded from the developer console.
	client_secrets_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

	
	# Create the client object and set the authorization configuration.
	client = build('analytics', 'v3', credentials=ServiceAccountCredentials.from_service_account_file(client_secrets_path))
	client.authorization.scopes.append('https://www.googleapis.com/auth/analytics.readonly')

	try:
			# If the user has already authorized this app, get an access token.
			# else redirect to ask the user to authorize access to Google Analytics.
			if client.authorization and client.authorization.valid:
					# Create an authorized analytics service object.
					analytics = client
			else:
					raise Exception('No access token found.')

			def get_first_profile_id(analytics):
					# Get the user's first view (profile) ID.

					# Get the list of accounts for the authorized user.
					accounts = analytics.management().accounts().list().execute()

					if 'items' in accounts and len(accounts['items']) > 0:
							first_account_id = accounts['items'][0]['id']

							# Get the list of properties for the authorized user.
							properties = analytics.management().webproperties().list(accountId=first_account_id).execute()

							if 'items' in properties and len(properties['items']) > 0:
									first_property_id = properties['items'][0]['id']

									# Get the list of views (profiles) for the authorized user.
									profiles = analytics.management().profiles().list(
											accountId=first_account_id,
											webPropertyId=first_property_id
									).execute()

									if 'items' in profiles and len(profiles['items']) > 0:
											# Return the first view (profile) ID.
											return profiles['items'][0]['id']

									else:
											raise Exception('No views (profiles) found for this user.')

							else:
									raise Exception('No properties found for this user.')

					else:
							raise Exception('No accounts found for this user.')

			def get_results(analytics, profile_id):
					# Calls the Core Reporting API and queries for the number of sessions
					# for the last seven days.
					return analytics.data().ga().get(
							ids='ga:' + profile_id,
							start_date='7daysAgo',
							end_date='today',
							metrics='ga:sessions'
					).execute()

			def print_results(results):
					# Parses the response from the Core Reporting API and prints
					# the profile name and total sessions.
					if 'rows' in results and len(results['rows']) > 0:
							# Get the profile name.
							profile_name = results['profileInfo']['profileName']

							# Get the entry for the first entry in the first row.
							sessions = results['rows'][0][0]

							# Print the results.
							print(f"First view (profile) found: {profile_name}")
							print(f"Total sessions: {sessions}")

					else:
							print("<p>No results found.</p>")

			# Get the first profile ID.
			profile_id = get_first_profile_id(analytics)

			# Get the results from the Core Reporting API.
			results = get_results(analytics, profile_id)

			# Print the results.
			print_results(results)
	except Exception as e:
			print(f"An exception occurred: {e}")

@google_analytics_bp.route('/google-ads/callback', methods=['GET'])
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


@google_analytics_bp.route('/google-analytics/accounts', methods=['GET'])
def get_google_analytics_accounts():
	return 'fetching...', 200


@google_analytics_bp.route('/google-analytics/test', methods=['GET'])
def attempt_create_client():
    return init_client()