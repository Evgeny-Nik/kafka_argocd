from flask import Flask, request, jsonify, render_template, redirect
from kafka import KafkaProducer
import requests
import json
import os
import logging

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)


KAFKA_HOST = os.getenv('KAFKA_HOST')
KAFKA_PORT = os.getenv('KAFKA_PORT')
API_URL = os.getenv('API_URL')
TOPIC_NAME = "purchase_topic"


producer = KafkaProducer(
    bootstrap_servers=f'{KAFKA_HOST}:{KAFKA_PORT}',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


@app.route('/buy', methods=['POST'])
def buy_item():
    user_id = request.form.get('userID')
    item_id = request.form.get('itemID')
    if user_id and item_id:
        purchase_data = {'userID': user_id, 'itemID': item_id}
        producer.send(TOPIC_NAME, value=purchase_data)
        return redirect('/')
    else:
        return jsonify({'status': 'error', 'message': 'Invalid request parameters'}), 400


@app.route('/')
def main():
    users_response = requests.get(f'http://{API_URL}/users')
    items_response = requests.get(f'http://{API_URL}/items')
    users = users_response.json()
    items = items_response.json()
    return render_template('index.html', users=users, items=items)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
