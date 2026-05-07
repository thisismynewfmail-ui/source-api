#!/usr/bin/env python3
"""AutoType v1.02 — python start.py"""
import json,re,threading,webbrowser,time,sys,os,uuid,glob,socket
from datetime import datetime

try:
    from flask import Flask,render_template,request,jsonify,Response,stream_with_context,send_from_directory
except ImportError:
    os.system(f"{sys.executable} -m pip install flask requests --quiet")
    from flask import Flask,render_template,request,jsonify,Response,stream_with_context,send_from_directory
try: import requests as R
except ImportError:
    os.system(f"{sys.executable} -m pip install requests --quiet"); import requests as R

BASE=os.path.dirname(os.path.abspath(__file__))
app=Flask(__name__)
DATA=os.path.join(BASE,"data");PRESETS=os.path.join(DATA,"presets");CHATS=os.path.join(DATA,"chats")
ACTIVE_ID_P=os.path.join(DATA,"active_id.txt");CUSTOM_P=os.path.join(DATA,"customization.json")
IMAGES=os.path.join(BASE,"images")
for d in [PRESETS,CHATS,IMAGES,os.path.join(DATA,"memory")]: os.makedirs(d,exist_ok=True)

_ltm=None
def get_ltm():
    global _ltm
    if _ltm is None:
        try: from memory import LongTermMemory; _ltm=LongTermMemory()
        except ImportError:
            os.system(f"{sys.executable} -m pip install sentence-transformers --quiet --break-system-packages 2>/dev/null || {sys.executable} -m pip install sentence-transformers --quiet")
            from memory import LongTermMemory; _ltm=LongTermMemory()
    return _ltm

TP=["qwen3","deepseek-r1","qwq","gpt-oss","o1","o3","omnibrain"]
# OpenAI-compatible parameters. Sent at top level of /v1/chat/completions.
# Most servers (text-generation-webui, llama-server, vLLM, KoboldCpp) accept
# these extras alongside the OpenAI core (temperature, top_p, max_tokens, ...).
PD={
 "temperature":{"type":"float","default":0.8,"min":0.0,"max":2.0,"step":0.05,"cat":"sampling","desc":"Randomness"},
 "top_k":{"type":"int","default":40,"min":0,"max":200,"step":1,"cat":"sampling","desc":"Token pool"},
 "top_p":{"type":"float","default":0.9,"min":0.0,"max":1.0,"step":0.05,"cat":"sampling","desc":"Nucleus"},
 "min_p":{"type":"float","default":0.0,"min":0.0,"max":1.0,"step":0.01,"cat":"sampling","desc":"Min prob"},
 "typical_p":{"type":"float","default":1.0,"min":0.0,"max":1.0,"step":0.05,"cat":"sampling","desc":"Typical"},
 "tfs":{"type":"float","default":1.0,"min":0.0,"max":2.0,"step":0.1,"cat":"sampling","desc":"Tail-free"},
 "mirostat_mode":{"type":"int","default":0,"min":0,"max":2,"step":1,"cat":"mirostat","desc":"Mode"},
 "mirostat_tau":{"type":"float","default":5.0,"min":0.0,"max":10.0,"step":0.1,"cat":"mirostat","desc":"Tau"},
 "mirostat_eta":{"type":"float","default":0.1,"min":0.0,"max":1.0,"step":0.01,"cat":"mirostat","desc":"Eta"},
 "repetition_penalty":{"type":"float","default":1.0,"min":0.0,"max":2.0,"step":0.05,"cat":"penalties","desc":"Repeat"},
 "repetition_penalty_range":{"type":"int","default":1024,"min":0,"max":131072,"step":64,"cat":"penalties","desc":"Repeat range"},
 "presence_penalty":{"type":"float","default":0.0,"min":-2.0,"max":2.0,"step":0.1,"cat":"penalties","desc":"Presence"},
 "frequency_penalty":{"type":"float","default":0.0,"min":-2.0,"max":2.0,"step":0.1,"cat":"penalties","desc":"Frequency"},
 "max_tokens":{"type":"int","default":2048,"min":1,"max":131072,"step":1,"cat":"generation","desc":"Max tokens"},
 "context_length":{"type":"int","default":4096,"min":256,"max":1048576,"step":256,"cat":"generation","desc":"Context window"},
 "seed":{"type":"int","default":-1,"min":-1,"max":999999999,"step":1,"cat":"generation","desc":"Seed (-1=random)"},
 "stop":{"type":"list","default":[],"cat":"generation","desc":"Stop seqs"},
}
CFG={"openai_host":"http://10.0.0.113:5000/v1","openai_api_key":"",
 "engine":"openai","model":"omnibrain-ue","system_prompt":"","keep_alive":"5m",
 "think_enabled":True,"think_visible":False,"show_stats":False,"is_thinking_model":False,
 "chat_template":""}
PO,MDFL={},{}
GGUF_META={}  # last-fetched GGUF metadata for the active model

