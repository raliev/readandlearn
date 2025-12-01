import hashlib
import re
import json
import unicodedata
import os
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# --- CONFIGURATION ---
DEFAULT_DICT_FILENAME = 'dictionary.json'
CURRENT_DICTIONARY = {}
FILE_CACHE = {}

# --- HELPER FUNCTIONS ---

def normalize_dict(raw_dict):
    normalized = {}
    for k, v in raw_dict.items():
        clean_key = str(k).lower().strip()
        normalized[clean_key] = v
    return normalized

def load_default_dictionary():
    global CURRENT_DICTIONARY
    if not os.path.exists(DEFAULT_DICT_FILENAME):
        sample_data = {
            "rauf": "A male name",
            "rauf aliev": "A specific person's full name",
            "leesburg": "A town in Virginia, USA",
            "web application": "A program stored on a remote server",
            "python": "A programming language",
            "fragment": "A small part broken or separated off something"
        }
        with open(DEFAULT_DICT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=4)
    
    try:
        with open(DEFAULT_DICT_FILENAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
            CURRENT_DICTIONARY = normalize_dict(data)
    except Exception:
        CURRENT_DICTIONARY = {}

def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def split_into_pages(text, max_chars=1000):
    pages = []
    current_page = []
    current_len = 0
    paragraphs = text.split('\n')
    
    for para in paragraphs:
        para = para.strip()
        if not para: continue
        if current_len + len(para) > max_chars and current_page:
            pages.append("\n".join(current_page))
            current_page = []
            current_len = 0
        if len(para) > max_chars:
            sentences = re.split(r'(?<=[.!?]) +', para)
            for sent in sentences:
                if current_len + len(sent) > max_chars and current_page:
                    pages.append(" ".join(current_page))
                    current_page = []
                    current_len = 0
                current_page.append(sent)
                current_len += len(sent)
        else:
            current_page.append(para)
            current_len += len(para)
    if current_page:
        pages.append("\n".join(current_page))
    return pages

def tokenize_greedy(text):
    # Mark newlines
    text = text.replace('\n', ' ||BR|| ')
    text = re.sub(r'\s+', ' ', text)
    words = text.split(' ')
    
    tokens = []
    n = len(words)
    i = 0
    while i < n:
        if words[i] == '||BR||':
            tokens.append({"text": "", "clickable": False, "newline": True})
            i += 1
            continue

        match_found = False
        for length in range(min(5, n - i), 0, -1):
            phrase_segment = words[i : i + length]
            if '||BR||' in phrase_segment: continue
            
            phrase_str = " ".join(phrase_segment)
            # Basic cleanup
            clean_key = re.sub(r'[^\w\s]', '', phrase_str).lower().strip()
            
            # LOGIC CHANGE: Check exact match first, then fallback to accent-free
            found_key = None
            if clean_key in CURRENT_DICTIONARY:
                found_key = clean_key
            else:
                # Remove accents (e.g. demandés -> demandes)
                normalized = unicodedata.normalize('NFD', clean_key)
                no_accent_key = "".join([c for c in normalized if unicodedata.category(c) != 'Mn'])
                if no_accent_key in CURRENT_DICTIONARY:
                    found_key = no_accent_key

            if found_key:
                tokens.append({
                    "text": phrase_str, 
                    "clickable": True, 
                    "translation": CURRENT_DICTIONARY[found_key]
                })
                i += length
                match_found = True
                break
                
        if not match_found:
            tokens.append({"text": words[i], "clickable": False, "translation": None})
            i += 1
    return tokens

# --- ROUTES ---

@app.route('/')
def index():
    default_filename = 'lepetitprince.txt'
    initial_state = {"hash": None, "totalPages": 0}
    
    # Check if default file exists
    if os.path.exists(default_filename):
        try:
            with open(default_filename, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Process exactly like upload_text
            f_hash = calculate_hash(text)
            pages = split_into_pages(text)
            
            # Store in the global cache immediately
            FILE_CACHE[f_hash] = pages
            
            initial_state = {
                "hash": f_hash, 
                "totalPages": len(pages)
            }
        except Exception as e:
            print(f"Error loading default file: {e}")

    # Pass the initial_state to the template
    return render_template_string(HTML_TEMPLATE, initial_state=initial_state)
@app.route('/upload_text', methods=['POST'])
def upload_text():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']
    text = file.read().decode('utf-8')
    f_hash = calculate_hash(text)
    pages = split_into_pages(text)
    FILE_CACHE[f_hash] = pages
    return jsonify({"hash": f_hash, "total_pages": len(pages)})

@app.route('/upload_dict', methods=['POST'])
def upload_dict():
    global CURRENT_DICTIONARY
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    try:
        data = json.load(request.files['file'])
        CURRENT_DICTIONARY = normalize_dict(data)
        return jsonify({"success": True, "count": len(CURRENT_DICTIONARY)})
    except:
        return jsonify({"error": "Invalid JSON"}), 400

@app.route('/get_page', methods=['POST'])
def get_page():
    data = request.json
    f_hash = data.get('hash')
    page_idx = int(data.get('page', 0))
    if f_hash not in FILE_CACHE: return jsonify({"error": "Session expired"}), 404
    pages = FILE_CACHE[f_hash]
    if page_idx < 0 or page_idx >= len(pages): return jsonify({"error": "Invalid page"}), 400
    return jsonify({"page_idx": page_idx, "tokens": tokenize_greedy(pages[page_idx])})

# --- TEMPLATE ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reader App</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-light: #eff6ff;
            --bg-color: #f8fafc;
            --sidebar-bg: #ffffff;
            --text-color: #1e293b;
            --border-color: #e2e8f0;
            --success: #22c55e;
            --danger: #ef4444;
        }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0; 
            height: 100vh; 
            display: flex; 
            color: var(--text-color);
            background-color: var(--bg-color);
            overflow: hidden;
        }

        /* --- LAYOUT --- */
        #main-container { 
            flex: 3; 
            padding: 30px 40px; 
            overflow-y: auto; 
            display: flex; 
            flex-direction: column;
            transition: opacity 0.3s;
        }
        
        #sidebar { 
            flex: 1; 
            background: var(--sidebar-bg); 
            border-left: 1px solid var(--border-color); 
            display: flex; 
            flex-direction: column; 
            padding: 20px;
            box-shadow: -2px 0 10px rgba(0,0,0,0.02);
            transition: all 0.3s ease;
            z-index: 10;
        }

        /* --- STUDY MODE STATES --- */
        body.study-mode #main-container {
            display: none; /* Hide main text */
        }

        body.study-mode #sidebar {
            width: 100vw; /* Take full width */
            flex: none;
            border: none;
            background: var(--bg-color); /* Matches page bg */
            padding: 40px;
            align-items: center;
        }

        /* --- TEXT DISPLAY --- */
        #text-display { 
            line-height: 1.8; 
            font-size: 1.15rem; 
            max-width: 800px; 
            margin: 0 auto; 
            text-align: justify; 
        }

        .token { 
            padding: 2px 1px; 
            margin: 0 1px; 
            border-radius: 3px; 
            display: inline-block; 
        }
        
        .token.clickable { 
            // border-bottom: 2px solid var(--primary); 
            color: inherit; 
            font-weight: 500;
            cursor: pointer; 
            transition: background 0.2s;
        }
        .token.clickable:hover { 
            background-color: var(--primary-light); 
        }

        /* --- CONTROLS --- */
        .controls-group {
            background: var(--sidebar-bg);
            border: 1px solid var(--border-color);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        
        h4 { margin: 0 0 10px 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; color: #64748b; }
        
        .btn {
            background: var(--text-color);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.9; }
        .btn-green { background: var(--success); }
        
        .nav-controls {
            display: none;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin: 20px 0;
            padding: 10px;
            background: white;
            border-radius: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
        }
        
        input[type="file"] { font-size: 0.9rem; width: 180px; }

        /* --- SIDEBAR LIST VIEW --- */
        #list-view {
            display: flex; 
            flex-direction: column; 
            flex-grow: 1;
        }
        
        #word-list { 
            list-style: none; 
            padding: 0; 
            margin-top: 10px; 
            overflow-y: auto; 
            flex-grow: 1;
        }
        
        #word-list li { 
            background: var(--primary-light);
            color: var(--primary);
            margin-bottom: 8px; 
            padding: 10px 15px; 
            border-radius: 6px; 
            font-weight: 500;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* --- TRANSLATION VIEW (FULL SCREEN) --- */
        #translation-view { 
            display: none; 
            width: 100%;
            max-width: 900px;
            flex-direction: column;
            height: 100%;
        }

        #translation-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            padding-bottom: 80px; /* Space for FAB */
            overflow-y: auto;
            width: 100%;
        }

        .trans-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
            transition: transform 0.2s;
        }
        .trans-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        .trans-term { font-size: 1.5rem; font-weight: 700; color: var(--text-color); margin-bottom: 10px; }
        .trans-def { font-size: 1.1rem; color: #64748b; font-style: italic; line-height: 1.5; }

        /* --- FLOATING BUTTONS --- */
        .fab-container {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 100;
            display: flex;
            gap: 15px;
        }

        .btn-pill {
            padding: 12px 30px;
            border-radius: 50px;
            font-weight: 600;
            font-size: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            cursor: pointer;
            border: none;
            transition: transform 0.2s;
        }
        .btn-pill:hover { transform: scale(1.05); }
        
        .btn-study { background: var(--primary); color: white; width: 100%; margin-top: 10px; border-radius: 8px;}
        .btn-close { background: var(--text-color); color: white; display: none; } /* Hidden by default */

    </style>
</head>
<body>

    <div id="main-container">
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
            <div class="controls-group">
                <h4>1. Text File</h4>
                <input type="file" id="text-input" accept=".txt">
                <button class="btn" onclick="uploadText()">Load</button>
            </div>

            <div class="controls-group">
                <h4>2. Dictionary</h4>
                <input type="file" id="dict-input" accept=".json">
                <button class="btn" onclick="uploadDict()">Load</button>
                <div id="dict-status" style="font-size: 12px; margin-top: 5px; color: #64748b;">Default Loaded</div>
            </div>
        </div>
        
        <div class="nav-controls" id="nav-area">
            <button class="btn" onclick="changePage(-1)">← Prev</button>
            <span style="font-weight: 600; color: #64748b; font-size: 0.9rem;">
                Page <input type="number" id="page-num" value="1" style="width: 40px; text-align: center; border: 1px solid #ccc; border-radius: 4px;" onchange="jumpToPage()"> 
                of <span id="total-pages">0</span>
            </span>
            <button class="btn" onclick="changePage(1)">Next →</button>
        </div>
        
        <div id="text-display">
            <div style="text-align: center; color: #94a3b8; margin-top: 50px;">
                Please upload a text file to begin reading.
            </div>
        </div>
    </div>

    <div id="sidebar">
        
        <div id="list-view">
            <h3 style="margin: 0 0 15px 0; color: var(--text-color);">Selected Words</h3>
            <div style="color: #94a3b8; font-size: 0.9rem; text-align: center;" id="empty-msg">
                Click blue words in the text to add them here.
            </div>
            <ul id="word-list"></ul>
            <div style="margin-top: auto;">
                <button class="btn btn-study" onclick="showTranslation()">Start Study Session</button>
            </div>
        </div>

        <div id="translation-view">
            <h2 style="text-align: center; margin-bottom: 30px;">Review Translations</h2>
            <div id="translation-grid"></div>
        </div>

    </div>

    <div class="fab-container">
        <button id="close-btn" class="btn-pill btn-close" onclick="closeTranslation()">
            Done / Close
        </button>
    </div>

    <script>
        const startData = {{ initial_state | tojson }}; 
        
        let currentHash = startData.hash;
        let totalPages = startData.totalPages;
        let currentPage = 0;
        let selectedWords = []; 

        load_default_dictionary();

        function init() {
            if (currentHash) {
                document.getElementById('total-pages').innerText = totalPages;
                document.getElementById('nav-area').style.display = 'flex';
                
                // Remove the "Please upload" message
                document.getElementById('text-display').innerText = '';
                
                // Check if we have a saved position for this specific file, otherwise 0
                const savedPage = localStorage.getItem(`reader_pos_${currentHash}`);
                currentPage = savedPage ? parseInt(savedPage) : 0;
                
                loadPage(currentPage);
            }
        }

        async function uploadText() {
            const fileInput = document.getElementById('text-input');
            if (fileInput.files.length === 0) return alert("Select a text file");
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            const res = await fetch('/upload_text', { method: 'POST', body: formData });
            const data = await res.json();
            currentHash = data.hash;
            totalPages = data.total_pages;
            
            document.getElementById('total-pages').innerText = totalPages;
            document.getElementById('nav-area').style.display = 'flex';
            
            const savedPage = localStorage.getItem(`reader_pos_${currentHash}`);
            currentPage = savedPage ? parseInt(savedPage) : 0;
            loadPage(currentPage);
        }

        init();

        async function uploadDict() {
            const fileInput = document.getElementById('dict-input');
            if (fileInput.files.length === 0) return alert("Select a JSON dictionary");
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            try {
                const res = await fetch('/upload_dict', { method: 'POST', body: formData });
                const data = await res.json();
                if(data.error) throw new Error(data.error);
                document.getElementById('dict-status').innerText = `Custom (${data.count} terms)`;
                document.getElementById('dict-status').style.color = "var(--success)";
                if (currentHash) loadPage(currentPage);
            } catch(e) { alert("Error uploading dictionary"); }
        }

        async function loadPage(idx) {
            if (idx < 0 || idx >= totalPages) return;
            currentPage = idx;
            document.getElementById('page-num').value = currentPage + 1;
            if(currentHash) localStorage.setItem(`reader_pos_${currentHash}`, currentPage);
            
            const res = await fetch('/get_page', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ hash: currentHash, page: currentPage })
            });
            const data = await res.json();
            if(data.error) return alert(data.error);
            renderTokens(data.tokens);
        }

        function changePage(delta) { loadPage(currentPage + delta); }
        function jumpToPage() { loadPage(parseInt(document.getElementById('page-num').value) - 1); }

        function renderTokens(tokens) {
            const container = document.getElementById('text-display');
            container.innerHTML = '';
            tokens.forEach(token => {
                // Handle newlines
                if (token.newline) {
                    container.appendChild(document.createElement('br'));
                    return;
                }

                const span = document.createElement('span');
                span.innerText = token.text;
                span.classList.add('token');
                
                if (token.clickable) {
                    span.classList.add('clickable');
                    span.onclick = () => addWordToList(token.text, token.translation);
                }
                
                container.appendChild(span);
                // Add a space after words, unless it's the end of a line
                container.appendChild(document.createTextNode(' ')); 
            });
        }

        function addWordToList(text, translation) {
            document.getElementById('empty-msg').style.display = 'none';
            if(selectedWords.some(w => w.text === text)) return;
            selectedWords.push({ text, translation });
            renderList();
        }

        function renderList() {
            const list = document.getElementById('word-list');
            list.innerHTML = '';
            selectedWords.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${item.text}</span> <span style="font-size:1.2em">›</span>`;
                list.appendChild(li);
            });
        }

        function showTranslation() {
            if (selectedWords.length === 0) return alert("Select some words first!");

            // 1. Enter Study Mode (CSS handles layout changes)
            document.body.classList.add('study-mode');

            // 2. Hide Sidebar List View, Show Grid View
            document.getElementById('list-view').style.display = 'none';
            document.getElementById('translation-view').style.display = 'flex';
            document.getElementById('close-btn').style.display = 'block';

            // 3. Render Cards
            const grid = document.getElementById('translation-grid');
            grid.innerHTML = '';
            selectedWords.forEach(item => {
                const div = document.createElement('div');
                div.className = 'trans-card';
                div.innerHTML = `
                    <div class="trans-term">${item.text}</div>
                    <div class="trans-def">${item.translation}</div>
                `;
                grid.appendChild(div);
            });
        }

        function closeTranslation() {
            // 1. Exit Study Mode
            document.body.classList.remove('study-mode');
            
            // 2. Reset Views
            document.getElementById('translation-view').style.display = 'none';
            document.getElementById('list-view').style.display = 'flex';
            document.getElementById('close-btn').style.display = 'none';
            document.getElementById('empty-msg').style.display = 'block';

            // 3. Clear Data
            selectedWords = [];
            renderList();
        }

        function load_default_dictionary() {
            // Placeholder logic for UI init
        }
    </script>
</body>
</html>
"""

load_default_dictionary()

if __name__ == '__main__':
    app.run(debug=True, port=5000)