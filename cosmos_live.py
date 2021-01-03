import mysql.connector
from pathlib import Path
from datetime import datetime, timedelta
import requests
import time
import json
import sys

def log(message):
	ct = str(datetime.now())
	ct = ct[:ct.rindex(".")]
	print("[%s] %s" % (ct, message))

class ConfigReader:
	environment = None
	config_json = None

	def __init__(self, environment):
		self.environment = environment

		config_file = Path(str(Path.home()) + "/.cosmos/config")
		if not config_file.is_file():
			raise ValueError('config file path is invalid.')
		else:
			self.config_json = json.loads(config_file.read_text())

	def get_database_connection_info(self):
		return self.config_json["database"][self.environment]

	def get_api_info(self):
		return self.config_json["api"][self.environment]

	def get_json(self, key):
		try:
			return 
		except:
			return None

class DatabaseConnector:
	host = None
	database = None
	user = None
	password = None
	db_connection = None

	def __init__(self, host, database, user, password):
		self.host = host
		self.database = database
		self.user = user
		self.password = password

	def open_connection(self):
		self.db_connection = mysql.connector.connect(
			host = self.host,
			database = self.database,
			user = self.user,
			passwd = self.password
		)

	def close_connection(self):
		self.db_connection.close()

	def get_admin_auth_key(self):
		self.open_connection()

		cursor = self.db_connection.cursor()
		cursor.execute("select value from config where `key` = 'admin_auth_key'")
		result = cursor.fetchall()
		cursor.close()

		self.close_connection()

		return result[0][0]

	def get_live_mode_pre_game_lobby_length(self):
		self.open_connection()

		cursor = self.db_connection.cursor()
		cursor.execute("select value from config where `key` = 'live_mode_pre_game_lobby_length'")
		result = cursor.fetchall()
		cursor.close()

		self.close_connection()

		return int(result[0][0])

	def get_live_mode_post_game_lobby_length(self):
		self.open_connection()

		cursor = self.db_connection.cursor()
		cursor.execute("select value from config where `key` = 'live_mode_post_game_lobby_length'")
		result = cursor.fetchall()
		cursor.close()

		self.close_connection()

		return result[0][0]

	def get_live_mode_question_timer_length(self):
		self.open_connection()

		cursor = self.db_connection.cursor()
		cursor.execute("select value from config where `key` = 'live_mode_question_timer_length'")
		result = cursor.fetchall()
		cursor.close()

		self.close_connection()

		return result[0][0]

	def get_live_mode_round_timer_length(self):
		self.open_connection()

		cursor = self.db_connection.cursor()
		cursor.execute("select value from config where `key` = 'live_mode_round_timer_length'")
		result = cursor.fetchall()
		cursor.close()

		self.close_connection()

		return result[0][0]


class RestApiConnector:
	admin_auth_key = None

	def __init__(self, api_url, admin_auth_key):
		self.api_url = api_url
		self.admin_auth_key = admin_auth_key

	def get_cosmos_live_session(self):
		json = {"admin_auth_key" : self.admin_auth_key};
		full_url = "%s/%s" % (self.api_url, "live")

		response_json = None
		try:
			response = requests.get(full_url, json)
			response_json = response.json()
		except requests.exceptions.ConnectionError:
			pass

		return response_json

	def advance_live_session_to_closed(self):
		log("advance_live_session_to_closed()")
		self.advance_live_session_state("closed")

	def advance_live_session_to_pre_game_lobby(self):
		log("advance_live_session_to_pre_game_lobby()")
		self.advance_live_session_state("pre_game_lobby")

	def advance_live_session_to_in_game(self):
		log("advance_live_session_to_in_game()")
		self.advance_live_session_state("in_game")

	def advance_live_session_to_post_game_lobby(self):
		log("advance_live_session_to_post_game_lobby()")
		self.advance_live_session_state("post_game_lobby")

	def advance_live_session_state(self, state):
		json = {"admin_auth_key" : self.admin_auth_key, "request" : "transition_state", "state" : state};
		full_url = "%s/%s" % (self.api_url, "liveAdmin")
		
		requests.get(full_url, json)

	def advance_live_session_round(self):
		log("advance_live_session_round()")

		json = {"admin_auth_key" : self.admin_auth_key, "request" : "advance_round"};
		full_url = "%s/%s" % (self.api_url, "liveAdmin")
		
		requests.get(full_url, json)

