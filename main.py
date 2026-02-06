from flask import Flask, request, render_template_string, send_file
import os, json, random
from datetime import datetime

UPLOAD_DIR = "uploads"
META_FILE = "files.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(META_FILE):
    with open(META_FILE, "w") as f:
        json.dump([], f)

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CatBox</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<style>
body {
    font-family: Inter, sans-serif;
    background: #2b1f16;
    color: #e6d7c3;
    margin:0;
    display:flex;
    flex-direction:column;
    align-items:center;
}
header {
    padding:20px;
    font-size:32px;
    font-weight:700;
    color:#d9b08c;
    text-shadow: 1px 1px #5c3b25;
}
.container {
    max-width:500px;
    width:100%;
    margin-top:40px;
    text-align:center;
}
.upload-btn {
    display:inline-block;
    padding:18px 36px;
    background:#7b5a3c;
    border-radius:20px;
    cursor:pointer;
    font-weight:600;
    transition:0.2s;
    color:white;
}
.upload-btn:hover {
    background:#5c3b25;
}
input[type=file] {
    display:none;
}
.progress-container {
    width:100%;
    background:#5c3b25;
    border-radius:12px;
    margin-top:20px;
    overflow:hidden;
    height:20px;
    display:none;
}
.progress-bar {
    width:0%;
    height:100%;
    background:#d9b08c;
    transition:0.3s;
}
.file-list {
    margin-top:30px;
    text-align:left;
}
.file-item {
    background:#3f2d23;
    padding:12px;
    margin-bottom:10px;
    border-radius:16px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.file-item span {
    display:flex;
    align-items:center;
}
.file-item i {
    margin-right:8px;
}
a {color:#d9b08c;text-decoration:none;font-weight:600;}
.cat-img {
    width:100%;
    max-width:300px;
    margin-top:30px;
    border-radius:16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
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
<a href="/download/{{ loop.index0 }}"><i class="fas fa-download"></i> Download</a>
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

CAT_IMAGES = [
    "https://cataas.com/cat?1",
    "https://cataas.com/cat?2",
    "https://cataas.com/cat?3",
    "https://cataas.com/cat?4",
    "https://cataas.com/cat?5"
]

@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
        f = request.files["file"]
        path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(path)
        with open(META_FILE,"r+") as meta:
            data = json.load(meta)
            data.append({"filename":f.filename,"uploaded":datetime.utcnow().isoformat()})
            meta.seek(0)
            json.dump(data, meta, indent=2)
        return "ok"
    with open(META_FILE) as meta:
        files = json.load(meta)
    cat_url = random.choice(CAT_IMAGES)
    return render_template_string(HTML, files=files, cat_url=cat_url)

@app.route("/download/<int:file_id>")
def download(file_id):
    with open(META_FILE) as meta:
        files = json.load(meta)
    file = files[file_id]
    return send_file(os.path.join(UPLOAD_DIR, file["filename"]), as_attachment=True)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
