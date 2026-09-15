import os, sqlite3, json, re
from datetime import datetime, timezone, date
import feedparser, requests

DB=os.getenv("DB_PATH","data/revenue.db")

def conn():
    os.makedirs(os.path.dirname(DB) or ".",exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS signals(
      id INTEGER PRIMARY KEY, title TEXT, summary TEXT, url TEXT,
      score INTEGER, intent INTEGER, urgency INTEGER, repeatability INTEGER,
      created_at TEXT);
    CREATE TABLE IF NOT EXISTS offers(
      id INTEGER PRIMARY KEY, signal_id INTEGER, name TEXT, price TEXT,
      deliverables TEXT, positioning TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS drafts(
      id INTEGER PRIMARY KEY, offer_id INTEGER, message TEXT, channel TEXT,
      status TEXT DEFAULT 'queued', created_at TEXT);
    CREATE TABLE IF NOT EXISTS prospects(
      id INTEGER PRIMARY KEY, name TEXT, source_url TEXT, status TEXT DEFAULT 'new',
      offer_id INTEGER, notes TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS results(
      id INTEGER PRIMARY KEY, prospect_id INTEGER, stage TEXT, amount REAL,
      notes TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
    INSERT OR IGNORE INTO settings VALUES('mode','approval');
    INSERT OR IGNORE INTO settings VALUES('kill','0');
    """); c.commit(); return c

def ai(prompt):
    key=os.getenv("OPENAI_API_KEY","").strip()
    model=os.getenv("LLM_MODEL","").strip()
    base=os.getenv("LLM_BASE_URL","https://api.openai.com/v1").rstrip("/")
    if not key or not model: return None
    r=requests.post(base+"/chat/completions",
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
        json={"model":model,"messages":[
          {"role":"system","content":"""You are the strategy engine for a small legitimate service business.
Optimize for useful, sellable outcomes. Never fabricate customers, testimonials, case studies,
credentials, results, scarcity, or guarantees. Use public information only. Do not suggest spam,
impersonation, scraping private accounts, bypassing platform controls, or deceptive claims.
Prefer a small fixed-scope paid pilot that can be fulfilled well."""},
          {"role":"user","content":prompt}],
        temperature=.35,timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def collect():
    c=conn(); feeds=[x.strip() for x in os.getenv("DEMAND_FEEDS","").split(",") if x.strip()]
    total=0
    keywords=["need","help","problem","looking for","recommend","how do","struggling","hire","cost","anyone know"]
    for u in feeds:
        f=feedparser.parse(u)
        for e in f.entries[:30]:
            title=e.get("title","").strip(); summary=re.sub("<[^>]+>"," ",e.get("summary","")).strip()
            text=(title+" "+summary).lower()
            intent=sum(k in text for k in keywords)
            urgency=sum(k in text for k in ["urgent","asap","today","deadline","stuck"])
            repeat=sum(k in text for k in ["every week","every month","again","constantly","ongoing"])
            score=intent+urgency+repeat
            if score>=int(os.getenv("MIN_DEMAND_SCORE","3")):
                c.execute("""INSERT INTO signals(title,summary,url,score,intent,urgency,repeatability,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",(title,summary[:1800],e.get("link",""),score,intent,urgency,repeat,
                datetime.now(timezone.utc).isoformat())); total+=1
    c.commit(); return total

def create_offers():
    c=conn()
    rows=c.execute("SELECT * FROM signals ORDER BY score DESC,id DESC LIMIT 5").fetchall()
    made=0
    for s in rows:
        prompt=f"""Demand signal:
TITLE: {s['title']}
CONTEXT: {s['summary'][:1500]}

Return JSON with exactly these keys:
name, price, deliverables, positioning, outreach

Create a realistic small service that one person could deliver using AI and normal
software. Price should be a fixed starter/pilot price, not a vague hourly estimate.
The outreach must be a short permission-based message, not mass spam."""
        try: out=ai(prompt)
        except Exception: out=None
        if not out: continue
        try:
            text=out.strip()
            if text.startswith("```"): text=text.split("\n",1)[1].rsplit("```",1)[0]
            d=json.loads(text)
            c.execute("""INSERT INTO offers(signal_id,name,price,deliverables,positioning,created_at)
            VALUES(?,?,?,?,?,?)""",(s["id"],d.get("name","Micro-service pilot"),d.get("price","$50-$150"),
            json.dumps(d.get("deliverables",[])),d.get("positioning",""),datetime.now(timezone.utc).isoformat()))
            oid=c.lastrowid
            c.execute("""INSERT INTO drafts(offer_id,message,channel,status,created_at) VALUES(?,?,?,?,?)""",
            (oid,d.get("outreach",""),"manual/authorized channel","queued",datetime.now(timezone.utc).isoformat()))
            made+=1
        except Exception: pass
    c.commit(); return made

def cycle():
    c=conn()
    if c.execute("SELECT value FROM settings WHERE key='kill'").fetchone()["value"]=="1": return {"stopped":True}
    collected=collect(); offers=create_offers()
    return {"signals":collected,"offers":offers}

def stats():
    c=conn()
    return {k:c.execute(q).fetchone()[0] for k,q in {
      "signals":"SELECT COUNT(*) FROM signals",
      "offers":"SELECT COUNT(*) FROM offers",
      "drafts":"SELECT COUNT(*) FROM drafts",
      "prospects":"SELECT COUNT(*) FROM prospects",
      "won":"SELECT COUNT(*) FROM results WHERE stage='won'",
      "revenue":"SELECT COALESCE(SUM(amount),0) FROM results WHERE stage='won'"
    }.items()}
