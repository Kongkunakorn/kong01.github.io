from flask import Flask, render_template, request, jsonify
import random
import json
import os

app = Flask(__name__)

CATEGORIES = {
    "animal": "🐶",
    "computer": "💻",
    "wordlist": "🍎"
}

def home():
    category_sizes = {}
    for key in CATEGORIES:
        path = os.path.join('wordlist', f'{key}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                category_sizes[key] = len(data)
        else:
            category_sizes[key] = 0

    return render_template("home.html", categories=CATEGORIES, category_sizes=category_sizes)

@app.route('/play/<category>')
def play(category):
    path = os.path.join('wordlist', f'{category}.json')
    if not os.path.exists(path):
        return f'ไม่พบหมวด: {category}', 404

    with open(path, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    word_pool = list(dictionary.keys())
    random.shuffle(word_pool)

    return render_template('index.html', words=word_pool, dictionary=dictionary, category=category)

@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    word = data.get('word', '').lower()
    category = data.get('category', '')

    path = os.path.join('wordlist', f'{category}.json')
    if not os.path.exists(path):
        return jsonify({'translation': 'หมวดไม่ถูกต้อง'})

    with open(path, 'r', encoding='utf-8') as f:
        word_dict = json.load(f)

    translation = word_dict.get(word, 'ไม่พบคำแปล')
    return jsonify({'translation': translation})

if __name__ == '__main__':
    app.run(debug=True,port=10100,host="0.0.0.0",use_reloader=True)
