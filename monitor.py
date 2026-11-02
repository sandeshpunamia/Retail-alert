"""Reliance regulatory monitor.
Usage:  python monitor.py            -> collect news + notices, send instant alerts, queue notices
        python monitor.py --digest   -> same, then also email the regulatory digest
        python monitor.py --dry-run  -> print instead of emailing, don't save state
All free: Google News RSS, public regulator pages, Gmail SMTP, GitHub Actions.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, html, io, json, os, re, smtplib, sys, time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote_plus, urljoin

import feedparser, requests
from bs4 import BeautifulSoup

import config as C

STATE_FILE = "state.json"
JUNK_RE = re.compile(r"state sla office|^food safety and standards authority of india( \(fssai\))?( - .*)?$|read official source|internship|summit|schemes and services|training and awareness|state sla office|^food safety and standards authority of india( \\(fssai\\))?$|^\s*-", re.I)
TOPIC_RE = re.compile("|".join(map(re.escape, C.NOTICE_WORDS + C.HIGH_WORDS + ["fdi", "epr", "rules", "act", "licen", "standard", "audit", "cag"])), re.I)
GROUP_RE = {g["key"]: re.compile(r"\b(" + "|".join(re.escape(b) for b in g["brands"]) + r")(?![a-z])", re.I)
            for g in C.GROUPS}
GENERIC_RE = {g["key"]: re.compile(r"\b(" + "|".join(re.escape(b) for b in g["generic"]) + r")", re.I)
              for g in C.GROUPS if g.get("generic")}
INDIA_RE = re.compile(C.INDIA_TERMS, re.I)
ACTION_RE = re.compile(r"\b(" + "|".join(re.escape(a.strip()) for a in C.ACTIONS) + r")", re.I)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(timezone.utc)


# ---------------- helpers ----------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            st = json.load(f)
        st.setdefault("pending_news", [])
        return st
    return {"seen_news": [], "seen_reg": [], "pending_reg": [], "pending_news": [], "title_hashes": []}

def save_state(s):
    s["seen_news"] = s["seen_news"][-3000:]
    s["seen_reg"] = s["seen_reg"][-5000:]
    s["title_hashes"] = s["title_hashes"][-3000:]
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=1)

def norm_title(t):
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", t)          # strip " - Publisher"
    return hashlib.md5(re.sub(r"[^a-z0-9]", "", t.lower()).encode()).hexdigest()[:14]

def get(url, timeout=25, **kw):
    for attempt in range(2):
        try:
            r = requests.get(url, headers=UA, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2)
    return None

def entry_time(e):
    for k in ("published_parsed", "updated_parsed"):
        if getattr(e, k, None):
            return datetime(*getattr(e, k)[:6], tzinfo=timezone.utc)
    return None

def gnews(query, days=None):
    q = query if "when:" in query else f"{query} when:{days or 2}d"
    url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"
    r = get(url)
    return feedparser.parse(r.content).entries if r else []


# ---------------- stream 1: news ----------------
def collect_news(state):
    """Returns (instant_items, digest_items). Each item carries its group."""
    seen = set(state["seen_news"]); hashes = set(state["title_hashes"])
    jobs = [(g, q) for g in C.GROUPS for q in g["queries"]]
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda j: gnews(j[1], days=2), jobs))
    # Query-group is only a hint. Final group = first group (in priority order) whose brand matches.
    cand = {}
    for (g, q), entries in zip(jobs, results):
        for e in entries:
            cand.setdefault(e.link, e)
    instant, digest = [], []
    first_run = not state["seen_news"]
    max_age = C.FIRST_RUN_MAX_AGE_HOURS if first_run else C.NEWS_MAX_AGE_HOURS
    per_group = {}
    ordered = sorted(cand.items(), key=lambda kv: entry_time(kv[1]) or NOW, reverse=True)
    for link, e in ordered:
        t = entry_time(e)
        if t and NOW - t > timedelta(hours=max_age):
            continue
        title = html.unescape(e.title)
        low = title.lower() + " " + html.unescape(re.sub("<[^>]+>", " ", e.get("summary", ""))).lower()
        if not ACTION_RE.search(low):
            continue
        def hit(g):
            if GROUP_RE[g["key"]].search(low):
                return True
            gr = GENERIC_RE.get(g["key"])
            return bool(gr and gr.search(low) and INDIA_RE.search(low))
        grp = next((g for g in C.GROUPS if hit(g)), None)
        if not grp:
            continue
        h = norm_title(title)
        if link in seen or h in hashes:
            continue
        seen.add(link); hashes.add(h)
        per_group[grp["key"]] = per_group.get(grp["key"], 0) + 1
        if first_run and per_group[grp["key"]] > C.FIRST_RUN_CAP_PER_GROUP:
            continue
        item = {"title": title, "link": link, "source": e.get("source", {}).get("title", ""),
                "group": grp["key"], "label": grp["label"], "email": grp["email"],
                "time": t.astimezone(IST).strftime("%d %b %Y, %I:%M %p IST") if t else "n/a"}
        (instant if grp["mode"] == "instant" else digest).append(item)
    state["seen_news"] = list(seen); state["title_hashes"] = list(hashes)
    return instant, digest


# ---------------- stream 2: regulator notices ----------------
def scrape_direct(reg):
    items = []
    for page in reg["direct"]:
        r = get(page)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = " ".join(a.get_text(" ").split())
            href = urljoin(page, a["href"])
            if len(text) < 12 or href.startswith(("javascript", "mailto")):
                continue
            dated = re.search(r"20\d\d|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", text)
            if href.lower().endswith(".pdf") or (dated and any(w in text.lower() for w in C.NOTICE_WORDS)):
                items.append({"regulator": reg["name"], "title": text[:220], "link": href,
                              "date": "", "via": "direct"})
    return items

def scrape_gnews(reg):
    items = []
    for q in reg["gnews"]:
        for e in gnews(q, days=C.REG_MAX_AGE_DAYS):
            t = entry_time(e)
            if t and NOW - t > timedelta(days=C.REG_MAX_AGE_DAYS):
                continue
            title = html.unescape(e.title)
            core = re.sub(r"\s+-\s+[^-]{2,60}$", "", title).strip()
            if len(core) < 25 or JUNK_RE.search(title) or not TOPIC_RE.search(core):
                continue
            items.append({"regulator": reg["name"], "title": title, "link": e.link,
                          "date": t.astimezone(IST).strftime("%d %b %Y") if t else "", "via": "news"})
    return items

def pdf_or_page_text(url):
    r = get(url, timeout=40)
    if not r:
        return ""
    ctype = r.headers.get("content-type", "").lower()
    try:
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            from pypdf import PdfReader
            rd = PdfReader(io.BytesIO(r.content))
            return " ".join((p.extract_text() or "") for p in rd.pages[:C.MAX_PDF_PAGES])
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script", "style", "nav", "footer", "header"]):
            t.decompose()
        return " ".join(soup.get_text(" ").split())
    except Exception:
        return ""

def relevance(text, headline_only=False):
    low = text.lower()
    hi = sum(w in low for w in C.HIGH_WORDS); med = sum(w in low for w in C.MED_WORDS)
    if headline_only:   # only a title to go on, so lower thresholds
        return "High" if hi >= 2 else "Medium" if hi >= 1 or med >= 1 else "Low"
    return "High" if hi >= 4 else "Medium" if hi >= 2 or med >= 2 else "Low"

KEY = re.compile(r"\b(decided|approved|shall|must|mandatory|deadline|effective|with effect|within \d+|"
                 r"no later than|penalt|licen[cs]e|label|retail|e-commerce|compliance|prohibit|ban|"
                 r"extended|amend|draft|comments?|stakeholder)\b", re.I)

def free_summary(text, title):
    """Zero-cost extractive summary: top sentences containing decision/deadline/compliance words."""
    text = re.sub(r"\s+", " ", text)
    sents = [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if 40 < len(s) < 330]
    scored = sorted(((len(KEY.findall(s)), i, s) for i, s in enumerate(sents)), reverse=True)[:4]
    picked = [s for _, _, s in sorted(scored, key=lambda x: x[1])]
    return picked

def gemini_summary(text, title):
    """Optional FREE tier: set GEMINI_API_KEY secret (Google AI Studio free key). Falls back silently."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key or len(text) < 300:
        return None
    prompt = ("Summarise this Indian regulator document for a retail/FMCG compliance team in 4-5 short "
              "bullet lines: what was decided/announced, who it affects, deadlines or actions required. "
              f"Title: {title}\n\n{text[:14000]}")
    try:
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                          params={"key": key}, timeout=60,
                          json={"contents": [{"parts": [{"text": prompt}]}]})
        out = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return [l.strip("-* ").strip() for l in out.splitlines() if l.strip()][:6]
    except Exception:
        return None

