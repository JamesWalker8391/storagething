import discord
from discord.ext import commands
from flask import Flask, request, render_template_string, send_file
import asyncio
import threading
import os
import json
import requests
from datetime import datetime

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = 1469381969690234933

UPLOAD_DIR = "uploads"
META_FILE = "files.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists(META_FILE):
    with open(META_FILE, "w") as f:
        json.dump([], f)

# =====================
# DISCORD BOT
# =====================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def send_file_to_discord(filepath, filename):
    channel = bot.get_channel(CHANNEL_ID)
    msg = await channel.send(file=discord.File(filepath, filename))
    meta = {
        "filename": filename,
        "message_id": msg.id,
        "url": msg.attachments[0].url,
        "uploaded": datetime.utcnow().isoformat()
    }
    with open(META_FILE, "r+") as f:
        data = json.load(f)
        data.append(meta)
        f.seek(0)
        json.dump(data, f, indent=2)

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Catbox Clone</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
body {
    font-family: Inter, sans-serif;
    background: #18191c;
    color: #fff;
    margin:0;
    display:flex;
    flex-direction:column;
    align-items:center;
}
header {
    padding:20px;
    font-size:24px;
    font-weight:600;
}
.container {
    max-width:500px;
    width:100%;
    margin-top:50px;
    text-align:center;
}
.upload-btn {
    display:inline-block;
    padding:20px 40px;
    background:#5865f2;
    border-radius:12px;
    cursor:pointer;
    font-weight:600;
    transition:0.2s;
}
.upload-btn:hover {
    background:#4752c4;
}
input[type=file] {
    display:none;
}
.progress-container {
    width:100%;
    background:#2b2d31;
    border-radius:8px;
    margin-top:20px;
    overflow:hidden;
    height:20px;
    display:none;
}
.progress-bar {
    width:0%;
    height:100%;
    background:#57f287;
    transition:0.3s;
}
.file-list {
    margin-top:30px;
    text-align:left;
}
.file-item {
    background:#2b2d31;
    padding:10px;
    margin-bottom:8px;
    border-radius:8px;
    display:flex;
    justify-content:space-between;
}
a {color:#00a8fc;text-decoration:none;}
</style>
</head>
<body>
<header>Catbox Clone</header>
<div class="container">
<label class="upload-btn">Select File
<input type="file" id="fileInput">
</label>
<div class="progress-container">
    <div class="progress-bar" id="progressBar"></div>
</div>
<div class="file-list">
{% for f in files %}
<div class="file-item">
<span>{{ f.filename }}</span>
<a href="/download/{{ loop.index0 }}">Download</a>
</div>
{% else %}
<p>No files yet.</p>
{% endfor %}
</div>
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
        if(e.lengthComputable){
            let percent = (e.loaded / e.total) * 100;
            progressBar.style.width = percent+"%";
        }
    }
    xhr.onload = () => {
        progressBar.style.width = "100%";
        setTimeout(()=>{location.reload()},500);
    }
    xhr.send(formData);
});
</script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method=="POST":
        f = request.files["file"]
        path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(path)
        asyncio.run_coroutine_threadsafe(send_file_to_discord(path,f.filename), bot.loop)
        return "ok"

    with open(META_FILE) as meta:
        files = json.load(meta)
    return render_template_string(HTML, files=files)

@app.route("/download/<int:file_id>")
def download(file_id):
    with open(META_FILE) as meta:
        files = json.load(meta)
    file = files[file_id]
    r = requests.get(file["url"], stream=True)
    local_path = os.path.join(UPLOAD_DIR,file["filename"])
    with open(local_path,"wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
    return send_file(local_path, as_attachment=True)

# =====================
# THREADING
# =====================
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()
bot.run(BOT_TOKEN)
