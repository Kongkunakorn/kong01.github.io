from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, abort
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

ICON_MAP = {
    "animal": "🐶",
    "computer": "💻",
    "wordlist": "🍎",
    "fruit": "🍊",
    "vehicle": "🚗",
    "sport": "⚽",
}

def load_categories():
    categories = {}
    wordlist_dir = os.path.join(os.path.dirname(__file__), "wordlist")
    if not os.path.exists(wordlist_dir):
        os.makedirs(wordlist_dir)

    for filename in os.listdir(wordlist_dir):
        if filename.endswith(".json"):
            name = filename.replace(".json", "")
            icon = ICON_MAP.get(name.lower(), "📘")
            categories[name] = icon
    return categories

CATEGORIES = load_categories()

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
                "created_at": datetime.now().isoformat(timespec="seconds")
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
    categories = CATEGORIES
    category_sizes = {}
    played = []

    # (ถ้ายังไม่ต้องใช้ played_categories จริง ๆ สามารถลบบล็อกนี้ได้)
    if current_user.is_authenticated:
        url = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Scores/records"
        headers = {"Authorization": f"Bearer {GRIST_API_KEY}"}
        try:
            res = requests.get(url, headers=headers).json()
            record = next(
                (r for r in res.get("records", []) if str(r["fields"].get("user_id")) == str(current_user.id)),
                None
            )
            if record:
                played = record["fields"].get("played_categories", "").split(",")
        except Exception as e:
            print(f"Error fetching played categories: {e}")

    for key in categories:
        path = os.path.join("wordlist", f"{key}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    category_sizes[key] = len(data)
            except Exception as e:
                print(f"[ERROR] Failed to load {key}: {e}")
                category_sizes[key] = 0
        else:
            category_sizes[key] = 0

    return render_template("home.html", categories=categories, category_sizes=category_sizes, played=played)

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

        existing_user = get_user_by_username(username)
        if existing_user:
            flash('ชื่อผู้ใช้นี้มีอยู่แล้ว', 'error')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
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

    url_base = f"{GRIST_API_URL}/{GRIST_DOC_ID}/tables/Scores"
    headers = {
        "Authorization": f"Bearer {GRIST_API_KEY}",
        "Content-Type": "application/json"
    }

    stats = {
        "total_words": 0,
        "wpm": 0,
        "total_seconds": 0,
        "last_played_human": None
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
                stats["last_played_human"] = fields.get("last_played_human", "-")
    except Exception as e:
        print(f"Error loading profile stats: {e}")

    return render_template("profile.html", user=current_user, stats=stats)

@app.route('/play/<category>')
@login_required
def play(category):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(BASE_DIR, "wordlist", f"{category}.json")
    if not os.path.exists(path):
        return f'ไม่พบหมวด: {category}', 404

    # ภาษาต้นทาง/ปลายทาง
    src = request.args.get("src", "en")
    dest = request.args.get("dest", "th")

    with open(path, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)  # {"key": {"en": "...", "th": "...", ...}, ...}

    # คัดเฉพาะคำที่มีทั้ง src และ dest
    filtered_keys = [
        k for k, obj in dictionary.items()
        if isinstance(obj, dict)
        and obj.get(src) and str(obj.get(src)).strip()
        and obj.get(dest) and str(obj.get(dest)).strip()
    ]
    if not filtered_keys:
        return f"หมวด '{category}' ไม่มีคำที่รองรับจาก {src} ไป {dest}", 400

    # จำกัดจำนวนคำ (ถ้ามี)
    max_words = request.args.get("max_words", type=int)
    random.shuffle(filtered_keys)
    if max_words and max_words > 0:
        filtered_keys = filtered_keys[:max_words]

    # ส่ง “ข้อความภาษาต้นทาง” ให้ผู้เล่นพิมพ์
    words_src = [dictionary[k][src] for k in filtered_keys]
    words_json_string = json.dumps(words_src, ensure_ascii=False)

    return render_template(
        'index.html',
        words=words_json_string,
        category=category,
        src=src,
        dest=dest
    )

@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    input_word = (data.get('word') or '').strip()
    category = data.get('category', '')
    src_lang = data.get('src_lang', 'en')
    dest_lang = data.get('dest_lang', 'th')
    key = data.get('key')

    path = os.path.join('wordlist', f'{category}.json')
    if not os.path.exists(path):
        return jsonify({'translation': 'หมวดไม่ถูกต้อง'})

    with open(path, 'r', encoding='utf-8') as f:
        word_dict = json.load(f)

    entry = None
    if key and key in word_dict:
        entry = word_dict[key]
    else:
        target = input_word.lower()
        for k, obj in word_dict.items():
            if not isinstance(obj, dict):
                continue
            cand = obj.get(src_lang) or obj.get('en')
            if not cand:
                continue
            cand_cmp = cand.lower() if hasattr(cand, 'lower') else cand
            if cand_cmp == target:
                entry = obj
                break

    if not entry:
        return jsonify({'translation': 'ไม่พบคำใน wordlist'})

    translation = entry.get(dest_lang) or entry.get('en') or ''
    return jsonify({'translation': translation})

def send_score_to_grist(user_id, username, table_id, score):
    print(f"📝 send_score_to_grist (legacy) uid={user_id}, username={username}, room={table_id}, score={score}")

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
    res_post = requests.post(post_url, headers=headers, json=payload)
    return res_post.status_code == 200

@app.post('/submit_score')
@login_required
def submit_score():
    data = request.get_json(force=True) or {}
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

    # ✅ ช่วยจับเคส env หาย
    if not GRIST_API_KEY or not GRIST_DOC_ID:
        print("[submit_score] Missing GRIST_API_KEY or GRIST_DOC_ID")
        return jsonify({'status':'error','message':'Missing GRIST env'}), 500

    now_human = datetime.now().isoformat(timespec="seconds")

    try:
        res = requests.get(f"{url_base}/records", headers=headers)
        if res.status_code != 200:
            print("[submit_score] GET /Scores/records failed:", res.status_code, res.text[:500])
            return jsonify({'status': 'error', 'message': 'Failed to fetch records', 'detail': res.text}), 500

        all_records = res.json().get("records", [])
        existing_record = next(
            (r for r in all_records if str(r["fields"].get("user_id")) == str(user_id)),
            None
        )

        if existing_record:
            fields = existing_record["fields"]
            old_total_words = int(fields.get("total_words", 0) or 0)
            old_total_seconds = int(fields.get("total_seconds", 0) or 0)

            payload = {
                "records": [{
                    "id": existing_record["id"],
                    "fields": {
                        "user_id": user_id,
                        "username": username,
                        "total_words": old_total_words + new_total_words,
                        "wpm": wpm,  # ใช้ WPM ล่าสุดทับค่าเดิม
                        "total_seconds": old_total_seconds + play_seconds,
                    }
                }]
            }
            res_patch = requests.patch(f"{url_base}/records", headers=headers, json=payload)
            print("[submit_score] PATCH status:", res_patch.status_code, res_patch.text[:500])
            if res_patch.status_code not in (200, 201):
                return jsonify({'status':'error','message':'Patch failed','detail':res_patch.text}), 500
            success = True
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
            print("[submit_score] POST status:", res_post.status_code, res_post.text[:500])
            if res_post.status_code not in (200, 201):
                return jsonify({'status':'error','message':'Post failed','detail':res_post.text}), 500
            success = True

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

    return jsonify({'status':'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=10100, host="0.0.0.0", use_reloader=False)