THEMES={
 "ss2":{"--g":"#6688cc","--gd":"#3a4a7a","--gk":"#1e2844","--bg":"#06060e","--bgp":"#0a0e1a","--bgi":"#080912","--bd":"#1a2040","--r":"#cc2233","--c":"#5577bb","--o":"#7799dd","--p":"#8888cc","--mem":"#5599dd","--ri":"#cc2233","--accent":"#4466aa","label":"System Shock 2"},
 "shodan":{"--g":"#cc3344","--gd":"#772233","--gk":"#3a1122","--bg":"#0a0408","--bgp":"#0e0812","--bgi":"#0a0610","--bd":"#2a0a1a","--r":"#ff2244","--c":"#cc4466","--o":"#ff4466","--p":"#aa3355","--mem":"#dd4477","--ri":"#ff2244","--accent":"#aa2244","label":"SHODAN"},
 "trioptimum":{"--g":"#7766cc","--gd":"#4433aa","--gk":"#221a55","--bg":"#060410","--bgp":"#0a0818","--bgi":"#080614","--bd":"#1a1440","--r":"#cc2233","--c":"#6655bb","--o":"#8877dd","--p":"#9988ee","--mem":"#7766dd","--ri":"#cc2233","--accent":"#5544aa","label":"Tri-Optimum"},
 "xerxes":{"--g":"#44cc88","--gd":"#227744","--gk":"#114422","--bg":"#040a06","--bgp":"#060e0a","--bgi":"#050c08","--bd":"#0a2a1a","--r":"#cc2233","--c":"#44bb77","--o":"#66dd99","--p":"#55cc88","--mem":"#44ddaa","--ri":"#cc2233","--accent":"#33aa66","label":"XERXES"},
 "gits":{"--g":"#00ffaa","--gd":"#007755","--gk":"#003322","--bg":"#020a08","--bgp":"#041210","--bgi":"#010806","--bd":"#0a3a2a","--r":"#cc2233","--c":"#00ffdd","--o":"#44ffaa","--p":"#00ccff","--mem":"#22ddff","--ri":"#cc2233","--accent":"#009977","label":"Ghost in the Shell"},
 "edgerunner":{"--g":"#ff0055","--gd":"#880033","--gk":"#440018","--bg":"#08020a","--bgp":"#0e0410","--bgi":"#060108","--bd":"#3a0a2a","--r":"#ff2244","--c":"#ff0088","--o":"#ff3300","--p":"#cc00ff","--mem":"#ff44cc","--ri":"#ff2244","--accent":"#cc0044","label":"Edgerunner"},
 "event0":{"--g":"#ffcc00","--gd":"#886600","--gk":"#443300","--bg":"#0a0800","--bgp":"#100e04","--bgi":"#080600","--bd":"#3a2a0a","--r":"#cc2233","--c":"#ffdd44","--o":"#ff9900","--p":"#ffaa44","--mem":"#ffbb00","--ri":"#cc2233","--accent":"#aa8800","label":"Event[0]"},
 "alien":{"--g":"#39ff14","--gd":"#1a8a0a","--gk":"#0d4a06","--bg":"#040804","--bgp":"#061006","--bgi":"#020602","--bd":"#1a3a1a","--r":"#cc2233","--c":"#00cc44","--o":"#88cc00","--p":"#66ff44","--mem":"#44ff88","--ri":"#cc2233","--accent":"#22aa11","label":"Alien"},
 "venture":{"--g":"#ff6600","--gd":"#993300","--gk":"#4a1a00","--bg":"#0a0400","--bgp":"#100800","--bgi":"#080200","--bd":"#3a1a0a","--r":"#ff2222","--c":"#ff8844","--o":"#ffaa00","--p":"#ff4400","--mem":"#ffcc44","--ri":"#ff2222","--accent":"#cc5500","label":"Venture Bros"},
 "ice":{"--g":"#88ccff","--gd":"#446688","--gk":"#223344","--bg":"#020608","--bgp":"#040a10","--bgi":"#010408","--bd":"#1a2a3a","--r":"#cc2233","--c":"#44ddff","--o":"#88aaff","--p":"#6688ff","--mem":"#44aaff","--ri":"#cc2233","--accent":"#4488cc","label":"Ice"},
 "mono":{"--g":"#cccccc","--gd":"#666666","--gk":"#333333","--bg":"#080808","--bgp":"#0e0e0e","--bgi":"#050505","--bd":"#2a2a2a","--r":"#cc2233","--c":"#aaaaaa","--o":"#999999","--p":"#888888","--mem":"#aaaaaa","--ri":"#cc2233","--accent":"#888888","label":"Monochrome"},
 "soma":{"--g":"#5599ff","--gd":"#2a4488","--gk":"#152244","--bg":"#020408","--bgp":"#04080e","--bgi":"#010206","--bd":"#0a1a3a","--r":"#cc2233","--c":"#4488ff","--o":"#66aaff","--p":"#3366cc","--mem":"#4499ff","--ri":"#cc2233","--accent":"#3366bb","label":"SOMA"},
 "deusex":{"--g":"#ffaa22","--gd":"#aa6611","--gk":"#553308","--bg":"#080604","--bgp":"#0c0a06","--bgi":"#060402","--bd":"#2a1a0a","--r":"#cc2233","--c":"#ffcc44","--o":"#ddaa00","--p":"#ffbb33","--mem":"#eebb44","--ri":"#cc2233","--accent":"#cc8800","label":"Deus Ex"},
 "blade":{"--g":"#ff4488","--gd":"#882244","--gk":"#441122","--bg":"#060208","--bgp":"#0a040e","--bgi":"#040108","--bd":"#2a0a2a","--r":"#ff2244","--c":"#ff66aa","--o":"#cc44ff","--p":"#ff44cc","--mem":"#ee66ff","--ri":"#ff2244","--accent":"#cc3388","label":"Blade Runner"},
 "matrix":{"--g":"#00ff00","--gd":"#008800","--gk":"#004400","--bg":"#000800","--bgp":"#001000","--bgi":"#000400","--bd":"#003300","--r":"#cc2233","--c":"#00dd00","--o":"#00bb00","--p":"#44ff44","--mem":"#22ff66","--ri":"#cc2233","--accent":"#00aa00","label":"Matrix"},
 "nier":{"--g":"#e8dcc8","--gd":"#8a7a66","--gk":"#4a4030","--bg":"#0a0908","--bgp":"#0e0d0c","--bgi":"#080706","--bd":"#2a2520","--r":"#cc6644","--c":"#d4c8b4","--o":"#bbaa88","--p":"#c8b898","--mem":"#ddd0bb","--ri":"#cc6644","--accent":"#aa9978","label":"NieR"},
 "fallout":{"--g":"#44ff88","--gd":"#228844","--gk":"#114422","--bg":"#060a06","--bgp":"#0a100a","--bgi":"#040804","--bd":"#1a2a1a","--r":"#cc2233","--c":"#66ffaa","--o":"#88cc44","--p":"#44dd66","--mem":"#66ffbb","--ri":"#cc2233","--accent":"#33bb55","label":"Fallout"},
}

