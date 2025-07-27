from flask import Flask, render_template, request, jsonify
import random
import json
import os

app = Flask(__name__)

wordlist_path = os.path.join('wordlist', 'wordlist.json')
with open(wordlist_path, 'r', encoding='utf-8') as f:
    word_dict = json.load(f)
    word_pool = list(word_dict.keys())

@app.route('/')
def index():
    random_words = word_pool
    return render_template('index.html', words=random_words)

@app.route('/translate', methods=['POST'])
def translate():
    word = request.json['word']
    translation = word_dict.get(word.lower(), 'ไม่พบคำแปล')
    return jsonify({'translation': translation})

if __name__ == '__main__':
    app.run(debug=True,port=10100,host="0.0.0.0",use_reloader=True)
