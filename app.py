from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import random
import json
import os
import requests


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'hardcoded-fallback'
GRIST_API_URL = "https://docs.getgrist.com/api/docs"
GRIST_API_KEY = os.getenv("GRIST_API_KEY")
GRIST_DOC_ID = os.getenv("GRIST_DOC_ID")
CATEGORIES = {
    "Animal": "🐶",
    "Computer": "💻",
    "Wordlist": "🍎"
}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user_data = get_user_by_id(user_id)
    if user_data:
        return User(user_data['id'], user_data['username'])
    return None

def get_user_by_id(user_id):
    url = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Users/records"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        user_id = int(user_id)
        res = requests.get(url, headers=headers)
        data = res.json()
        records = data.get("records", [])
        
        for record in records:
            if record["id"] == user_id:
                return {
                    'id': record["id"],
                    'username': record["fields"].get("username"),
                    'password_hash': record["fields"].get("password_hash")
                }
    except Exception as e:
        print(f"Error getting user by ID: {e}")
    return None

def get_user_by_username(username):
    """ดึงข้อมูล user จาก Grist โดยใช้ username"""
    url = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Users/records"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        records = data.get("records", [])
        
        for record in records:
            if record["fields"].get("username") == username:
                return {
                    'id': record["id"],
                    'username': record["fields"].get("username"),
                    'password_hash': record["fields"].get("password_hash")
                }
    except Exception as e:
        print(f"Error getting user by username: {e}")
    return None

def create_user_in_grist(username, password_hash):
    url = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Users/records"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "records": [{
            "fields": {
                "username": username,
                "password_hash": password_hash,
                "created_at": datetime.now().isoformat()
            }
        }]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            response_data = res.json()
            return response_data['records'][0]['id']
    except Exception as e:
        print(f"Error creating user: {e}")
    return None

