import mysql.connector
from pathlib import Path
from datetime import datetime
import requests
import time
import json
import sys

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

class RestApiConnector:
	admin_auth_key = None

	def __init__(self, api_url, admin_auth_key):
		self.api_url = api_url
		self.admin_auth_key = admin_auth_key

	def get_cosmos_live_session(self):
		json = {"admin_auth_key" : self.admin_auth_key};
		full_url = "%s/%s" % (self.api_url, "live")
		response = requests.get(full_url, json)

		return response.json()

class CosmosLiveSessionManager:
	rest_api_connector = None
	def __init__(self, rest_api_connector):
		self.rest_api_connector = rest_api_connector

	def run(self):
		while True:
			live_session = self.rest_api_connector.get_cosmos_live_session()
			self.handle_live_session(live_session["payload"]["cosmos_live_session"])

			time.sleep(1)

	def handle_live_session(self, session):
		session_state = session["state"]

		if session_state == "CLOSED":
			self.handle_closed_live_session(session)

	def handle_closed_live_session(self, session):
		start_date_time = self.get_date(session["start"])
		now_date_time = self.get_date(datetime.utcnow())

		print ("start: " + str(start_date_time))
		print ("now:   " + str(now_date_time))
		print ()

		if (start_date_time > now_date_time):
			return

		print ("later!")

	def clean_date(self, date):
		return date.replace("T", " ")[:date.rindex(".")]

	def get_date(self, date):
		date = str(date)
		str_date = self.clean_date(date)

		datetime_object = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')

		return datetime_object


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

	cosmos_live_session_manager = CosmosLiveSessionManager(rest_api_connector)
	cosmos_live_session_manager.run()



if __name__ == "__main__":
	if (len(sys.argv) != 2):
		print("error: must specify environment.")
		exit(1)

	try:
		main(sys.argv[1])
	except KeyboardInterrupt:
		sys.exit(0)