CUST_D={"llm_name":"AI","heading_mode":"text","heading_image":"images/heading.png","theme":"ss2",
    "nav_visible":True,"crt_effect":True,"sound_enabled":False,"pc_speaker":False,"engine":"openai",
    "brightness":100,"classic_steam":False}
def load_cust():
    d=dict(CUST_D)
    if os.path.exists(CUSTOM_P):
        try:
            with open(CUSTOM_P) as f: d.update(json.load(f))
        except: pass
    return d
def save_cust(d):
    with open(CUSTOM_P,"w") as f: json.dump(d,f,indent=2)
CUST=load_cust()
# Engine is fixed to openai-compatible — ignore any legacy CUST["engine"]
CFG["engine"]="openai"

# ══════════════════════════════════════════════════════════════════
# CHAT SYSTEM — Every chat is a file. Active ID tracked separately.
# ══════════════════════════════════════════════════════════════════
_chat_lock=threading.Lock()
_chat_version=0  # Bumps on any change, used for cross-window sync

def _chat_path(cid):
    return os.path.join(CHATS,f"{cid}.json")

def _read_chat(cid):
    """Read a chat file by ID. Returns dict or None."""
    p=_chat_path(cid)
    if not os.path.exists(p): return None
    try:
        with open(p) as f: return json.load(f)
    except: return None

def _write_chat(data):
    """Write chat data to its file. Always updates timestamp."""
    global _chat_version
    data["updated"]=datetime.now().isoformat()
    with _chat_lock:
        with open(_chat_path(data["id"]),"w") as f: json.dump(data,f)
        _chat_version+=1

def _get_active_id():
    """Get the currently active chat ID."""
    if os.path.exists(ACTIVE_ID_P):
        try:
            with open(ACTIVE_ID_P) as f: return f.read().strip()
        except: pass
    return None

def _set_active_id(cid):
    """Set the active chat ID."""
    with open(ACTIVE_ID_P,"w") as f: f.write(cid)

def _next_new_number():
    """Find next 'New N' number by scanning existing chat titles."""
    n=1
    for fp in glob.glob(os.path.join(CHATS,"*.json")):
        try:
            with open(fp) as f: d=json.load(f)
            title=d.get("title","")
            if title.startswith("New "):
                try: num=int(title[4:]); n=max(n,num+1)
                except: pass
        except: pass
    return n

def _create_new_chat():
    """Create a brand new chat file and set it active."""
    cid=uuid.uuid4().hex[:8]
    num=_next_new_number()
    data={"id":cid,"title":f"New {num}","model":CFG.get("model",""),
          "messages":[],"created":datetime.now().isoformat(),"updated":datetime.now().isoformat()}
    _write_chat(data)
    _set_active_id(cid)
    return data

def _ensure_active():
    """Ensure there's a valid active chat. Create one if not."""
    cid=_get_active_id()
    if cid:
        data=_read_chat(cid)
        if data: return data
    # No valid active chat — create one
    return _create_new_chat()

def _get_active():
    """Get active chat data. Always returns valid data."""
    return _ensure_active()

def _append_to_active(msg):
    """Append a message to the active chat and save immediately."""
    data=_get_active()
    data["messages"].append(msg)
    data["model"]=CFG.get("model","")
    _write_chat(data)

def _list_all_chats():
    """List all chat files, sorted by modification time (newest first)."""
    chats=[]
    for fp in sorted(glob.glob(os.path.join(CHATS,"*.json")),key=os.path.getmtime,reverse=True):
        try:
            with open(fp) as f: d=json.load(f)
            chats.append({"id":d["id"],"title":d.get("title","?"),"model":d.get("model",""),
                "updated":d.get("updated",""),"message_count":len(d.get("messages",[]))})
        except: pass
    return chats

# ── Helpers ───────────────────────────────────────────────────────
def eff(k):
    if k in PO: return PO[k]
    if k in MDFL: return MDFL[k]
    return PD[k]["default"]

def _unescape(s):
    """Process escape sequences in stop tokens: \\n → newline, \\t → tab, etc."""
    return s.replace("\\n","\n").replace("\\t","\t").replace("\\r","\r").replace("\\\\","\\")

def _reescape(s):
    """Re-escape special chars for display: newline → \\n, tab → \\t, etc."""
    return s.replace("\\","\\\\").replace("\n","\\n").replace("\t","\\t").replace("\r","\\r")

def build_openai_opts():
    """Build OpenAI-compatible /v1/chat/completions params. Always sends
    user/model defaults so custom samplers work; context_length is excluded
    (used only for client-side trimming, not sent to API)."""
    o={}
    for k,p in PD.items():
        if k=="context_length": continue
        v=eff(k)
        if k=="stop":
            if v: o["stop"]=v
            continue
        if k=="max_tokens":
            if v and v>0: o["max_tokens"]=v
            continue
        # Skip neutral defaults that aren't explicitly set by user or model
        if k not in PO and k not in MDFL:
            d=p.get("default")
            if v==d: continue
        o[k]=v
    return o
def parse_params(s):
    p,st={},[]
    if not s: return p
    for line in s.strip().split("\n"):
        line=line.strip()
        if not line or line.startswith("#"): continue
        parts=line.split(None,1)
        if len(parts)!=2: continue
        k,v=parts[0].strip(),parts[1].strip().strip('"').strip("'")
        if k=="stop": st.append(_unescape(v));continue
        if k in PD:
            try:
                if PD[k]["type"]=="int": p[k]=int(v)
                elif PD[k]["type"]=="float": p[k]=float(v)
                elif PD[k]["type"]=="bool": p[k]=v.lower() in ("true","1","yes")
            except: pass
    if st: p["stop"]=st
    return p
def det_think(n,d=None):
    nl=n.lower()
    for pat in TP:
        if pat in nl: return True
    if d:
        for pat in TP:
            if pat in (d.get("family") or "").lower(): return True
    return False