@app.route('/')
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร', 'error')
            return render_template('register.html')
            
        if len(password) < 6:
            flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
            return render_template('register.html')
        
        # ตรวจสอบ username ซ้ำ
        existing_user = get_user_by_username(username)
        if existing_user:
            flash('ชื่อผู้ใช้นี้มีอยู่แล้ว', 'error')
            return render_template('register.html')
        
        # แฮชรหัสผ่าน
        password_hash = generate_password_hash(password)
        
        # สร้าง user ใหม่
        user_id = create_user_in_grist(username, password_hash)
        if user_id:
            user = User(user_id, username)
            login_user(user)
            session['user_id'] = user_id
            flash('สมัครสมาชิกสำเร็จ! เข้าสู่ระบบแล้ว', 'success')
            return redirect(url_for('home'))
        else:
            flash('เกิดข้อผิดพลาดในการสมัครสมาชิก', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('login.html')
        
        user_data = get_user_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'])
            login_user(user)
            session['user_id'] = user_data['id']
            flash('เข้าสู่ระบบสำเร็จ!', 'success')
            return redirect(url_for('home'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('ออกจากระบบแล้ว', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    user_id = current_user.id
    username = current_user.username

    url_base = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Scores"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }

    stats = {
        "total_words": 0,
        "wpm": 0,
        "total_seconds": 0,
        "timestamp_human": None
    }

    try:
        res = requests.get(f"{url_base}/records", headers=headers)
        if res.status_code == 200:
            all_records = res.json().get("records", [])
            record = next(
                (r for r in all_records if str(r["fields"].get("user_id")) == str(user_id)),
                None
            )
            if record:
                fields = record["fields"]
                stats["total_words"] = fields.get("total_words", 0)
                stats["wpm"] = fields.get("wpm", 0)
                stats["total_seconds"] = fields.get("total_seconds", 0)
                stats["timestamp_human"] = fields.get("timestamp_human", "-")
    except Exception as e:
        print(f"Error loading profile stats: {e}")

    return render_template("profile.html", user=current_user, stats=stats)


@app.route('/play/<category>')
@login_required
def play(category):
    path = os.path.join('wordlist', f'{category}.json')
    if not os.path.exists(path):
        return f'ไม่พบหมวด: {category}', 404

    with open(path, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    word_pool = list(dictionary.keys())
    random.shuffle(word_pool)

    max_words = request.args.get("max_words", type=int)
    if max_words and max_words > 0:
        word_pool = word_pool[:max_words]

    words_json_string = json.dumps(word_pool)

    return render_template(
        'index.html',
        words=words_json_string,
        dictionary=dictionary,
        category=category
    )

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

def send_score_to_grist(user_id, username, table_id, score): 
    print(f"📝 ส่งคะแนน: user_id={user_id}, username={username}, room={table_id}, score={score}")
    url_base = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Scores"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # ดึง record ทั้งหมดแล้วกรองตาม user_id และ room
        print(f"📥 Checking existing score in Grist for user_id={user_id}, room={table_id}")
        res = requests.get(f"{url_base}/records", headers=headers)

        if res.status_code != 200:
            print(f"❌ Failed to fetch records: {res.status_code}")
            print("🔴 Response body:", res.text)
            return False

        data = res.json()
        all_records = data.get("records", [])

        # 🟢 กำหนดตัวแปรก่อน แล้วค่อย print
        user_records = [r for r in all_records if 
                        str(r["fields"].get("user_id")) == str(user_id) and 
                        r["fields"].get("room") == table_id]

        print(f"🔍 Matched user records: {len(user_records)}")

        if user_records:
            best_record = max(user_records, key=lambda r: r["fields"].get("score", 0))
            best_score = best_record["fields"].get("score", 0)
            record_id = best_record["id"]

            if score > best_score:
                patch_url = f"{url_base}/records"
                payload = {
                    "records": [{
                        "id": record_id,
                        "fields": {
                            "user_id": user_id,
                            "username": username,
                            "room": table_id,
                            "score": score,
                        }
                    }]
                }

                res_patch = requests.patch(patch_url, headers=headers, json=payload)

                for r in user_records:
                    if r["id"] != record_id:
                        requests.delete(f"{url_base}/records/{r['id']}", headers=headers)
                return res_patch.status_code == 200
            else:
                for r in user_records:
                    if r["id"] != record_id:
                        requests.delete(f"{url_base}/records/{r['id']}", headers=headers)
                return True
        else:
            print("🔍 No existing record, creating new one.")
            return create_new_score_record(user_id, username, table_id, score, url_base, headers)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False

    
def create_new_score_record(user_id, username, total_words, wpm, url_base, headers):
    post_url = f"{url_base}/records"
    payload = {
        "records": [{
            "fields": {
                "user_id": user_id,
                "username": username,
                "total_words": total_words,
                "wpm": wpm,
            }
        }]
    }

    print("📤 Sending new score payload:", payload)

    res_post = requests.post(post_url, headers=headers, json=payload)
    print("📬 Response status:", res_post.status_code)
    print("📬 Response body:", res_post.text)
    return res_post.status_code == 200

@app.route('/leaderboard/<room>')
@login_required
def leaderboard(room):
    url = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Scores/records"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        all_scores = data.get("records", [])
        
        # กรองตาม room
        room_scores = [
            r["fields"] for r in all_scores
            if r["fields"].get("room") == room
        ]
        
        # เรียงจากมากไปน้อย
        room_scores.sort(key=lambda x: x.get("score", 0), reverse=True)

        return render_template("leaderboard.html", scores=room_scores, room=room)
    
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return "เกิดข้อผิดพลาดในการโหลด Leaderboard", 500


@app.route('/submit_score', methods=['POST'])
@login_required
def submit_score():
    data = request.json
    new_total_words = int(data.get('total_words', 0) or 0)
    wpm = int(data.get('wpm', 0) or 0)
    play_seconds = int(data.get('total_seconds', 0) or 0)

    user_id = current_user.id
    username = current_user.username

    url_base = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Scores"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.get(f"{url_base}/records", headers=headers)
        if res.status_code != 200:
            return jsonify({'status': 'error', 'message': 'Failed to fetch records'}), 500

        all_records = res.json().get("records", [])
        existing_record = next(
            (r for r in all_records if str(r["fields"].get("user_id")) == str(user_id)),
            None
        )

        if existing_record:
            fields = existing_record["fields"]
            old_total_words = fields.get("total_words", 0)
            old_total_seconds = fields.get("total_seconds", 0)

            payload = {
                "records": [{
                    "id": existing_record["id"],
                    "fields": {
                        "user_id": user_id,
                        "username": username,
                        "total_words": old_total_words + new_total_words,
                        "wpm": wpm,
                        "total_seconds": old_total_seconds + play_seconds,
                    }
                }]
            }
            res_patch = requests.patch(f"{url_base}/records", headers=headers, json=payload)
            success = res_patch.status_code == 200
        else:
            payload = {
                "records": [{
                    "fields": {
                        "user_id": user_id,
                        "username": username,
                        "total_words": new_total_words,
                        "wpm": wpm,
                        "total_seconds": play_seconds,
                    }
                }]
            }
            res_post = requests.post(f"{url_base}/records", headers=headers, json=payload)
            success = res_post.status_code == 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        success = False

    return jsonify({
        'status': 'ok' if success else 'error',
        'message': 'Data submitted successfully' if success else 'Failed to submit data'
    })


if __name__ == '__main__':
    app.run(debug=True, port=10100, host="0.0.0.0", use_reloader=False)