def collect_regulatory(state):
    seen = set(state["seen_reg"]); hashes = set(state["title_hashes"])
    first_run = not state["seen_reg"] and not state["pending_reg"]
    new = []
    per_reg = 5 if first_run else 10
    for reg in C.REGULATORS:
        cands = scrape_direct(reg) + scrape_gnews(reg)
        taken = 0
        for it in cands:
            if taken >= per_reg:
                break
            key = it["link"]
            h = norm_title(it["title"])
            if key in seen or h in hashes:
                continue
            seen.add(key); hashes.add(h)
            new.append(it); taken += 1
    for it in new:
        text = pdf_or_page_text(it["link"]) if it["via"] == "direct" else ""
        basis = text or it["title"]
        lines = gemini_summary(text, it["title"]) if text else None
        if not lines:
            lines = free_summary(text, it["title"]) if len(text) > 400 else []
        it["summary"] = lines or ["Headline only - open the link for details."]
        it["relevance"] = relevance(it["title"] + " " + text[:6000], headline_only=not text)
    state["seen_reg"] = list(seen); state["title_hashes"] = list(hashes)
    state["pending_reg"].extend(new)
    return new


# ---------------- email ----------------
def send_email(subject, html_body, text_body, dry):
    if dry:
        print("=" * 70, "\nSUBJECT:", subject, "\n", text_body); return
    user, pwd, to = os.environ["SMTP_USER"], os.environ["SMTP_PASS"], os.environ["MAIL_TO"]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.attach(MIMEText(text_body, "plain", "utf-8")); msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(user, pwd); s.sendmail(user, [x.strip() for x in to.split(",")], msg.as_string())

