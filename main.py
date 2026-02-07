from flask import Flask, request, render_template_string, send_file, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os, random, sqlite3, string
from datetime import datetime
from functools import wraps

UPLOAD_DIR = "uploads"
DB_FILE = "app.db"
SECRET_KEY = os.urandom(24)
BASE_URL = "http://localhost:8080"  # change to your public domain when deploying

os.makedirs(UPLOAD_DIR, exist_ok=True)
app = Flask(__name__)
app.secret_key = SECRET_KEY

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    db.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        filename TEXT,
        stored_name TEXT,
        uploaded TEXT
    )""")
    db.commit()

init_db()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def random_filename(ext):
    chars = string.ascii_letters + string.digits + "-_"
    name = ''.join(random.choices(chars, k=10))
    return f"{name}.{ext}"

HTML_MAIN = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CatBox</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<style>
body{font-family:Inter,sans-serif;background:#2b1f16;color:#e6d7c3;margin:0;display:flex;flex-direction:column;align-items:center;}
header{padding:20px;font-size:32px;font-weight:700;color:#d9b08c;text-shadow:1px 1px #5c3b25;}
.container{max-width:500px;width:100%;margin-top:40px;text-align:center;}
.upload-btn{display:inline-block;padding:18px 36px;background:#7b5a3c;border-radius:20px;cursor:pointer;font-weight:600;transition:0.2s;color:white;}
.upload-btn:hover{background:#5c3b25;}
input[type=file]{display:none;}
.progress-container{width:100%;background:#5c3b25;border-radius:12px;margin-top:20px;overflow:hidden;height:20px;display:none;}
.progress-bar{width:0%;height:100%;background:#d9b08c;transition:0.3s;}
.file-list{margin-top:30px;text-align:left;}
.file-item{background:#3f2d23;padding:12px;margin-bottom:10px;border-radius:16px;display:flex;justify-content:space-between;align-items:center;flex-direction:column;}
.file-row{width:100%;display:flex;justify-content:space-between;align-items:center;margin-top:5px;}
input.link-input{width:100%;padding:6px;border-radius:8px;border:none;background:#5c3b25;color:#d9b08c;}
a{color:#d9b08c;text-decoration:none;font-weight:600;}
.cat-img{width:100%;max-width:300px;margin-top:30px;border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,0.4);}
button.copy-btn{padding:4px 8px;border:none;border-radius:8px;background:#7b5a3c;color:white;cursor:pointer;transition:0.2s;}
button.copy-btn:hover{background:#5c3b25;}
</style>
</head>
<body>
<header>CatBox <i class="fas fa-cat"></i></header>
<div class="container">
<label class="upload-btn"><i class="fas fa-upload"></i> Select File
<input type="file" id="fileInput">
</label>
<div class="progress-container">
<div class="progress-bar" id="progressBar"></div>
</div>
<div class="file-list">
{% for f in files %}
<div class="file-item">
<span><i class="fas fa-file"></i> {{ f.filename }}</span>
<div class="file-row">
<a href="/download/{{ f.id }}"><i class="fas fa-download"></i> Download</a>
<a href="/delete/{{ f.id }}"><i class="fas fa-trash"></i> Delete</a>
</div>
<div class="file-row">
<input class="link-input" id="link{{ f.id }}" value="{{ base_url }}/f/{{ f.stored_name }}" readonly>
<button class="copy-btn" onclick="copyLink('{{ f.id }}')">Copy Link</button>
</div>
</div>
{% else %}
<p style="color:#d9b08c;">No files yet.</p>
{% endfor %}
</div>
<img class="cat-img" src="{{ cat_url }}" alt="Random Cat">
</div>
<script>
const fileInput = document.getElementById("fileInput");
const progressBar = document.getElementById("progressBar");
const progressContainer = document.querySelector(".progress-container");
fileInput.addEventListener("change", async ()=>{
if(!fileInput.files.length) return;
const file=fileInput.files[0];
const formData=new FormData();
formData.append("file",file);
progressContainer.style.display="block";
progressBar.style.width="0%";
const xhr=new XMLHttpRequest();
xhr.open("POST","/",true);
xhr.upload.onprogress=e=>{
if(e.lengthComputable){let percent=(e.loaded/e.total)*100;progressBar.style.width=percent+"%";}}
xhr.onload=()=>{progressBar.style.width="100%";setTimeout(()=>{location.reload()},500);}
xhr.send(formData);
});
function copyLink(id){
const input=document.getElementById("link"+id);
input.select();
input.setSelectionRange(0,99999);
document.execCommand("copy");
alert("Copied: "+input.value);
}
</script>
</body>
</html>
"""