class CosmosLiveSessionManager:
	database_connector = None
	rest_api_connector = None

	def __init__(self, database_connector, rest_api_connector):
		self.database_connector = database_connector
		self.rest_api_connector = rest_api_connector

	def run(self):
		while True:
			live_session = self.rest_api_connector.get_cosmos_live_session()
			if live_session is None:
				log("ERROR: failed to reach api.")
			else:
				self.handle_live_session(live_session["payload"]["cosmos_live_session"])

			time.sleep(1)

	def get_appropriate_state(self, session):
		if self.session_has_ended(session):
			return "POST_GAME_LOBBY"

		start_date_time = self.get_date(session["start"])
		pre_game_lobby_date_time = self.get_pre_game_lobby_date_time(start_date_time)
		now_date_time = self.get_date(datetime.utcnow())

		if now_date_time < pre_game_lobby_date_time:
			return "CLOSED"
		elif now_date_time >= pre_game_lobby_date_time and now_date_time < start_date_time:
			return "PRE_GAME_LOBBY"
		elif now_date_time >= start_date_time:
			return "IN_GAME"

		return "CLOSED"

	def get_pre_game_lobby_date_time(self, start_date_time):
		pre_game_lobby_seconds = self.database_connector.get_live_mode_pre_game_lobby_length()
		return start_date_time - timedelta(seconds = pre_game_lobby_seconds)

	def handle_live_session_in_game(self, session):
		round_seconds_remaining = int(session["round_seconds_remaining"])
		if round_seconds_remaining > 0:
			return

		self.rest_api_connector.advance_live_session_round()

	def handle_live_session(self, session):
		session_state = session["state"]

		if (session_state == "POST_GAME_LOBBY"):
			return

		destination_state = self.get_appropriate_state(session)

		if destination_state == session_state:
			if session_state == "IN_GAME":
				self.handle_live_session_in_game(session)
			return

		if destination_state == "CLOSED":
			self.rest_api_connector.advance_live_session_to_closed()
		elif destination_state == "PRE_GAME_LOBBY":
			self.rest_api_connector.advance_live_session_to_pre_game_lobby()
		elif destination_state == "IN_GAME":
			self.rest_api_connector.advance_live_session_to_in_game()
		elif destination_state == "POST_GAME_LOBBY":
			self.rest_api_connector.advance_live_session_to_post_game_lobby()

	def session_has_ended(self, session):
		session_round = session["round"]
		session_players = session["player_count"];

		return session_round > 1 and session_players == 0

	def get_date(self, date):
		str_date = self.clean_date(str(date))
		datetime_object = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')

		return datetime_object

	def clean_date(self, date):
		return date.replace("T", " ")[:date.rindex(".")]


def get_database_connection_info(environment):
	config_reader = ConfigReader(environment)
	database_connection_info = config_reader.get_database_connection_info()
	if database_connection_info == None:
		raise ValueError('database config data is invalid.')

	return database_connection_info

def get_api_info(environment):
	config_reader = ConfigReader(environment)
	api_info = config_reader.get_api_info()
	if api_info == None:
		raise ValueError('api config data is invalid.')

	return api_info

def get_api_url(environment):
	api_info = get_api_info(environment)
	api_url = "%s:%s" % (api_info["host"], api_info["port"])

	return api_url

def get_database_connector(database_connection_info):
	host = database_connection_info["host"]
	database = database_connection_info["database"]
	user = database_connection_info["user"]
	password = database_connection_info["password"]

	database_connector = DatabaseConnector(host, database, user, password)

	return database_connector

def main(environment):
	database_connection_info = get_database_connection_info(environment)
	database_connector = get_database_connector(database_connection_info)

	admin_auth_key = database_connector.get_admin_auth_key()
	api_url = get_api_url(environment)

	rest_api_connector = RestApiConnector(api_url, admin_auth_key)

	cosmos_live_session_manager = CosmosLiveSessionManager(database_connector, rest_api_connector)
	cosmos_live_session_manager.run()



if __name__ == "__main__":
	if (len(sys.argv) != 2):
		log("error: must specify environment.")
		exit(1)

	try:
		main(sys.argv[1])
	except KeyboardInterrupt:
		sys.exit(0)