def grouped_email(items, subject, heading, note, dry):
    """One email, items grouped by label, group order follows config."""
    now = datetime.now(IST).strftime("%d %b %Y, %I:%M %p")
    order = [g["label"] for g in C.GROUPS]
    items = sorted(items, key=lambda i: order.index(i["label"]))
    text, blocks, last = [f"{heading} ({now} IST)", ""], [], None
    for i in items:
        if i["label"] != last:
            last = i["label"]
            text += [f"== {last.upper()} ==", ""]
            blocks.append(f"<p style='margin:18px 0 6px;font-size:12px;letter-spacing:1px;color:#7F7F7F'>"
                          f"{html.escape(last.upper())}</p>")
        text += [f"* {i['title']}", f"  {i['source'] or 'n/a'} | {i['time']}", f"  {i['link']}", ""]
        blocks.append(f"<p style='margin:0 0 12px;border-left:3px solid #1F3864;padding-left:8px'>"
                      f"<b>{html.escape(i['title'])}</b><br><span style='color:#666'>"
                      f"{html.escape(i['source'] or 'n/a')} | {i['time']}</span><br>"
                      f"<a href='{i['link']}'>Read article</a></p>")
    body = (f"<div style='font-family:Calibri,Arial;font-size:14px'>"
            f"<h3 style='border-left:4px solid #1F3864;padding-left:8px;color:#1F3864'>{html.escape(heading)}</h3>"
            f"{''.join(blocks)}<p style='color:#888;font-size:12px'><i>{html.escape(note)}</i></p></div>")
    send_email(subject, body, "\n".join(text), dry)

