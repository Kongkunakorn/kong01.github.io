from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    sentence = "hello world are you gay"
    words = sentence.split()
    return render_template('index.html', sentence=words)

@app.route('/translate', methods=['POST'])
def translate():
    word = request.json['word']
    dictionary = {
        'hello': 'สวัสดี',
        'world': 'โลก',
        'are': 'เป็น',
        'you': 'คุณ',
        'gay': 'เกย์'
    }
    translation = dictionary.get(word.lower(), 'ไม่พบคำแปล')
    return jsonify({'translation': translation})

if __name__ == '__main__':
    app.run(debug=True,port=10100,host="0.0.0.0",use_reloader=True)
