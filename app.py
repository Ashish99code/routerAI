# AI API/app.py
from fastapi import FastAPI, HTTPException, Query, Request, Response, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import openai
import os
import json
from dotenv import load_dotenv

ADMIN_PASSWORD = "admin123"  # Hardcoded for now
MODELS_FILE = "allowed_models.json"
API_KEYS_FILE = "api_keys.json"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")

# Helper functions for models

def load_models():
    with open(MODELS_FILE, "r") as f:
        return json.load(f)

def save_models(models):
    with open(MODELS_FILE, "w") as f:
        json.dump(models, f, indent=2)

def load_api_keys():
    with open(API_KEYS_FILE, "r") as f:
        return json.load(f)

def save_api_keys(keys):
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

# Allowlist of models the frontend can use
ALLOWED_MODELS = {
    "mistralai/mixtral-8x7b-instruct",
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat-v3-0324:free", 
    "google/gemini-2.5-pro-exp-03-25",
    "google/gemma-3n-e4b-it:free",
    "deepseek/deepseek-r1:free",
    "google/gemini-2.0-flash-exp:free",
    "tngtech/deepseek-r1t-chimera:free",
    "deepseek/deepseek-chat:free",
    "meta-llama/llama-4-maverick:free",
    "qwen/qwen3-235b-a22b:free",
    "microsoft/mai-ds-r1:free",
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-r1-distill-llama-70b:free",
    "deepseek/deepseek-prover-v2:free",
    "mistralai/mistral-nemo:free",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
    "qwen/qwq-32b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "meta-llama/llama-4-maverick:free",
    "microsoft/mai-ds-r1:free",
    "deepseek/deepseek-r1-distill-llama-70b:free",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
    "qwen/qwq-32b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-4-scout:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen3-14b:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "qwen/qwen3-30b-a3b:free",
    "deepseek/deepseek-r1-distill-qwen-32b:free",
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-r1:online",
    "google/gemma-3-12b-it:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "thudm/glm-z1-32b:free",
    "nvidia/llama-3.3-nemotron-super-49b-v1:free",
    "agentica-org/deepcoder-14b-preview:free",
    "microsoft/phi-4-reasoning-plus:free",
    "qwen/qwen3-8b:free",
    "open-r1/olympiccoder-32b:free",# Your new model
    # Add other free models from OpenRouter here
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenRouter client
load_dotenv()
client = openai.AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Dependency for admin session

def require_admin(request: Request):
    if not request.session.get("admin_logged_in"):
        raise HTTPException(status_code=401, detail="Not authenticated")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not request.session.get("admin_logged_in"):
        return HTMLResponse("""
        <html><head><title>Admin Login</title>
        <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7fa; }
        .centered { max-width: 400px; margin: 80px auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 24px #0001; padding: 2rem; }
        input[type=password], button { font-size: 1.1rem; padding: 0.7rem; border-radius: 7px; border: 1px solid #bbb; margin-bottom: 1rem; width: 100%; }
        button { background: #3ba9f6; color: #fff; border: none; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #238ad3; }
        </style></head><body>
        <div class='centered'>
        <h2 style='text-align:center;'>Admin Login</h2>
        <form method='post' action='/admin/login'>
            <input type='password' name='password' placeholder='Password' required />
            <button type='submit'>Login</button>
        </form>
        </div></body></html>
        """)
    models = load_models()
    models_json = json.dumps(models)
    return HTMLResponse(f"""
    <html><head><title>Admin Dashboard</title>
    <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7fa; }}
    .container {{ max-width: 800px; margin: 40px auto; background: #fff; border-radius: 14px; box-shadow: 0 4px 24px #0001; padding: 2.5rem; }}
    h2 {{ text-align:center; color: #3ba9f6; margin-bottom: 2rem; }}
    .search-bar {{ margin-bottom: 1.5rem; display: flex; gap: 1rem; }}
    .search-bar input {{ flex: 1; font-size: 1.05rem; padding: 0.7rem; border-radius: 7px; border: 1px solid #bbb; }}
    .add-form {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
    .add-form input {{ flex: 1; font-size: 1.05rem; padding: 0.7rem; border-radius: 7px; border: 1px solid #bbb; }}
    .add-form button {{ background: #3ba9f6; color: #fff; border: none; border-radius: 7px; padding: 0.7rem 1.5rem; font-size: 1.05rem; cursor: pointer; transition: background 0.2s; }}
    .add-form button:hover {{ background: #238ad3; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; }}
    th, td {{ padding: 0.8rem 1rem; border-bottom: 1px solid #e3e8ee; text-align: left; }}
    th {{ background: #f0f6fa; color: #3ba9f6; font-size: 1.08rem; }}
    tr:last-child td {{ border-bottom: none; }}
    .edit-btn, .delete-btn, .save-btn, .cancel-btn {{ border: none; border-radius: 7px; padding: 0.5rem 1.1rem; font-size: 1rem; cursor: pointer; transition: background 0.2s; margin-right: 0.3rem; }}
    .edit-btn {{ background: #6366f1; color: #fff; }}
    .edit-btn:hover {{ background: #3730a3; }}
    .delete-btn {{ background: #ef4444; color: #fff; }}
    .delete-btn:hover {{ background: #b91c1c; }}
    .save-btn {{ background: #10b981; color: #fff; }}
    .save-btn:hover {{ background: #059669; }}
    .cancel-btn {{ background: #bbb; color: #fff; }}
    .cancel-btn:hover {{ background: #888; }}
    .logout-btn {{ background: #3ba9f6; color: #fff; border: none; border-radius: 7px; padding: 0.7rem 1.5rem; font-size: 1.05rem; cursor: pointer; float: right; margin-top: 1.5rem; transition: background 0.2s; }}
    .logout-btn:hover {{ background: #238ad3; }}
    .success-msg {{ color: #10b981; margin-bottom: 1rem; font-weight: 500; }}
    .error-msg {{ color: #ef4444; margin-bottom: 1rem; font-weight: 500; }}
    .pagination {{ display: flex; justify-content: center; gap: 0.5rem; margin-bottom: 1.5rem; }}
    .pagination button {{ background: #f0f6fa; color: #3ba9f6; border: none; border-radius: 6px; padding: 0.5rem 1.1rem; font-size: 1rem; cursor: pointer; transition: background 0.2s; }}
    .pagination button.active, .pagination button:hover {{ background: #3ba9f6; color: #fff; }}
    @media (max-width: 600px) {{ .container {{ padding: 1rem; }} th, td {{ padding: 0.5rem 0.4rem; }} }}
    </style></head><body>
    <div class='container'>
    <h2>Admin Dashboard</h2>
    <div class='search-bar'>
        <input type='text' id='searchInput' placeholder='Search models...' oninput='renderTable()' />
    </div>
    <form class='add-form' id='addModelForm' onsubmit='return false;'>
        <input type='text' id='newModel' placeholder='Add new model...' required />
        <button type='submit'>Add Model</button>
    </form>
    <div id='msg'></div>
    <div id='tableContainer'></div>
    <div class='pagination' id='pagination'></div>
    <button class='logout-btn' onclick="logout()">Logout</button>
    </div>
    <script>
    let models = {models_json};
    let editIdx = -1;
    let searchTerm = '';
    let page = 1;
    const pageSize = 8;
    const msgDiv = document.getElementById('msg');
    document.getElementById('addModelForm').onsubmit = async function() {{
        const model = document.getElementById('newModel').value.trim();
        if (!model) return;
        if (models.some(m => m.toLowerCase() === model.toLowerCase())) {{
            msgDiv.innerHTML = `<span class='error-msg'>Model name already exists (case-insensitive).</span>`;
            return;
        }}
        const res = await fetch('/admin/models', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{model}})}});
        if (res.ok) {{
            msgDiv.innerHTML = '<span class="success-msg">Model added successfully!</span>';
            setTimeout(()=>location.reload(), 800);
        }} else {{
            const data = await res.json();
            msgDiv.innerHTML = `<span class='error-msg'>${{data.detail || 'Error adding model.'}}</span>`;
        }}
    }};
    function renderTable() {{
        searchTerm = document.getElementById('searchInput').value.trim().toLowerCase();
        let filtered = models.filter(m => m.toLowerCase().includes(searchTerm));
        let totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
        if (page > totalPages) page = totalPages;
        let start = (page-1)*pageSize, end = start+pageSize;
        let rows = filtered.slice(start, end).map((m, i) => {{
            let idx = models.indexOf(m);
            if (editIdx === idx) {{
                return `<tr><td><input id='editInput' value='${{m}}' style='width:90%' /></td><td>
                <button class='save-btn' onclick='saveEdit(${{idx}})'>Save</button>
                <button class='cancel-btn' onclick='cancelEdit()'>Cancel</button></td></tr>`;
            }} else {{
                return `<tr><td>${{m}}</td><td>
                <button class='edit-btn' onclick='editModel(${{idx}})'>Edit</button>
                <button class='delete-btn' onclick='deleteModel(${{idx}})'>Delete</button></td></tr>`;
            }}
        }}).join('');
        document.getElementById('tableContainer').innerHTML = `<table><thead><tr><th>Model Name</th><th style='width:160px;'>Action</th></tr></thead><tbody>${{rows}}</tbody></table>`;
        // Pagination
        let pagBtns = '';
        for (let i=1; i<=totalPages; ++i) pagBtns += `<button class='${{i===page?'active':''}}' onclick='gotoPage(${{i}})'>${{i}}</button>`;
        document.getElementById('pagination').innerHTML = pagBtns;
    }}
    function gotoPage(p) {{ page = p; renderTable(); }}
    function editModel(idx) {{ editIdx = idx; renderTable(); }}
    function cancelEdit() {{ editIdx = -1; renderTable(); }}
    async function saveEdit(idx) {{
        const newVal = document.getElementById('editInput').value.trim();
        if (!newVal) {{ msgDiv.innerHTML = `<span class='error-msg'>Model name cannot be empty.</span>`; return; }}
        if (models.some(m => m.toLowerCase() === newVal.toLowerCase() && models.indexOf(m) !== idx)) {{ msgDiv.innerHTML = `<span class='error-msg'>Duplicate model name (case-insensitive).</span>`; return; }}
        // Remove old, add new
        const delRes = await fetch('/admin/models', {{method:'DELETE',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{model:models[idx]}})}});
        if (!delRes.ok) {{ msgDiv.innerHTML = `<span class='error-msg'>Error editing model.</span>`; return; }}
        const addRes = await fetch('/admin/models', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{model:newVal}})}});
        if (addRes.ok) {{
            msgDiv.innerHTML = '<span class="success-msg">Model updated!</span>';
            setTimeout(()=>location.reload(), 800);
        }} else {{
            msgDiv.innerHTML = `<span class='error-msg'>Error editing model.</span>`;
        }}
    }}
    async function deleteModel(idx) {{
        if (!confirm('Delete this model?')) return;
        const res = await fetch('/admin/models', {{method:'DELETE',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{model:models[idx]}})}});
        if (res.ok) {{
            msgDiv.innerHTML = '<span class="success-msg">Model deleted.</span>';
            setTimeout(()=>location.reload(), 800);
        }} else {{
            const data = await res.json();
            msgDiv.innerHTML = `<span class='error-msg'>${{data.detail || 'Error deleting model.'}}</span>`;
        }}
    }}
    async function logout() {{
        await fetch('/admin/logout', {{method:'POST'}});
        location.reload();
    }}
    window.renderTable = renderTable;
    window.editModel = editModel;
    window.cancelEdit = cancelEdit;
    window.saveEdit = saveEdit;
    window.deleteModel = deleteModel;
    window.gotoPage = gotoPage;
    renderTable();
    </script>
    <div class='container'>
    <h2>API Key Management</h2>
    <div class='search-bar'>
        <input type='text' id='apiKeySearchInput' placeholder='Search API keys...' oninput='renderApiKeyTable()' />
    </div>
    <form class='add-form' id='addApiKeyForm' onsubmit='return false;'>
        <input type='text' id='newApiKey' placeholder='Add new API key...' required />
        <input type='text' id='newApiKeyOwner' placeholder='Owner' />
        <input type='text' id='newApiKeyNote' placeholder='Note' />
        <button type='submit'>Add API Key</button>
    </form>
    <div id='apiKeyMsg'></div>
    <div id='apiKeyTableContainer'></div>
    <div class='pagination' id='apiKeyPagination'></div>
    </div>
    <script>
    let apiKeys = [];
    let apiKeyEditIdx = -1;
    let apiKeySearchTerm = '';
    let apiKeyPage = 1;
    const apiKeyPageSize = 8;
    const apiKeyMsgDiv = document.getElementById('apiKeyMsg');
    document.getElementById('addApiKeyForm').onsubmit = async function() {{
        const key = document.getElementById('newApiKey').value.trim();
        const owner = document.getElementById('newApiKeyOwner').value.trim();
        const note = document.getElementById('newApiKeyNote').value.trim();
        if (!key) return;
        if (apiKeys.some(k => k.key.toLowerCase() === key.toLowerCase())) {{
            apiKeyMsgDiv.innerHTML = `<span class='error-msg'>API key already exists (case-insensitive).</span>`;
            return;
        }}
        const res = await fetch('/admin/api-keys', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{key, owner, note, active: true}})}});
        if (res.ok) {{
            apiKeyMsgDiv.innerHTML = '<span class="success-msg">API key added successfully!</span>';
            setTimeout(()=>location.reload(), 800);
        }} else {{
            const data = await res.json();
            apiKeyMsgDiv.innerHTML = `<span class='error-msg'>${{data.detail || 'Error adding API key.'}}</span>`;
        }}
    }};
    async function loadApiKeys() {{
        const res = await fetch('/admin/api-keys');
        if (res.ok) {{
            apiKeys = await res.json();
            renderApiKeyTable();
        }} else {{
            apiKeyMsgDiv.innerHTML = `<span class='error-msg'>Error loading API keys.</span>`;
        }}
    }}
    function renderApiKeyTable() {{
        apiKeySearchTerm = document.getElementById('apiKeySearchInput').value.trim().toLowerCase();
        let filtered = apiKeys.filter(k => k.key.toLowerCase().includes(apiKeySearchTerm) || k.owner.toLowerCase().includes(apiKeySearchTerm));
        let totalPages = Math.max(1, Math.ceil(filtered.length / apiKeyPageSize));
        if (apiKeyPage > totalPages) apiKeyPage = totalPages;
        let start = (apiKeyPage-1)*apiKeyPageSize, end = start+apiKeyPageSize;
        let rows = filtered.slice(start, end).map((k, i) => {{
            let idx = apiKeys.indexOf(k);
            if (apiKeyEditIdx === idx) {{
                return `<tr><td><input id='editApiKeyInput' value='${{k.key}}' style='width:90%' /></td><td><input id='editApiKeyOwnerInput' value='${{k.owner}}' style='width:90%' /></td><td><input id='editApiKeyNoteInput' value='${{k.note}}' style='width:90%' /></td><td>
                <button class='save-btn' onclick='saveApiKeyEdit(${{idx}})'>Save</button>
                <button class='cancel-btn' onclick='cancelApiKeyEdit()'>Cancel</button></td></tr>`;
            }} else {{
                return `<tr><td>${{k.key}}</td><td>${{k.owner}}</td><td>${{k.note}}</td><td>
                <label class='switch'><input type='checkbox' ${{k.active ? 'checked' : ''}} onchange='toggleApiKeyStatus(${{idx}})' /><span class='slider round'></span></label></td><td>
                <button class='edit-btn' onclick='editApiKey(${{idx}})'>Edit</button>
                <button class='delete-btn' onclick='deleteApiKey(${{idx}})'>Delete</button></td></tr>`;
            }}
        }}).join('');
        document.getElementById('apiKeyTableContainer').innerHTML = `<table><thead><tr><th>API Key</th><th>Owner</th><th>Note</th><th>Status</th><th style='width:160px;'>Action</th></tr></thead><tbody>${{rows}}</tbody></table>`;
        // Pagination
        let pagBtns = '';
        for (let i=1; i<=totalPages; ++i) pagBtns += `<button class='${{i===apiKeyPage?'active':''}}' onclick='gotoApiKeyPage(${{i}})'>${{i}}</button>`;
        document.getElementById('apiKeyPagination').innerHTML = pagBtns;
    }}
    function gotoApiKeyPage(p) {{ apiKeyPage = p; renderApiKeyTable(); }}
    function editApiKey(idx) {{ apiKeyEditIdx = idx; renderApiKeyTable(); }}
    function cancelApiKeyEdit() {{ apiKeyEditIdx = -1; renderApiKeyTable(); }}
    async function saveApiKeyEdit(idx) {{
        const newKey = document.getElementById('editApiKeyInput').value.trim();
        const newOwner = document.getElementById('editApiKeyOwnerInput').value.trim();
        const newNote = document.getElementById('editApiKeyNoteInput').value.trim();
        if (!newKey) {{ apiKeyMsgDiv.innerHTML = `<span class='error-msg'>API key cannot be empty.</span>`; return; }}
        if (apiKeys.some(k => k.key.toLowerCase() === newKey.toLowerCase() && apiKeys.indexOf(k) !== idx)) {{ apiKeyMsgDiv.innerHTML = `<span class='error-msg'>Duplicate API key (case-insensitive).</span>`; return; }}
        const res = await fetch('/admin/api-keys', {{method:'PUT',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{key:newKey, owner:newOwner, note:newNote, active:apiKeys[idx].active}})}});
        if (res.ok) {{
            apiKeyMsgDiv.innerHTML = '<span class="success-msg">API key updated!</span>';
            setTimeout(()=>location.reload(), 800);
        }} else {{
            apiKeyMsgDiv.innerHTML = `<span class='error-msg'>Error updating API key.</span>`;
        }}
    }}
    async function toggleApiKeyStatus(idx) {{
        const newStatus = !apiKeys[idx].active;
        const res = await fetch('/admin/api-keys', {{method:'PUT',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{key:apiKeys[idx].key, active:newStatus}})}});
        if (res.ok) {{
            apiKeys[idx].active = newStatus;
            apiKeyMsgDiv.innerHTML = `<span class="success-msg">API key status updated to ${{newStatus ? 'active' : 'inactive'}}.</span>`;
        }} else {{
            apiKeyMsgDiv.innerHTML = `<span class='error-msg'>Error updating API key status.</span>`;
        }}
    }}
    async function deleteApiKey(idx) {{
        if (!confirm('Delete this API key?')) return;
        const res = await fetch('/admin/api-keys', {{method:'DELETE',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{key:apiKeys[idx].key}})}});
        if (res.ok) {{
            apiKeyMsgDiv.innerHTML = '<span class="success-msg">API key deleted.</span>';
            setTimeout(()=>location.reload(), 800);
        }} else {{
            const data = await res.json();
            apiKeyMsgDiv.innerHTML = `<span class='error-msg'>${{data.detail || 'Error deleting API key.'}}</span>`;
        }}
    }}
    window.renderApiKeyTable = renderApiKeyTable;
    window.editApiKey = editApiKey;
    window.cancelApiKeyEdit = cancelApiKeyEdit;
    window.saveApiKeyEdit = saveApiKeyEdit;
    window.deleteApiKey = deleteApiKey;
    window.gotoApiKeyPage = gotoApiKeyPage;
    window.toggleApiKeyStatus = toggleApiKeyStatus;
    loadApiKeys();
    </script>
    <style>
    .switch {{
        position: relative;
        display: inline-block;
        width: 60px;
        height: 34px;
    }}
    .switch input {{
        opacity: 0;
        width: 0;
        height: 0;
    }}
    .slider {{
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
    }}
    .slider:before {{
        position: absolute;
        content: "";
        height: 26px;
        width: 26px;
        left: 4px;
        bottom: 4px;
        background-color: white;
        transition: .4s;
    }}
    input:checked + .slider {{
        background-color: #2196F3;
    }}
    input:checked + .slider:before {{
        transform: translateX(26px);
    }}
    .slider.round {{
        border-radius: 34px;
    }}
    .slider.round:before {{
        border-radius: 50%;
    }}
    </style>
    </body></html>
    """)

@app.post("/admin/login")
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["admin_logged_in"] = True
        return RedirectResponse("/admin", status_code=302)
    return HTMLResponse("<h3>Login failed</h3><a href='/admin'>Try again</a>")

@app.post("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return Response(status_code=204)

@app.get("/admin/models")
async def get_models(request: Request, admin: None = Depends(require_admin)):
    return load_models()

@app.post("/admin/models")
async def add_model(request: Request, data: dict, admin: None = Depends(require_admin)):
    models = load_models()
    model = data.get("model")
    if not model or model in models:
        raise HTTPException(status_code=400, detail="Invalid or duplicate model")
    models.append(model)
    save_models(models)
    return {"success": True}

@app.delete("/admin/models")
async def delete_model(request: Request, data: dict, admin: None = Depends(require_admin)):
    models = load_models()
    model = data.get("model")
    if not model or model not in models:
        raise HTTPException(status_code=400, detail="Model not found")
    models.remove(model)
    save_models(models)
    return {"success": True}

@app.get("/admin/api-keys")
async def get_api_keys(request: Request, admin: None = Depends(require_admin)):
    return load_api_keys()

@app.post("/admin/api-keys")
async def add_api_key(request: Request, data: dict, admin: None = Depends(require_admin)):
    keys = load_api_keys()
    key = data.get("key")
    owner = data.get("owner", "")
    note = data.get("note", "")
    if not key or any(k["key"] == key for k in keys):
        raise HTTPException(status_code=400, detail="Invalid or duplicate key")
    keys.append({"key": key, "owner": owner, "active": True, "note": note})
    save_api_keys(keys)
    return {"success": True}

@app.put("/admin/api-keys")
async def update_api_key(request: Request, data: dict, admin: None = Depends(require_admin)):
    keys = load_api_keys()
    key = data.get("key")
    for k in keys:
        if k["key"] == key:
            k["owner"] = data.get("owner", k["owner"])
            k["note"] = data.get("note", k["note"])
            k["active"] = data.get("active", k["active"])
            save_api_keys(keys)
            return {"success": True}
    raise HTTPException(status_code=404, detail="Key not found")

@app.delete("/admin/api-keys")
async def delete_api_key(request: Request, data: dict, admin: None = Depends(require_admin)):
    keys = load_api_keys()
    key = data.get("key")
    new_keys = [k for k in keys if k["key"] != key]
    if len(new_keys) == len(keys):
        raise HTTPException(status_code=404, detail="Key not found")
    save_api_keys(new_keys)
    return {"success": True}

@app.post("/api/generate")
async def generate_text(
    prompt: str = Query(...),
    model: str = Query("deepseek/deepseek-r1:free"),
    apikey: str = Query(...),
    worktype: str = Query(""),
    from_: str = Query("", alias="from")
):
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    allowed_models = set(load_models())
    if model not in allowed_models:
        raise HTTPException(
            status_code=403,
            detail=f"Model '{model}' is not allowed. Choose from: {list(allowed_models)}"
        )
    # API key validation
    api_keys = load_api_keys()
    key_obj = next((k for k in api_keys if k["key"] == apikey and k["active"]), None)
    if not key_obj:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    # Optionally: log worktype/from_/apikey usage here
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))