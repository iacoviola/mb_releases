import requests
import sqlite3
from configparser import ConfigParser

from flask import Flask, request

config = ConfigParser()
config.read('config.cfg')

tg_token = config.get('SETTINGS', 'tg_token')
tg_id = config.get('SETTINGS', 'tg_id')

db_path = config.get('PATHS', 'db')

tg_url = f'https://api.telegram.org/bot'

app = Flask(__name__)

def mark_acknowledged(db_path, msg_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        UPDATE releases SET still_interesting = 0 WHERE last_msg_id = ?
    ''', (msg_id,))
    conn.commit()
    conn.close()

@app.route(f"/{tg_token}", methods=['POST'])
def receive_update():
    update = request.json
    if 'callback_query' in update:
        callback_query = update['callback_query']
        callback_data = callback_query['data']
        
        if callback_data.startswith('download') or callback_data.startswith('unwanted'):
            message_id = callback_query['message']['message_id']
            mark_acknowledged(db_path=db_path, msg_id=message_id)
            
            # Acknowledge to the user in the chat
            requests.post(f'{tg_url}{tg_token}/answerCallbackQuery', json={
                'callback_query_id': callback_query['id'],
                'text': 'Acknowledged! You won\'t receive further messages about this release.'
            })
    
    return '', 200

if __name__ == "__main__":
    app.run(port=8443)


# Test with curl
# curl -X POST -H "Content-Type: application/json" -d '{"callback_query": {"id": "123456789", "data": "downloaded", "message": {"message_id": 123456789}}}' http://localhost:8443/123456789:AAE-123456789

# Remember to uncomment ngix configuration