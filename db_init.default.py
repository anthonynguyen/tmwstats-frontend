import pymongo
import os
client = pymongo.MongoClient("MongoDB database URL goes here") 
db = client.get_default_database()