def strip_think(c):
    if not c: return c
    c=re.sub(r'<think>[\s\S]*?</think>\s*','',c,flags=re.DOTALL)
    c=re.sub(r'<think>[\s\S]*$','',c,flags=re.DOTALL)
    return c.strip()
def process_sys(sp):
    if not sp: return sp
    now=datetime.now()
    h=now.strftime("%I:%M %p").lower().lstrip('0')
    day=now.day;suf="th" if 11<=day<=13 else {1:"st",2:"nd",3:"rd"}.get(day%10,"th")
    return sp.replace("<|DATE|>",f"{h} {now.strftime('%B')} {day}{suf}, {now.year}")
def _auth_headers():
    h={"Content-Type":"application/json"}
    k=(CFG.get("openai_api_key") or "").strip()
    if k: h["Authorization"]=f"Bearer {k}"
    return h

def get_models():
    """List models from the OpenAI-compatible /v1/models endpoint."""
    try:
        r=R.get(f"{CFG['openai_host'].rstrip('/')}/models",headers=_auth_headers(),timeout=5)
        r.raise_for_status()
        return r.json().get("data",[])
    except: return []

def fetch_gguf_meta(name):
    """Pull GGUF metadata + sampling defaults for a model from the API.

    Tries (in order): text-generation-webui /v1/internal/model/info,
    llama-server /props, generic /v1/models/<id>. Returns a dict normalised
    to: {"context_length": int|None, "chat_template": str, "system": str,
         "details": {...raw...}, "sampling": {...sampling defaults...}}.
    """
    base=CFG['openai_host'].rstrip('/')
    out={"context_length":None,"chat_template":"","system":"","details":{},"sampling":{}}
    raw=None
    # text-generation-webui
    try:
        r=R.get(f"{base}/internal/model/info",headers=_auth_headers(),timeout=8)
        if r.status_code==200: raw=r.json();out["details"].update(raw)
    except: pass
    # llama-server props (often at the host root, not under /v1)
    try:
        root=base[:-3] if base.endswith("/v1") else base
        r=R.get(f"{root}/props",headers=_auth_headers(),timeout=8)
        if r.status_code==200:
            p=r.json();out["details"].update({"props":p})
            dm=p.get("default_generation_settings") or p.get("generation_settings") or {}
            for src,dst in (("temperature","temperature"),("top_k","top_k"),("top_p","top_p"),
                            ("min_p","min_p"),("typical_p","typical_p"),("tfs_z","tfs"),
                            ("repeat_penalty","repetition_penalty"),("repeat_last_n","repetition_penalty_range"),
                            ("presence_penalty","presence_penalty"),("frequency_penalty","frequency_penalty"),
                            ("mirostat","mirostat_mode"),("mirostat_tau","mirostat_tau"),("mirostat_eta","mirostat_eta"),
                            ("seed","seed")):
                if src in dm: out["sampling"][dst]=dm[src]
            if "n_ctx" in p: out["context_length"]=int(p["n_ctx"])
            if "chat_template" in p: out["chat_template"]=p["chat_template"]
            if "system_prompt" in p: out["system"]=p["system_prompt"]
    except: pass
    # generic /v1/models/<id> — some servers embed gguf metadata here
    try:
        r=R.get(f"{base}/models/{name}",headers=_auth_headers(),timeout=8)
        if r.status_code==200:
            d=r.json();out["details"].update({"model":d})
            meta=d.get("meta") or d.get("metadata") or {}
            for k in meta:
                if k.endswith(".context_length"):
                    try: out["context_length"]=int(meta[k])
                    except: pass
                if k.endswith("tokenizer.chat_template"):
                    out["chat_template"]=str(meta[k])
            # Some servers expose sampling defaults nested under "default_sampler"
            ds=d.get("default_sampler") or d.get("sampling") or {}
            for k,v in ds.items():
                if k in PD: out["sampling"][k]=v
    except: pass
    return out
def get_lan_ip():
    try: s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(("8.8.8.8",80));ip=s.getsockname()[0];s.close();return ip
    except: return "127.0.0.1"
def get_cfg_state():
    return {"connection":{k:CFG[k] for k in ("openai_host","openai_api_key","engine","model","system_prompt","keep_alive","chat_template")},
        "toggles":{k:CFG[k] for k in ("think_enabled","think_visible","show_stats")},"param_overrides":dict(PO)}
def apply_cfg_state(st):
    global PO
    for k,v in st.get("connection",{}).items():
        if k in CFG: CFG[k]=v
    for k,v in st.get("toggles",{}).items():
        if k in CFG: CFG[k]=v
    PO=dict(st.get("param_overrides",{}))

def trim_messages_to_context(msgs, num_ctx, sys_tokens=0):
    """
    Trim messages from the FRONT to fit within context_length.
    Rough estimate: 1 token ≈ 4 chars. Keeps most recent messages.
    sys_tokens: estimated tokens used by system prompt + memory injection.
    """
    budget = num_ctx - sys_tokens - max(200, eff("max_tokens"))  # reserve room for the response
    if budget <= 0: budget = num_ctx // 2

    # Walk backwards, accumulating token estimate
    kept = []
    total = 0
    for msg in reversed(msgs):
        content = msg.get("content","")
        est_tokens = len(content) // 4 + 4  # +4 for role overhead
        if total + est_tokens > budget and kept:
            break  # Stop adding older messages
        kept.append(msg)
        total += est_tokens

    kept.reverse()
    return kept

# ── Routes ────────────────────────────────────────────────────────
@app.route("/")
def index(): return render_template("index.html")
@app.route("/images/<path:fn>")
def serve_img(fn): return send_from_directory(IMAGES,fn)

