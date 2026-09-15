import os,json,re,feedparser,requests
from pathlib import Path
from datetime import datetime,timezone
cfg=json.loads(Path("config.json").read_text())
signals=[]
for u in cfg["feeds"]:
    try:
        f=feedparser.parse(u)
        for e in f.entries[:30]:
            t=e.get("title","").strip(); s=re.sub("<[^>]+>"," ",e.get("summary","")).strip()
            tx=(t+" "+s).lower()
            score=sum(k in tx for k in ["need","help","problem","looking for","recommend","how do","struggling","hire","cost","urgent","deadline"])
            if score>=cfg["min_score"]: signals.append({"title":t,"summary":s[:1500],"url":e.get("link",""),"score":score})
    except Exception: pass
signals.sort(key=lambda x:x["score"],reverse=True)
latest="No strong signal found."
key=os.getenv("OPENAI_API_KEY","").strip(); model=os.getenv("LLM_MODEL","").strip()
if signals and key and model:
    s=signals[0]
    prompt=f"""Turn this public demand signal into one realistic small fixed-scope service pilot.
Signal: {s['title']}
Context: {s['summary']}
Give: offer name, starter price, 3 deliverables, why it solves the problem, and a short
permission-based outreach message. Never fabricate proof or guarantee results."""
    try:
        r=requests.post(os.getenv("LLM_BASE_URL","https://api.openai.com/v1").rstrip()+"/chat/completions",
          headers={"Authorization":"Bearer "+key},
          json={"model":model,"messages":[{"role":"system","content":"Truthful service-business strategist."},{"role":"user","content":prompt}],"temperature":.35},timeout=60)
        r.raise_for_status(); latest=r.json()["choices"][0]["message"]["content"]
    except Exception: latest="AI request failed this cycle."
elif signals:
    latest="Top signal:\n"+signals[0]["title"]+"\n\nConfigure an authorized AI API key to generate the offer."
state={"updated_at":datetime.now(timezone.utc).isoformat(),"mode":"approval","signals":len(signals),
       "top_signal":signals[0] if signals else None,"latest":latest}
Path("data/state.json").write_text(json.dumps(state,indent=2))