NOTE = "Auto-generated from Google News. Verify before forwarding."

def send_news_emails(instant, dry):
    rel = [i for i in instant if i["email"] == "reliance"]
    comp = [i for i in instant if i["email"] == "competitor"]
    if rel:
        grouped_email(rel, f"ALERT: Reliance - govt action - {len(rel)} new item(s)",
                      "Government action alert: Reliance group", NOTE, dry)
    if comp:
        grouped_email(comp, f"Competitor watch - {len(comp)} new item(s)",
                      "Competitor watch: government action", NOTE, dry)


def digest_email(items, dry):
    order = {"High": 0, "Medium": 1, "Low": 2}
    items = sorted(items, key=lambda x: (order[x["relevance"]], x["regulator"]))
    now = datetime.now(IST).strftime("%d %b %Y, %I:%M %p")
    colour = {"High": "#C00000", "Medium": "#ED7D31", "Low": "#7F7F7F"}
    text, blocks = [f"REGULATORY UPDATE DIGEST ({now} IST)", ""], []
    for i in items:
        text += [f"[{i['relevance'].upper()}] {i['regulator']} - {i['title']}"] + \
                [f"  - {s}" for s in i["summary"]] + [f"  {i['link']}", ""]
        bullets = "".join(f"<li>{html.escape(s)}</li>" for s in i["summary"])
        blocks.append(
            f"<div style='border-left:4px solid {colour[i['relevance']]};padding:2px 10px;margin:0 0 16px'>"
            f"<b>{html.escape(i['regulator'])}</b> &nbsp;<span style='color:{colour[i['relevance']]};font-size:12px'>"
            f"Relevance: {i['relevance']}</span> <span style='color:#888;font-size:12px'>{i['date']}</span><br>"
            f"<b>{html.escape(i['title'])}</b><ul style='margin:4px 0'>{bullets}</ul>"
            f"<a href='{i['link']}'>Open source</a></div>")
    body = (f"<div style='font-family:Calibri,Arial;font-size:14px'>"
            f"<h3 style='border-left:4px solid #1F3864;padding-left:8px;color:#1F3864'>Regulatory update digest</h3>"
            f"{''.join(blocks)}<p style='color:#888;font-size:12px'><i>Auto-generated summaries; "
            f"read the source document before acting.</i></p></div>")
    send_email(f"Regulatory digest: FSSAI / CAG / LM / CDSCO / DPIIT / CPCB - {len(items)} item(s)",
               body, "\n".join(text), dry)


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--digest", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state = load_state()

    instant, digest_news = collect_news(state)
    print(f"news: {len(instant)} instant, {len(digest_news)} queued for digest")
    if instant:
        send_news_emails(instant, a.dry_run)
    state["pending_news"].extend(digest_news)

    reg = collect_regulatory(state)
    print(f"regulatory: {len(reg)} new, {len(state['pending_reg'])} pending")

    if a.digest and state["pending_news"]:
        grouped_email(state["pending_news"], f"Competitor digest: e-com / FMCG / beauty - {len(state['pending_news'])} item(s)",
                      "Competitor digest: government action", NOTE, a.dry_run)
        state["pending_news"] = []
    if a.digest and state["pending_reg"]:
        digest_email(state["pending_reg"], a.dry_run)
        state["pending_reg"] = []

    if not a.dry_run:
        save_state(state)

if __name__ == "__main__":
    main()
