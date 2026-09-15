import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from engine import conn, cycle, stats
load_dotenv()
app=Flask(__name__)
HTML=r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revenue OS</title><style>
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f4f4f6;margin:0;padding:14px;color:#111}
h1{margin:4px 0 12px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.card{background:#fff;border-radius:18px;padding:15px;margin:8px 0;box-shadow:0 2px 12px #0001}
.stat b{font-size:25px;display:block}button{border:0;border-radius:12px;padding:12px;margin:3px;font-weight:700}
.dark{background:#111;color:#fff}.danger{background:#d22;color:#fff}.muted{color:#666;font-size:13px}
.item{padding:12px 0;border-bottom:1px solid #eee}.pill{padding:5px 8px;border-radius:9px;background:#eee;font-size:12px}
</style></head><body>
<h1>Revenue OS</h1>
<div class=grid id=stats></div>
<div class=card><b>Autonomy</b><p id=mode>approval</p>
<button onclick="setmode('manual')">Manual</button><button onclick="setmode('approval')">Approval</button><button onclick="setmode('autopilot')">Autopilot</button>
<button class=danger onclick="kill()">Emergency stop</button><button class=dark onclick="run()">Run now</button>
<p class=muted>Autopilot runs bounded research/offer jobs. Outreach remains permission-based and authorized.</p></div>
<div class=card><b>Latest queued outreach</b><div id=drafts>Loading…</div></div>
<script>
async function refresh(){let s=await (await fetch('/api/stats')).json();document.querySelector('#stats').innerHTML=
Object.entries(s).map(([k,v])=>`<div class="card stat">${k}<b>${v}</b></div>`).join('');
let m=await (await fetch('/api/mode')).json();document.querySelector('#mode').textContent=m.mode;
let d=await (await fetch('/api/drafts')).json();document.querySelector('#drafts').innerHTML=d.map(x=>`<div class=item><b>${esc(x.name)}</b><br>${esc(x.message)}<br><span class=pill>${esc(x.price)}</span></div>`).join('')||'No drafts yet.'}
async function run(){await fetch('/api/cycle',{method:'POST'});refresh()}
async function kill(){await fetch('/api/kill',{method:'POST'});refresh()}
async function setmode(x){await fetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:x})});refresh()}
function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
refresh();setInterval(refresh,10000)
</script></body></html>"""
@app.get("/")
def home(): return render_template_string(HTML)
@app.get("/api/stats")
def api_stats(): return jsonify(stats())
@app.get("/api/mode")
def api_mode():
    c=conn(); return jsonify({"mode":c.execute("SELECT value FROM settings WHERE key='mode'").fetchone()["value"],
                              "kill":c.execute("SELECT value FROM settings WHERE key='kill'").fetchone()["value"]})
@app.get("/api/drafts")
def api_drafts():
    c=conn(); rows=c.execute("""SELECT d.message,o.name,o.price FROM drafts d JOIN offers o ON o.id=d.offer_id
    ORDER BY d.id DESC LIMIT 15""").fetchall(); return jsonify([dict(r) for r in rows])
@app.post("/api/cycle")
def api_cycle(): return jsonify(cycle())
@app.post("/api/kill")
def api_kill():
    c=conn(); c.execute("UPDATE settings SET value='1' WHERE key='kill'"); c.commit(); return jsonify({"stopped":True})
@app.post("/api/mode")
def api_setmode():
    m=request.json.get("mode")
    if m not in ["manual","approval","autopilot"]: return jsonify({"error":"invalid"}),400
    c=conn(); c.execute("UPDATE settings SET value=? WHERE key='mode'",(m,)); c.execute("UPDATE settings SET value='0' WHERE key='kill'"); c.commit()
    return jsonify({"mode":m})
if __name__=="__main__":
    conn()
    s=BackgroundScheduler(); s.add_job(cycle,"interval",minutes=int(os.getenv("CYCLE_MINUTES","30"))); s.start()
    app.run(host=os.getenv("HOST","0.0.0.0"),port=int(os.getenv("PORT","8080")))