@app.route("/api/models",methods=["GET"])
def api_models():
    ms=[]
    for m in get_models():
        mid=m.get("id","unknown")
        ms.append({"name":mid,"size":0,
            "parameter_size":m.get("parameter_size","") or m.get("meta",{}).get("general.parameter_count",""),
            "quantization":m.get("quantization","") or m.get("meta",{}).get("general.file_type",""),
            "family":m.get("family","gguf"),"is_thinking":det_think(mid)})
    return jsonify({"models":ms,"current":CFG["model"],"engine":"openai"})

@app.route("/api/model_info",methods=["POST"])
def api_model_info():
    n=request.json.get("model","")
    meta=fetch_gguf_meta(n)
    return jsonify({"template":meta.get("chat_template",""),
        "parameters_raw":json.dumps(meta.get("sampling",{}),indent=2) if meta.get("sampling") else "",
        "system_prompt":meta.get("system",""),"details":meta.get("details",{}),
        "context_length":meta.get("context_length")})

@app.route("/api/select_model",methods=["POST"])
def api_select_model():
    global MDFL,GGUF_META
    n=request.json.get("model","");CFG["model"]=n;MDFL={}
    meta=fetch_gguf_meta(n);GGUF_META=meta
    # Lift GGUF sampling defaults into MDFL so the UI shows them as model defaults
    samp=meta.get("sampling",{})
    for k,v in samp.items():
        if k not in PD: continue
        try:
            t=PD[k]["type"]
            if t=="int": MDFL[k]=int(v)
            elif t=="float": MDFL[k]=float(v)
            elif t=="bool": MDFL[k]=bool(v)
            else: MDFL[k]=v
        except: pass
    if meta.get("context_length"):
        try: MDFL["context_length"]=int(meta["context_length"])
        except: pass
    if meta.get("chat_template") and not CFG.get("chat_template","").strip():
        # Don't overwrite a user-edited template — only seed if empty
        pass
    CFG["is_thinking_model"]=det_think(n,meta.get("details",{}))
    return jsonify({"status":"ok","model":n,"model_defaults":MDFL,
        "model_system":meta.get("system",""),
        "template":meta.get("chat_template",""),
        "is_thinking_model":CFG["is_thinking_model"],"engine":"openai"})

@app.route("/api/config",methods=["GET","POST"])
def api_config():
    if request.method=="GET":
        e,s={},{}
        for k in PD:
            v=eff(k)
            if k=="stop" and isinstance(v,list): e[k]=[_reescape(t) for t in v]
            else: e[k]=v
            s[k]="user" if k in PO else("model" if k in MDFL else "default")
        return jsonify({**CFG,"params":e,"sources":s,"model_defaults":MDFL,"param_defs":PD,
            "lan_ip":get_lan_ip(),"port":7865,"hostname":socket.gethostname()})
    data=request.json
    for k in ("openai_host","openai_api_key","engine","model","system_prompt","keep_alive","chat_template"):
        if k in data: CFG[k]=data[k]
    for k in ("think_enabled","think_visible","show_stats"):
        if k in data: CFG[k]=bool(data[k])
    if "params" in data:
        PO.clear()
        for k,v in data["params"].items():
            if k not in PD: continue
            pd=PD[k]
            try:
                if pd["type"]=="int": v=int(v)
                elif pd["type"]=="float": v=float(v)
                elif pd["type"]=="bool": v=bool(v)
                elif pd["type"]=="list":
                    if isinstance(v,str): v=[_unescape(x.strip()) for x in v.split(",") if x.strip()]
            except: continue
            PO[k]=v
    return jsonify({"status":"ok"})

@app.route("/api/reset_param",methods=["POST"])
def api_rp():
    k=request.json.get("key","");PO.pop(k,None);v=eff(k)
    if k=="stop" and isinstance(v,list): v=[_reescape(t) for t in v]
    return jsonify({"status":"ok","effective":v})
@app.route("/api/reset_all_params",methods=["POST"])
def api_rap(): PO.clear();return jsonify({"status":"ok"})

# Presets
@app.route("/api/presets",methods=["GET"])
def api_presets():
    ps=[]
    for fp in sorted(glob.glob(os.path.join(PRESETS,"*.json")),key=os.path.getmtime,reverse=True):
        try:
            with open(fp) as f: d=json.load(f)
            ps.append({"id":d["id"],"name":d["name"],"model":d.get("state",{}).get("connection",{}).get("model","")})
        except: pass
    return jsonify({"presets":ps})
@app.route("/api/presets/save",methods=["POST"])
def api_ps():
    n=request.json.get("name","").strip()
    if not n: return jsonify({"error":"Name needed"}),400
    pid=uuid.uuid4().hex[:8]
    with open(os.path.join(PRESETS,f"{pid}.json"),"w") as f:
        json.dump({"id":pid,"name":n,"state":get_cfg_state()},f,indent=2)
    return jsonify({"status":"ok"})
@app.route("/api/presets/load",methods=["POST"])
def api_pl():
    fp=os.path.join(PRESETS,f"{request.json.get('id','')}.json")
    if not os.path.exists(fp): return jsonify({"error":"Not found"}),404
    with open(fp) as f: apply_cfg_state(json.load(f).get("state",{}))
    return jsonify({"status":"ok"})
@app.route("/api/presets/delete",methods=["POST"])
def api_pdel():
    fp=os.path.join(PRESETS,f"{request.json.get('id','')}.json")
    if os.path.exists(fp): os.remove(fp)
    return jsonify({"status":"ok"})

# ══════════════════════════════════════════════════════════════════
# CHAT ROUTES — Simple and correct
# ══════════════════════════════════════════════════════════════════

@app.route("/api/active",methods=["GET"])
def api_active_get():
    """Get the active chat + version for rendering and sync."""
    data=_get_active()
    return jsonify({"chat":data,"version":_chat_version,"active_id":data["id"]})

@app.route("/api/active/poll",methods=["GET"])
def api_active_poll():
    """Lightweight sync check."""
    return jsonify({"version":_chat_version,"active_id":_get_active_id()})

