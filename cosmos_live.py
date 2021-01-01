import mysql.connector
from pathlib import Path
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

	def __init__(self, admin_auth_key):
		self.admin_auth_key = admin_auth_key


def get_database_connection_data(environment):
	config_reader = ConfigReader(environment)
	database_connection_data = config_reader.get_database_connection_info()
	if database_connection_data == None:
		raise ValueError('database config data is invalid.')

	return database_connection_data

def get_database_connector(database_connection_data):
	host = database_connection_data["host"]
	database = database_connection_data["database"]
	user = database_connection_data["user"]
	password = database_connection_data["password"]

	database_connector = DatabaseConnector(host, database, user, password)

	return database_connector

def main(environment):
	database_connection_data = get_database_connection_data(environment)
	database_connector = get_database_connector(database_connection_data)

	admin_auth_key = database_connector.get_admin_auth_key()
	rest_api_connector = RestApiConnector(admin_auth_key)




	


if __name__ == "__main__":
	if (len(sys.argv) != 2):
		print("error: must specify environment.")
		exit(1)

	main(sys.argv[1])