HTML_AUTH = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{{ title }}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
body{font-family:Inter,sans-serif;background:#2b1f16;color:#e6d7c3;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
.auth-container{background:#3f2d23;padding:40px;border-radius:16px;display:flex;flex-direction:column;width:300px;}
input{margin-bottom:15px;padding:10px;border-radius:8px;border:none;}
button{padding:10px;border:none;border-radius:8px;background:#7b5a3c;color:white;font-weight:600;cursor:pointer;transition:0.2s;}
button:hover{background:#5c3b25;}
a{color:#d9b08c;text-decoration:none;margin-top:10px;text-align:center;}
</style>
</head>
<body>
<div class="auth-container">
<h2 style="text-align:center">{{ title }}</h2>
<form method="post">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button>{{ title }}</button>
</form>
{% if alt_link %}
<a href="{{ alt_link }}">{{ alt_text }}</a>
{% endif %}
</div>
</body>
</html>
"""

CAT_IMAGES = ["https://cataas.com/cat?1","https://cataas.com/cat?2","https://cataas.com/cat?3","https://cataas.com/cat?4","https://cataas.com/cat?5"]

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        db = get_db()
        try:
            db.execute("INSERT INTO users (username,password) VALUES (?,?)",(username,password))
            db.commit()
        except:
            return "Username taken"
        return redirect(url_for("login"))
    return render_template_string(HTML_AUTH, title="Register", alt_link="/login", alt_text="Login instead")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
        if user and check_password_hash(user["password"],password):
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
        return "Invalid login"
    return render_template_string(HTML_AUTH, title="Login", alt_link="/register", alt_text="Register instead")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET","POST"])
@login_required
def index():
    if request.method=="POST":
        f = request.files["file"]
        ext = f.filename.split('.')[-1]
        stored = random_filename(ext)
        f.save(os.path.join(UPLOAD_DIR, stored))
        db = get_db()
        db.execute("INSERT INTO files (user_id,filename,stored_name,uploaded) VALUES (?,?,?,?)",
                   (session["user_id"], f.filename, stored, datetime.utcnow().isoformat()))
        db.commit()
        return "ok"
    db = get_db()
    files = db.execute("SELECT * FROM files WHERE user_id=?",(session["user_id"],)).fetchall()
    cat_url = random.choice(CAT_IMAGES)
    return render_template_string(HTML_MAIN, files=files, cat_url=cat_url, base_url=BASE_URL)

@app.route("/download/<int:file_id>")
@login_required
def download(file_id):
    db = get_db()
    f = db.execute("SELECT * FROM files WHERE id=? AND user_id=?",(file_id,session["user_id"])).fetchone()
    if not f: return "Not found"
    return send_file(os.path.join(UPLOAD_DIR,f["stored_name"]), as_attachment=True)

@app.route("/delete/<int:file_id>")
@login_required
def delete(file_id):
    db = get_db()
    f = db.execute("SELECT * FROM files WHERE id=? AND user_id=?",(file_id,session["user_id"])).fetchone()
    if not f: return "Not found"
    try: os.remove(os.path.join(UPLOAD_DIR,f["stored_name"]))
    except: pass
    db.execute("DELETE FROM files WHERE id=?",(file_id,))
    db.commit()
    return redirect(url_for("index"))

@app.route("/f/<filename>")
def public_file(filename):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return "Not found"
    return send_file(path)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