@app.route("/api/active/new",methods=["POST"])
def api_active_new():
    """Start a new chat. Current chat is already saved (it's always a file)."""
    data=_create_new_chat()
    return jsonify({"status":"ok","chat":data,"version":_chat_version})

@app.route("/api/active/switch",methods=["POST"])
def api_active_switch():
    """Switch to a different chat by ID."""
    cid=request.json.get("id","")
    if not _read_chat(cid): return jsonify({"error":"Chat not found"}),404
    _set_active_id(cid)
    global _chat_version
    _chat_version+=1
    return jsonify({"status":"ok","version":_chat_version})

@app.route("/api/active/rename",methods=["POST"])
def api_active_rename():
    """Rename the active chat."""
    new_title=request.json.get("title","").strip()
    if not new_title: return jsonify({"error":"Title required"}),400
    data=_get_active()
    data["title"]=new_title
    _write_chat(data)
    return jsonify({"status":"ok","title":new_title,"version":_chat_version})

@app.route("/api/active/unsend",methods=["POST"])
def api_active_unsend():
    """Remove last user+assistant pair (or just last user msg)."""
    data=_get_active()
    msgs=data.get("messages",[])
    if not msgs: return jsonify({"status":"empty"})
    if msgs[-1].get("role")=="assistant":
        msgs.pop()
        if msgs and msgs[-1].get("role")=="user": msgs.pop()
    elif msgs[-1].get("role")=="user":
        msgs.pop()
    data["messages"]=msgs
    _write_chat(data)
    return jsonify({"status":"ok","version":_chat_version})


@app.route("/api/active/append",methods=["POST"])
def api_active_append():
    """Append an assistant message (used to save partial generation on stop)."""
    content=request.json.get("content","")
    thinking=request.json.get("thinking","")
    if not content and not thinking: return jsonify({"status":"empty"})
    _append_to_active({"role":"assistant","content":content,"thinking":thinking})
    return jsonify({"status":"ok","version":_chat_version})

@app.route("/api/active/edit",methods=["POST"])
def api_active_edit():
    """Edit a message at a specific index in the active chat."""
    idx=request.json.get("index")
    new_content=request.json.get("content","")
    if idx is None: return jsonify({"error":"Index required"}),400
    data=_get_active()
    msgs=data.get("messages",[])
    if idx<0 or idx>=len(msgs): return jsonify({"error":"Invalid index"}),400
    msgs[idx]["content"]=new_content
    data["messages"]=msgs
    _write_chat(data)
    return jsonify({"status":"ok","version":_chat_version})

@app.route("/api/active/regen",methods=["POST"])
def api_active_regen():
    """Regenerate from a message index. Truncates chat to just before the target
    user message and returns that message text so the frontend can re-send it."""
    idx=request.json.get("index")
    if idx is None: return jsonify({"error":"Index required"}),400
    data=_get_active()
    msgs=data.get("messages",[])
    if idx<0 or idx>=len(msgs): return jsonify({"error":"Invalid index"}),400
    # Find the user message to regenerate from
    if msgs[idx].get("role")=="user":
        user_idx=idx
    else:
        # Assistant message: find the preceding user message
        user_idx=None
        for i in range(idx-1,-1,-1):
            if msgs[i].get("role")=="user":
                user_idx=i;break
        if user_idx is None: return jsonify({"error":"No user message found"}),400
    user_text=msgs[user_idx]["content"]
    # Truncate: keep everything before the user message
    data["messages"]=msgs[:user_idx]
    _write_chat(data)
    return jsonify({"status":"ok","version":_chat_version,"message":user_text})

# ── Chat library operations ───────────────────────────────────────
@app.route("/api/chats",methods=["GET"])
def api_chats_list():
    return jsonify({"chats":_list_all_chats(),"active_id":_get_active_id()})

@app.route("/api/chats/rename",methods=["POST"])
def api_chats_rename():
    cid=request.json.get("id","")
    new_title=request.json.get("title","").strip()
    if not new_title: return jsonify({"error":"Title required"}),400
    data=_read_chat(cid)
    if not data: return jsonify({"error":"Not found"}),404
    data["title"]=new_title
    _write_chat(data)
    return jsonify({"status":"ok","version":_chat_version})

@app.route("/api/chats/duplicate",methods=["POST"])
def api_chats_dup():
    cid=request.json.get("id","")
    data=_read_chat(cid)
    if not data: return jsonify({"error":"Not found"}),404
    new_id=uuid.uuid4().hex[:8]
    data["id"]=new_id
    data["title"]=data.get("title","Chat")+" (copy)"
    data["created"]=datetime.now().isoformat()
    _write_chat(data)
    return jsonify({"status":"ok","id":new_id})

@app.route("/api/chats/delete",methods=["POST"])
def api_chats_del():
    cid=request.json.get("id","")
    fp=_chat_path(cid)
    if not os.path.exists(fp): return jsonify({"error":"Not found"}),404
    # If deleting the active chat, switch to a new one
    if _get_active_id()==cid:
        os.remove(fp)
        _create_new_chat()
    else:
        os.remove(fp)
    global _chat_version
    _chat_version+=1
    return jsonify({"status":"ok","version":_chat_version})

@app.route("/api/chats/export",methods=["POST"])
def api_chats_export():
    cid=request.json.get("id","")
    data=_read_chat(cid) or _get_active()
    lines=[f"# {data.get('title','Session')}",""]
    for m in data.get("messages",[]):
        lines.append(f"[{m.get('role','').upper()}]\n{strip_think(m.get('content',''))}\n")
    return jsonify({"text":"\n".join(lines)})

# ── Customization ─────────────────────────────────────────────────
@app.route("/api/customization",methods=["GET","POST"])
def api_cust():
    global CUST
    if request.method=="GET": return jsonify({**CUST,"themes":THEMES})
    data=request.json
    for k in ("llm_name","heading_mode","heading_image","theme"):
        if k in data: CUST[k]=data[k]
    for k in ("nav_visible","crt_effect","sound_enabled","pc_speaker","classic_steam"):
        if k in data: CUST[k]=bool(data[k])
    if "brightness" in data: CUST["brightness"]=int(data["brightness"])
    save_cust(CUST);return jsonify({"status":"ok"})

