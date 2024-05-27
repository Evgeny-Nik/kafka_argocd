from flask import Flask, jsonify
from pymongo import MongoClient
from kafka import KafkaConsumer
import threading
import json
import os
import logging

logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')


app = Flask(__name__)

# Use the MongoDB instance running on port 27017
MONGO_HOST = os.getenv('MONGO_HOST')
MONGO_PORT = os.getenv('MONGO_PORT')
MONGO_USER = os.getenv('MONGO_USER')
MONGO_PASS = os.getenv('MONGO_PASS')

KAFKA_HOST = os.getenv('KAFKA_HOST')
KAFKA_PORT = os.getenv('KAFKA_PORT')
TOPIC_NAME = "purchase_topic"

conn_str = f'mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/'
mongo_client = MongoClient(conn_str, 
                           serverSelectionTimeoutMS=5000, 
                           authSource='admin', 
                           authMechanism='SCRAM-SHA-1')
db = mongo_client['shop_db']
collection_user = db['users']
collection_items = db['items']


# Kafka configuration
consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers=f'{KAFKA_HOST}:{KAFKA_PORT}',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)


def consume_messages():
    for message in consumer:
        data = message.value
        user_id = data.get('userID')
        item_id = data.get('itemID')
        if user_id and item_id:
            # Update the purchases list in MongoDB
            collection_user.update_one({'userID': user_id}, {'$push': {'purchases': item_id}})
        else:
            print("Invalid purchase data:", data)


@app.route('/items', methods=['GET'])
def get_items():
    items = list(collection_items.find({}, {'_id': 0}))
    return jsonify(items)


@app.route('/users', methods=['GET'])
def get_users():
    users = list(collection_user.find({}, {'_id': 0}))
    return jsonify(users)

# Start Kafka consumer in a separate thread
threading.Thread(target=consume_messages, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)