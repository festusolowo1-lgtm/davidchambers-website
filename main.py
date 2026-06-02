"""
DAVID CHAMBERS — FastAPI Backend v3.0 (Clean Rebuild)
Run:  python main.py          (local, from project root)
      uvicorn main:app ...    (Railway/production)
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, shutil, hashlib
from datetime import datetime, timedelta
from database import get_db, hp, init_db, DB_PATH

app = FastAPI(title="David Chambers v3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE    = _HERE
UPLOADS = os.path.join(BASE, "images", "uploads")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(os.path.join(BASE, "images", "team"), exist_ok=True)

# Static mounts
app.mount("/css",    StaticFiles(directory=os.path.join(BASE,"css")),    name="css")
app.mount("/js",     StaticFiles(directory=os.path.join(BASE,"js")),     name="js")
app.mount("/images", StaticFiles(directory=os.path.join(BASE,"images")), name="images")
app.mount("/pages",  StaticFiles(directory=os.path.join(BASE,"pages")),  name="pages")
app.mount("/guides", StaticFiles(directory=os.path.join(BASE,"guides")), name="guides")

@app.get("/")
def root(): return FileResponse(os.path.join(BASE,"index.html"))

@app.get("/index.html")
def index_html(): return FileResponse(os.path.join(BASE,"index.html"))

@app.get("/sw.js")
def sw(): return FileResponse(os.path.join(BASE,"sw.js"), media_type="application/javascript")

@app.get("/manifest.json")
def manifest(): return FileResponse(os.path.join(BASE,"manifest.json"), media_type="application/manifest+json")

# ── SESSIONS ─────────────────────────────────────────
_sessions: dict = {}

def make_token(uid:int, role:str, staff_role:str="") -> str:
    token = hashlib.sha256(f"{uid}{role}{staff_role}{datetime.now().isoformat()}".encode()).hexdigest()
    _sessions[token] = {"uid":uid,"role":role,"staff_role":staff_role,"exp":datetime.now()+timedelta(hours=12)}
    return token

def auth(token:str, role:str) -> dict:
    s = _sessions.get(token)
    if not s or s["exp"] < datetime.now() or s["role"] != role:
        raise HTTPException(401, "Unauthorized")
    return s

# ── MODELS ───────────────────────────────────────────
class Login(BaseModel):        email:str; password:str
class ClientMsg(BaseModel):    token:str; message:str
class ClientCreate(BaseModel): name:str; email:str; password:str; phone:Optional[str]=""
class CaseCreate(BaseModel):
    client_id:int; case_ref:str; case_type:str; counsel:str
    status:Optional[str]="Active"; court:Optional[str]=""; filed_date:Optional[str]=""
    next_date:Optional[str]=""; next_event:Optional[str]=""
class CaseUpdate(BaseModel):
    status:Optional[str]="Active"; court:Optional[str]=""
    next_date:Optional[str]=""; next_event:Optional[str]=""
class TimelineAdd(BaseModel):
    case_id:int; event_date:str; title:str
    description:Optional[str]=""; status:Optional[str]="pending"; sort_order:Optional[int]=99
class TimelineUpdate(BaseModel):
    event_date:str; title:str; description:Optional[str]=""; status:str
class InvoiceAdd(BaseModel):
    case_id:int; invoice_ref:str; description:str; amount:str; status:Optional[str]="Due"
class TeamAdd(BaseModel):
    name:str; role:str; bar_year:str; bio:Optional[str]=""; sort_order:Optional[int]=99
class PriceUpdate(BaseModel): service:str; price:str; note:Optional[str]=""
class BankUpdate(BaseModel):  bank_name:str; account_name:str; account_number:str
class MsgSend(BaseModel):     case_id:int; sender:str; message:str
class StaffCreate(BaseModel): name:str; email:str; password:str; role:str
class StaffUpdate(BaseModel): name:str; email:str; role:str
class BookingSubmit(BaseModel):
    name:str; phone:str; email:str; practice_area:Optional[str]=""
    booking_date:str; booking_time:str; method:Optional[str]="Phone Call"; notes:Optional[str]=""
class InquirySubmit(BaseModel):
    name:str; phone:str; email:str; practice_area:Optional[str]=""; message:str

# ══════════════════════════════════════════════════════
# PUBLIC (no auth)
# ══════════════════════════════════════════════════════

@app.get("/api/public/settings")
def pub_settings():
    db=get_db()
    rows=db.execute("SELECT key,value FROM settings WHERE key IN ('logo','firm_name','tagline','phone','email','address','hours')").fetchall()
    db.close(); return {r["key"]:r["value"] for r in rows}

@app.get("/api/public/team")
def pub_team():
    db=get_db()
    rows=[dict(r) for r in db.execute("SELECT name,role,bar_year,bio,photo FROM team WHERE active=1 ORDER BY sort_order").fetchall()]
    db.close(); return rows

@app.get("/api/public/pricing")
def pub_pricing():
    db=get_db()
    rows=[dict(r) for r in db.execute("SELECT service,price,note FROM pricing WHERE active=1 ORDER BY sort_order").fetchall()]
    db.close(); return rows

@app.post("/api/booking")
def submit_booking(body:BookingSubmit):
    db=get_db()
    db.execute("INSERT INTO bookings(name,phone,email,practice_area,booking_date,booking_time,method,notes) VALUES(?,?,?,?,?,?,?,?)",
               (body.name,body.phone,body.email,body.practice_area,body.booking_date,body.booking_time,body.method,body.notes))
    db.commit(); db.close()
    return {"ok":True,"message":f"Booking confirmed for {body.booking_date} at {body.booking_time}"}

@app.post("/api/contact")
def submit_inquiry(body:InquirySubmit):
    db=get_db()
    db.execute("INSERT INTO inquiries(name,phone,email,practice_area,message) VALUES(?,?,?,?,?)",
               (body.name,body.phone,body.email,body.practice_area,body.message))
    db.commit(); db.close()
    return {"ok":True,"message":"Message received. We will respond within 2 hours."}

@app.get("/api/health")
def health(): return {"status":"ok","db":os.path.exists(DB_PATH),"version":"3.0"}

# ══════════════════════════════════════════════════════
# CLIENT PORTAL
# ══════════════════════════════════════════════════════

@app.post("/api/client/login")
def client_login(body:Login):
    db=get_db()
    row=db.execute("SELECT id,name FROM clients WHERE email=? AND password_hash=? AND active=1",
                   (body.email.lower().strip(),hp(body.password))).fetchone()
    db.close()
    if not row: raise HTTPException(401,"Incorrect email or password")
    return {"token":make_token(row["id"],"client"),"name":row["name"]}

@app.get("/api/client/dashboard")
def client_dashboard(token:str):
    s=auth(token,"client"); db=get_db()
    case=db.execute("SELECT * FROM cases WHERE client_id=? ORDER BY id DESC LIMIT 1",(s["uid"],)).fetchone()
    if not case: db.close(); return {"case":None}
    cid=case["id"]
    tl   =[dict(r) for r in db.execute("SELECT * FROM timeline  WHERE case_id=? ORDER BY sort_order",(cid,))]
    docs =[dict(r) for r in db.execute("SELECT * FROM documents WHERE case_id=? ORDER BY id DESC",(cid,))]
    msgs =[dict(r) for r in db.execute("SELECT * FROM messages  WHERE case_id=? ORDER BY id DESC",(cid,))]
    invs =[dict(r) for r in db.execute("SELECT * FROM invoices  WHERE case_id=? ORDER BY id",(cid,))]
    bank =db.execute("SELECT * FROM bank ORDER BY id DESC LIMIT 1").fetchone()
    unread=db.execute("SELECT COUNT(*) FROM messages WHERE case_id=? AND is_read=0 AND sender_type='firm'",(cid,)).fetchone()[0]
    db.execute("UPDATE messages SET is_read=1 WHERE case_id=? AND sender_type='firm'",(cid,))
    db.commit(); db.close()
    return {"case":dict(case),"timeline":tl,"documents":docs,"messages":msgs,
            "invoices":invs,"bank":dict(bank) if bank else {},"unread":unread}

@app.post("/api/client/message")
def client_message(body:ClientMsg):
    s=auth(body.token,"client"); db=get_db()
    case=db.execute("SELECT id FROM cases WHERE client_id=? ORDER BY id DESC LIMIT 1",(s["uid"],)).fetchone()
    if not case: db.close(); raise HTTPException(404,"No case found")
    now=datetime.now().strftime("%b %d, %Y %I:%M %p")
    db.execute("INSERT INTO messages(case_id,sender,sender_type,message,is_read,created_at) VALUES(?,?,?,?,?,?)",
               (case["id"],"Client","client",body.message,1,now))
    db.commit(); db.close(); return {"ok":True}

@app.post("/api/client/logout")
def client_logout(token:str): _sessions.pop(token,None); return {"ok":True}

# ══════════════════════════════════════════════════════
# ADMIN AUTH + STAFF
# ══════════════════════════════════════════════════════

@app.post("/api/admin/login")
def admin_login(body:Login):
    db=get_db()
    row=db.execute("SELECT id,name,role FROM admin_users WHERE email=? AND password_hash=? AND active=1",
                   (body.email.lower().strip(),hp(body.password))).fetchone()
    db.close()
    if not row: raise HTTPException(401,"Incorrect credentials")
    token=make_token(row["id"],"admin",row["role"])
    return {"token":token,"name":row["name"],"role":row["role"]}

@app.get("/api/admin/staff")
def get_staff(token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT id,name,email,role,active,created_at FROM admin_users ORDER BY id").fetchall()]
    db.close(); return rows

@app.post("/api/admin/staff")
def add_staff(token:str, body:StaffCreate):
    s=auth(token,"admin")
    if s["staff_role"] not in("rescavia_admin","firm_owner","super_admin"): raise HTTPException(403,"Insufficient permission")
    if body.role not in("firm_owner","super_admin","case_manager","receptionist"): raise HTTPException(400,"Invalid role")
    db=get_db()
    try:
        db.execute("INSERT INTO admin_users(email,password_hash,name,role) VALUES(?,?,?,?)",(body.email.lower(),hp(body.password),body.name,body.role))
        db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close()
        return {"id":new_id,"ok":True}
    except sqlite3.IntegrityError: db.close(); raise HTTPException(400,"Email already exists")

@app.delete("/api/admin/staff/{sid}")
def delete_staff(sid:int, token:str):
    s=auth(token,"admin")
    if s["staff_role"] not in("rescavia_admin","firm_owner","super_admin"): raise HTTPException(403,"Insufficient permission")
    if s["uid"]==sid: raise HTTPException(400,"Cannot delete your own account")
    db=get_db(); db.execute("UPDATE admin_users SET active=0 WHERE id=?",(sid,)); db.commit(); db.close(); return {"ok":True}

@app.post("/api/admin/staff/{sid}/reset-password")
def reset_pwd(sid:int, token:str, new_password:str):
    s=auth(token,"admin")
    if s["staff_role"] not in("rescavia_admin","firm_owner","super_admin"): raise HTTPException(403,"Insufficient permission")
    db=get_db(); db.execute("UPDATE admin_users SET password_hash=? WHERE id=?",(hp(new_password),sid)); db.commit(); db.close(); return {"ok":True}

# ══════════════════════════════════════════════════════
# ADMIN: DASHBOARD + CLIENTS + CASES
# ══════════════════════════════════════════════════════

@app.get("/api/admin/stats")
def admin_stats(token:str):
    auth(token,"admin"); db=get_db()
    data={"clients":db.execute("SELECT COUNT(*) FROM clients WHERE active=1").fetchone()[0],
          "cases_active":db.execute("SELECT COUNT(*) FROM cases WHERE status='Active'").fetchone()[0],
          "bookings_new":db.execute("SELECT COUNT(*) FROM bookings WHERE status='New'").fetchone()[0],
          "inquiries_new":db.execute("SELECT COUNT(*) FROM inquiries WHERE status='New'").fetchone()[0],
          "bookings":[dict(r) for r in db.execute("SELECT * FROM bookings ORDER BY created_at DESC LIMIT 20")],
          "inquiries":[dict(r) for r in db.execute("SELECT * FROM inquiries ORDER BY created_at DESC LIMIT 20")]}
    db.close(); return data

@app.get("/api/admin/clients")
def get_clients(token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT id,name,email,phone,created_at,active FROM clients ORDER BY id DESC").fetchall()]
    db.close(); return rows

@app.post("/api/admin/clients")
def add_client(token:str, body:ClientCreate):
    auth(token,"admin"); db=get_db()
    try:
        db.execute("INSERT INTO clients(email,password_hash,name,phone) VALUES(?,?,?,?)",(body.email.lower(),hp(body.password),body.name,body.phone))
        db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close()
        return {"id":new_id,"ok":True}
    except sqlite3.IntegrityError: db.close(); raise HTTPException(400,"Email already exists")

@app.get("/api/admin/cases")
def get_cases(token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT c.*,cl.name AS client_name,cl.email AS client_email FROM cases c JOIN clients cl ON c.client_id=cl.id ORDER BY c.id DESC").fetchall()]
    db.close(); return rows

@app.post("/api/admin/cases")
def add_case(token:str, body:CaseCreate):
    auth(token,"admin"); db=get_db()
    try:
        db.execute("INSERT INTO cases(client_id,case_ref,case_type,counsel,status,court,filed_date,next_date,next_event) VALUES(?,?,?,?,?,?,?,?,?)",
                   (body.client_id,body.case_ref,body.case_type,body.counsel,body.status,body.court,body.filed_date,body.next_date,body.next_event))
        db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close(); return {"id":new_id,"ok":True}
    except sqlite3.IntegrityError: db.close(); raise HTTPException(400,"Case reference already exists")

@app.put("/api/admin/cases/{cid}")
def update_case(cid:int, token:str, body:CaseUpdate):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE cases SET status=?,court=?,next_date=?,next_event=? WHERE id=?",(body.status,body.court,body.next_date,body.next_event,cid))
    db.commit(); db.close(); return {"ok":True}

# ══════════════════════════════════════════════════════
# ADMIN: TIMELINE, MESSAGES, DOCUMENTS, INVOICES
# ══════════════════════════════════════════════════════

@app.get("/api/admin/timeline/{case_id}")
def get_timeline(case_id:int, token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT * FROM timeline WHERE case_id=? ORDER BY sort_order",(case_id,)).fetchall()]
    db.close(); return rows

@app.post("/api/admin/timeline")
def add_timeline(token:str, body:TimelineAdd):
    auth(token,"admin"); db=get_db()
    db.execute("INSERT INTO timeline(case_id,event_date,title,description,status,sort_order) VALUES(?,?,?,?,?,?)",
               (body.case_id,body.event_date,body.title,body.description,body.status,body.sort_order))
    db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close(); return {"id":new_id,"ok":True}

@app.put("/api/admin/timeline/{tid}")
def update_timeline(tid:int, token:str, body:TimelineUpdate):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE timeline SET event_date=?,title=?,description=?,status=? WHERE id=?",(body.event_date,body.title,body.description,body.status,tid))
    db.commit(); db.close(); return {"ok":True}

@app.delete("/api/admin/timeline/{tid}")
def delete_timeline(tid:int, token:str):
    auth(token,"admin"); db=get_db()
    db.execute("DELETE FROM timeline WHERE id=?",(tid,)); db.commit(); db.close(); return {"ok":True}

@app.get("/api/admin/messages/{case_id}")
def get_messages(case_id:int, token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT * FROM messages WHERE case_id=? ORDER BY id",(case_id,)).fetchall()]
    db.execute("UPDATE messages SET is_read=1 WHERE case_id=? AND sender_type='client'",(case_id,))
    db.commit(); db.close(); return rows

@app.post("/api/admin/messages")
def send_message(token:str, body:MsgSend):
    auth(token,"admin"); now=datetime.now().strftime("%b %d, %Y %I:%M %p"); db=get_db()
    db.execute("INSERT INTO messages(case_id,sender,sender_type,message,is_read,created_at) VALUES(?,?,?,?,?,?)",
               (body.case_id,body.sender,"firm",body.message,0,now))
    db.commit(); db.close(); return {"ok":True}

@app.get("/api/admin/documents/{case_id}")
def get_documents(case_id:int, token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT * FROM documents WHERE case_id=? ORDER BY id DESC",(case_id,)).fetchall()]
    db.close(); return rows

@app.post("/api/admin/documents/{case_id}")
def upload_document(case_id:int, token:str, file:UploadFile=File(...)):
    auth(token,"admin")
    ext=os.path.splitext(file.filename)[1].lower()
    fname=f"case{case_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    data=file.file.read()
    with open(os.path.join(UPLOADS,fname),"wb") as f: f.write(data)
    ftype="pdf" if ext==".pdf" else "word" if ext in(".doc",".docx") else "image"
    today=datetime.now().strftime("%b %d, %Y"); db=get_db()
    db.execute("INSERT INTO documents(case_id,filename,file_type,file_size,upload_date) VALUES(?,?,?,?,?)",
               (case_id,file.filename,ftype,f"{max(len(data)//1024,1)} KB",today))
    db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close()
    return {"id":new_id,"filename":file.filename,"ok":True}

@app.post("/api/admin/invoices")
def add_invoice(token:str, body:InvoiceAdd):
    auth(token,"admin"); today=datetime.now().strftime("%b %d, %Y"); db=get_db()
    try:
        db.execute("INSERT INTO invoices(case_id,invoice_ref,description,amount,status,invoice_date) VALUES(?,?,?,?,?,?)",
                   (body.case_id,body.invoice_ref,body.description,body.amount,body.status,today))
        db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close(); return {"id":new_id,"ok":True}
    except sqlite3.IntegrityError: db.close(); raise HTTPException(400,"Invoice reference already exists")

@app.put("/api/admin/invoices/{iid}/status")
def update_invoice(iid:int, token:str, status:str):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE invoices SET status=? WHERE id=?",(status,iid)); db.commit(); db.close(); return {"ok":True}

# ══════════════════════════════════════════════════════
# ADMIN: TEAM, PRICING, BANK, LOGO, SETTINGS
# ══════════════════════════════════════════════════════

@app.get("/api/admin/team")
def get_team(token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT * FROM team WHERE active=1 ORDER BY sort_order").fetchall()]
    db.close(); return rows

@app.post("/api/admin/team")
def add_team(token:str, body:TeamAdd):
    auth(token,"admin"); db=get_db()
    db.execute("INSERT INTO team(name,role,bar_year,bio,sort_order) VALUES(?,?,?,?,?)",(body.name,body.role,body.bar_year,body.bio,body.sort_order))
    db.commit(); new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; db.close(); return {"id":new_id,"ok":True}

@app.put("/api/admin/team/{tid}")
def update_team(tid:int, token:str, body:TeamAdd):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE team SET name=?,role=?,bar_year=?,bio=? WHERE id=?",(body.name,body.role,body.bar_year,body.bio,tid))
    db.commit(); db.close(); return {"ok":True}

@app.delete("/api/admin/team/{tid}")
def delete_team(tid:int, token:str):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE team SET active=0 WHERE id=?",(tid,)); db.commit(); db.close(); return {"ok":True}

@app.post("/api/admin/team/{tid}/photo")
def upload_team_photo(tid:int, token:str, file:UploadFile=File(...)):
    auth(token,"admin")
    ext=os.path.splitext(file.filename)[1].lower() or ".jpg"
    fname=f"team_{tid}{ext}"; path=os.path.join(BASE,"images","team",fname)
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)
    url=f"images/team/{fname}"; db=get_db()
    db.execute("UPDATE team SET photo=? WHERE id=?",(url,tid)); db.commit(); db.close()
    return {"photo":url,"ok":True}

@app.get("/api/admin/pricing")
def get_pricing(token:str):
    auth(token,"admin"); db=get_db()
    rows=[dict(r) for r in db.execute("SELECT * FROM pricing WHERE active=1 ORDER BY sort_order").fetchall()]
    db.close(); return rows

@app.put("/api/admin/pricing/{pid}")
def update_pricing(pid:int, token:str, body:PriceUpdate):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE pricing SET service=?,price=?,note=? WHERE id=?",(body.service,body.price,body.note,pid))
    db.commit(); db.close(); return {"ok":True}

@app.get("/api/admin/bank")
def get_bank(token:str):
    auth(token,"admin"); db=get_db()
    row=db.execute("SELECT * FROM bank ORDER BY id DESC LIMIT 1").fetchone()
    db.close(); return dict(row) if row else {}

@app.post("/api/admin/bank")
def update_bank(token:str, body:BankUpdate):
    auth(token,"admin"); db=get_db()
    db.execute("DELETE FROM bank")
    db.execute("INSERT INTO bank(bank_name,account_name,account_number) VALUES(?,?,?)",(body.bank_name,body.account_name,body.account_number))
    db.commit(); db.close(); return {"ok":True}

@app.post("/api/admin/logo")
def upload_logo(token:str, file:UploadFile=File(...)):
    s=auth(token,"admin")
    if s["staff_role"] not in("rescavia_admin","firm_owner"):
        raise HTTPException(403,"Logo management: RESCAIVA or Firm Owner only")
    ext=os.path.splitext(file.filename)[1].lower() or ".png"
    path=os.path.join(BASE,"images",f"logo{ext}")
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)
    db=get_db(); db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",("logo",f"images/logo{ext}"))
    db.commit(); db.close(); return {"logo":f"images/logo{ext}","ok":True}

@app.put("/api/admin/bookings/{bid}/status")
def booking_status(bid:int, token:str, status:str):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE bookings SET status=? WHERE id=?",(status,bid)); db.commit(); db.close(); return {"ok":True}

@app.put("/api/admin/inquiries/{iid}/status")
def inquiry_status(iid:int, token:str, status:str):
    auth(token,"admin"); db=get_db()
    db.execute("UPDATE inquiries SET status=? WHERE id=?",(status,iid)); db.commit(); db.close(); return {"ok":True}

# ── STARTUP ──────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    port = os.environ.get("PORT", "8000")
    print(f"\n{'='*50}\n  DAVID CHAMBERS v3.0 — PORT {port}\n  http://localhost:{port}\n{'='*50}\n")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