# ── Memory ────────────────────────────────────────────────────────
@app.route("/api/memory/stats",methods=["GET"])
def api_ms():
    ltm=get_ltm();s=ltm.get_stats()
    s["last_status"]=ltm.last_status
    s["last_interest"]=ltm.last_interest;s["last_action"]=ltm.last_action;s["config"]=ltm.config
    return jsonify(s)
@app.route("/api/memory/config",methods=["POST"])
def api_mc():
    ltm=get_ltm();data=request.json
    for k in ("enable_saving","enable_injection","dumb_mode"):
        if k in data: ltm.config[k]=bool(data[k])
    for k in ("interest_threshold","load_similarity_threshold"):
        if k in data: ltm.config[k]=float(data[k])
    for k in ("max_memories_to_fetch","memory_length_cutoff","min_pair_length"):
        if k in data: ltm.config[k]=int(data[k])
    ltm.save_config();return jsonify({"status":"ok"})
@app.route("/api/memory/list",methods=["GET"])
def api_ml(): return jsonify({"memories":get_ltm().list_memories()})
@app.route("/api/memory/delete",methods=["POST"])
def api_md(): get_ltm().delete_memory(request.json.get("id",0));return jsonify({"status":"ok"})
@app.route("/api/memory/reset",methods=["POST"])
def api_mr(): get_ltm().reset_all();return jsonify({"status":"ok"})
@app.route("/api/memory/export",methods=["GET"])
def api_me(): return jsonify({"text":get_ltm().export_text()})

# ══════════════════════════════════════════════════════════════════
# CHAT ENDPOINT — Context cutoff + auto-save
# ══════════════════════════════════════════════════════════════════
@app.route("/api/chat",methods=["POST"])
def api_chat():
    data=request.json;user_msg=data.get("message","").strip()
    if not user_msg: return jsonify({"error":"Empty"}),400
    if not CFG["model"]: return jsonify({"error":"No model selected."}),400

    # Append user message immediately (auto-save)
    _append_to_active({"role":"user","content":user_msg})

    ltm=get_ltm()
    all_msgs=_get_active().get("messages",[])

    # Build system messages (measure their size for context budgeting)
    sys_parts=[]
    sp=process_sys(CFG["system_prompt"])
    if sp: sys_parts.append({"role":"system","content":sp})

    # Memory injection — query uses ONLY the most recent pair:
    # the previous assistant response + the current user message just sent
    mem_inj=None;retrieved=[]
    if ltm.config["enable_injection"]:
        query_parts=[]
        # Find the previous assistant message (before the user msg we just appended)
        for m in reversed(all_msgs[:-1]):
            if m.get("role")=="assistant":
                query_parts.append(strip_think(m["content"])[:300])
                break
        # Add the current user message (always present, it's the last one)
        query_parts.append(strip_think(user_msg)[:300])
        query_text=" ".join(query_parts)
        mem_inj,retrieved=ltm.build_injection(query_text)
        if mem_inj: sys_parts.append({"role":"system","content":mem_inj})

    # Estimate system token usage
    sys_chars=sum(len(m["content"]) for m in sys_parts)
    sys_tokens_est=sys_chars//4+20

    # Context cutoff: trim history to fit within context_length
    num_ctx=eff("context_length")
    history_for_api=[]
    for msg in all_msgs:
        c=msg["content"]
        if msg["role"]=="assistant": c=strip_think(c)
        history_for_api.append({"role":msg["role"],"content":c})

    trimmed=trim_messages_to_context(history_for_api, num_ctx, sys_tokens_est)

    api_msgs=sys_parts+trimmed
    think_on=CFG["think_enabled"] and CFG["is_thinking_model"]

    def gen():
        mem_action_inject=f"injected:{len(retrieved)}" if retrieved else ("no_match" if ltm.config["enable_injection"] else "inject_off")
        try:
            yield f"data: {json.dumps({'mem_inject':mem_action_inject,'mem_count':len(retrieved),'ctx_msgs':len(trimmed),'ctx_total':len(all_msgs)})}\n\n"

            fc,ft="","";gen_started=time.time();in_think=False;think_t0=None
            opts=build_openai_opts()
            payload={"model":CFG["model"],"messages":api_msgs,"stream":True}
            payload.update(opts)
            if CFG.get("chat_template","").strip(): payload["chat_template"]=CFG["chat_template"]
            r=R.post(f"{CFG['openai_host'].rstrip('/')}/chat/completions",
                     json=payload,headers=_auth_headers(),stream=True,timeout=300)
            if r.status_code!=200:
                try:
                    err_body=r.json();e=err_body.get("error")
                    err_msg=e.get("message") if isinstance(e,dict) else (e or err_body.get("detail") or r.text)
                except: err_msg=r.text or f"HTTP {r.status_code}"
                yield f"data: {json.dumps({'error':f'OpenAI ({r.status_code}): {err_msg}'})}" + "\n\n";return
            st={}
            buffer=""  # for splicing across <think> tag boundaries
            for line in r.iter_lines():
                if not line: continue
                line=line.decode('utf-8') if isinstance(line,bytes) else line
                if not line.startswith("data: "): continue
                chunk=line[6:].strip()
                if chunk=="[DONE]": break
                try:
                    d=json.loads(chunk)
                    choice=d.get("choices",[{}])[0]
                    delta=choice.get("delta",{})
                    ct=delta.get("content","") or ""
                    rt=delta.get("reasoning_content","") or delta.get("reasoning","") or ""
                    fin=choice.get("finish_reason")
                    if rt:
                        if not think_t0:
                            think_t0=time.time();in_think=True
                            yield f"data: {json.dumps({'think_start':True})}\n\n"
                        ft+=rt
                        yield f"data: {json.dumps({'thinking':rt,'think_len':len(ft)})}\n\n"
                    if ct:
                        # Inline <think>...</think> stripping for servers that don't split reasoning
                        buffer+=ct
                        out=""
                        while buffer:
                            if in_think:
                                idx=buffer.find("</think>")
                                if idx==-1:
                                    ft+=buffer;yield f"data: {json.dumps({'thinking':buffer,'think_len':len(ft)})}\n\n";buffer="";break
                                ft+=buffer[:idx];buffer=buffer[idx+len("</think>"):]
                                in_think=False
                                td=round(time.time()-(think_t0 or time.time()),1)
                                yield f"data: {json.dumps({'think_end':True,'think_duration':td})}\n\n"
                            else:
                                idx=buffer.find("<think>")
                                if idx==-1:
                                    out+=buffer;buffer="";break
                                out+=buffer[:idx];buffer=buffer[idx+len("<think>"):]
                                in_think=True;think_t0=time.time()
                                yield f"data: {json.dumps({'think_start':True})}\n\n"
                        if out:
                            fc+=out
                            yield f"data: {json.dumps({'token':out})}\n\n"
                    if fin:
                        if in_think:
                            td=round(time.time()-(think_t0 or time.time()),1)
                            in_think=False
                            yield f"data: {json.dumps({'think_end':True,'think_duration':td})}\n\n"
                        timings=d.get("timings",{});usage=d.get("usage",{})
                        if timings:
                            st["eval_count"]=timings.get("predicted_n",0)
                            if timings.get("predicted_ms"): st["eval_duration"]=int(timings["predicted_ms"]*1e6)
                            if timings.get("prompt_ms"):
                                st["prompt_eval_duration"]=int(timings["prompt_ms"]*1e6)
                                st["prompt_eval_count"]=timings.get("prompt_n",0)
                            if timings.get("predicted_ms") and timings.get("prompt_ms"):
                                st["total_duration"]=int((timings["predicted_ms"]+timings["prompt_ms"])*1e6)
                        elif usage:
                            st["eval_count"]=usage.get("completion_tokens",0)
                            st["prompt_eval_count"]=usage.get("prompt_tokens",0)
                            st["total_duration"]=int((time.time()-gen_started)*1e9)
                            if st["eval_count"]:
                                st["eval_duration"]=int((time.time()-gen_started)*1e9)
                except: pass
            _append_to_active({"role":"assistant","content":fc,"thinking":ft})
            yield f"data: {json.dumps({'done':True,'stats':st,'version':_chat_version})}\n\n"
            if (ltm.config["enable_saving"] or ltm.config.get("dumb_mode")) and fc:
                ltm.evaluate_and_store(user_msg, fc)
                yield f"data: {json.dumps({'mem_save':ltm.last_action,'mem_interest':ltm.last_interest})}\n\n"
        except R.exceptions.ConnectionError:
            yield f"data: {json.dumps({'error':'Cannot connect to '+CFG.get('openai_host','')})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error':str(e)})}\n\n"
    return Response(stream_with_context(gen()),mimetype="text/event-stream")

