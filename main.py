from flask import Flask, request, render_template_string, send_file, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import os, random, sqlite3
from datetime import datetime
from functools import wraps

UPLOAD_DIR = "uploads"
DB_FILE = "app.db"
SECRET_KEY = os.urandom(24)
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
    db.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, user_id INTEGER, filename TEXT, uploaded TEXT)")
    db.commit()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CatBox</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<style>
body {font-family: Inter, sans-serif; background:#2b1f16; color:#e6d7c3; margin:0; display:flex; flex-direction:column; align-items:center;}
header {padding:20px; font-size:32px; font-weight:700; color:#d9b08c; text-shadow:1px 1px #5c3b25;}
.container {max-width:500px; width:100%; margin-top:40px; text-align:center;}
.upload-btn {display:inline-block; padding:18px 36px; background:#7b5a3c; border-radius:20px; cursor:pointer; font-weight:600; transition:0.2s; color:white;}
.upload-btn:hover {background:#5c3b25;}
input[type=file] {display:none;}
.progress-container {width:100%; background:#5c3b25; border-radius:12px; margin-top:20px; overflow:hidden; height:20px; display:none;}
.progress-bar {width:0%; height:100%; background:#d9b08c; transition:0.3s;}
.file-list {margin-top:30px; text-align:left;}
.file-item {background:#3f2d23; padding:12px; margin-bottom:10px; border-radius:16px; display:flex; justify-content:space-between; align-items:center;}
.file-item span {display:flex; align-items:center;}
.file-item i {margin-right:8px;}
a {color:#d9b08c;text-decoration:none;font-weight:600;}
.cat-img {width:100%; max-width:300px; margin-top:30px; border-radius:16px; box-shadow:0 4px 12px rgba(0,0,0,0.4);}
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
<a href="/download/{{ f.id }}"><i class="fas fa-download"></i> Download</a>
<a href="/delete/{{ f.id }}"><i class="fas fa-trash"></i> Delete</a>
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
fileInput.addEventListener("change", async () => {
if(!fileInput.files.length) return;
const file = fileInput.files[0];
const formData = new FormData();
formData.append("file", file);
progressContainer.style.display = "block";
progressBar.style.width = "0%";
const xhr = new XMLHttpRequest();
xhr.open("POST","/",true);
xhr.upload.onprogress = e => {
if(e.lengthComputable){ let percent = (e.loaded / e.total) * 100; progressBar.style.width = percent+"%"; }
}
xhr.onload = () => { progressBar.style.width = "100%"; setTimeout(()=>{location.reload()},500); }
xhr.send(formData);
});
</script>
</body>
</html>"""

CAT_IMAGES = ["https://cataas.com/cat?1","https://cataas.com/cat?2","https://cataas.com/cat?3","https://cataas.com/cat?4","https://cataas.com/cat?5"]

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            db = get_db()
            db.execute("INSERT INTO users (username,password) VALUES (?,?)",(username,password))
            db.commit()
        except:
            return "Username taken"
        return redirect(url_for("login"))
    return '''<form method="post">Username:<input name="username"><br>Password:<input name="password" type="password"><br><button>Register</button></form>'''

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
    return '''<form method="post">Username:<input name="username"><br>Password:<input name="password" type="password"><br><button>Login</button></form>'''

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET","POST"])
@login_required
def index():
    if request.method=="POST":
        f = request.files["file"]
        path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(path)
        db = get_db()
        db.execute("INSERT INTO files (user_id,filename,uploaded) VALUES (?,?,?)",(session["user_id"],f.filename,datetime.utcnow().isoformat()))
        db.commit()
        return "ok"
    db = get_db()
    files = db.execute("SELECT * FROM files WHERE user_id=?",(session["user_id"],)).fetchall()
    cat_url = random.choice(CAT_IMAGES)
    return render_template_string(HTML, files=files, cat_url=cat_url)

@app.route("/download/<int:file_id>")
@login_required
def download(file_id):
    db = get_db()
    f = db.execute("SELECT * FROM files WHERE id=? AND user_id=?",(file_id,session["user_id"])).fetchone()
    if not f: return "Not found"
    return send_file(os.path.join(UPLOAD_DIR,f["filename"]), as_attachment=True)

@app.route("/delete/<int:file_id>")
@login_required
def delete(file_id):
    db = get_db()
    f = db.execute("SELECT * FROM files WHERE id=? AND user_id=?",(file_id,session["user_id"])).fetchone()
    if not f: return "Not found"
    try: os.remove(os.path.join(UPLOAD_DIR,f["filename"]))
    except: pass
    db.execute("DELETE FROM files WHERE id=?",(file_id,))
    db.commit()
    return redirect(url_for("index"))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