# ══════════════════════════════════════════════════════════════════
# SPEECH ROUTES — TTS only (STT removed)
# ══════════════════════════════════════════════════════════════════
_speech_cfg = None
def get_speech_cfg():
    global _speech_cfg
    if _speech_cfg is None:
        try:
            from speech import load_speech_config
            _speech_cfg = load_speech_config()
        except: _speech_cfg = {}
    return _speech_cfg

@app.route("/api/speech/config", methods=["GET","POST"])
def api_speech_config():
    global _speech_cfg
    if request.method == "GET":
        return jsonify(get_speech_cfg())
    data = request.json
    cfg = get_speech_cfg()
    for k in ("tts_enabled","tts_auto_speak"):
        if k in data: cfg[k] = bool(data[k])
    if "tts_voice" in data: cfg["tts_voice"] = str(data["tts_voice"])
    for k in ("tts_rate","tts_volume"):
        if k in data: cfg[k] = int(data[k])
    _speech_cfg = cfg
    try:
        from speech import save_speech_config
        save_speech_config(cfg)
    except: pass
    return jsonify({"status":"ok"})

@app.route("/api/speech/tts", methods=["POST"])
def api_speech_tts():
    try:
        from speech import speak_to_wav
        text = request.json.get("text", "").strip()
        if not text:
            return jsonify({"error":"No text"}), 400
        cfg = get_speech_cfg()
        wav = speak_to_wav(text, cfg)
        if wav:
            return Response(wav, mimetype="audio/wav")
        return jsonify({"error":"TTS generation failed"}), 500
    except ImportError as e:
        return jsonify({"error": f"pyttsx3 not installed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/speech/voices", methods=["GET"])
def api_speech_voices():
    try:
        from speech import get_tts_voices
        return jsonify({"voices": get_tts_voices()})
    except Exception as e:
        return jsonify({"voices": [], "error": str(e)})

@app.route("/api/health",methods=["GET"])
def api_health():
    try:
        # Probe /v1/models — universal OpenAI-compatible health check
        r=R.get(f"{CFG['openai_host'].rstrip('/')}/models",headers=_auth_headers(),timeout=3)
        if r.status_code<500:
            return jsonify({"ollama":"connected","engine":"openai"})
        return jsonify({"ollama":"disconnected","engine":"openai"}),503
    except: return jsonify({"ollama":"disconnected","engine":"openai"}),503

if __name__=="__main__":
    port=7865;lan=get_lan_ip()
    # Ensure an active chat exists on startup
    _ensure_active()
    print(f"\n\033[36m  AutoType v1.02\033[0m\n  Local:   http://localhost:{port}\n  Network: http://{lan}:{port}\n")
    threading.Thread(target=lambda:get_ltm(),daemon=True).start()
    threading.Thread(target=lambda:(time.sleep(1.5),webbrowser.open(f"http://localhost:{port}")),daemon=True).start()
    app.run(host="0.0.0.0",port=port,debug=False)
