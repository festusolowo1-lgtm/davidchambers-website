"""
DAVID CHAMBERS — Database Layer
Works from any working directory via __file__ resolution
"""
import sqlite3, hashlib, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dc.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def hp(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS admin_users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        name TEXT DEFAULT 'Admin', role TEXT DEFAULT 'super_admin',
        active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);

    CREATE TABLE IF NOT EXISTS team(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, role TEXT NOT NULL, bar_year TEXT NOT NULL,
        bio TEXT DEFAULT '', photo TEXT DEFAULT '',
        active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0);

    CREATE TABLE IF NOT EXISTS pricing(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service TEXT NOT NULL, price TEXT NOT NULL, note TEXT DEFAULT '',
        active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0);

    CREATE TABLE IF NOT EXISTS bank(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_name TEXT NOT NULL, account_name TEXT NOT NULL, account_number TEXT NOT NULL);

    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        name TEXT NOT NULL, phone TEXT DEFAULT '',
        active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS cases(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL, case_ref TEXT UNIQUE NOT NULL,
        case_type TEXT NOT NULL, counsel TEXT NOT NULL,
        status TEXT DEFAULT 'Active', court TEXT DEFAULT '',
        filed_date TEXT DEFAULT '', next_date TEXT DEFAULT '', next_event TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id));

    CREATE TABLE IF NOT EXISTS timeline(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL, event_date TEXT NOT NULL,
        title TEXT NOT NULL, description TEXT DEFAULT '',
        status TEXT DEFAULT 'pending', sort_order INTEGER DEFAULT 0,
        FOREIGN KEY(case_id) REFERENCES cases(id));

    CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL, filename TEXT NOT NULL,
        file_type TEXT DEFAULT 'pdf', file_size TEXT DEFAULT '',
        upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(case_id) REFERENCES cases(id));

    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL, sender TEXT NOT NULL,
        sender_type TEXT DEFAULT 'firm', message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(case_id) REFERENCES cases(id));

    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL, invoice_ref TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL, amount TEXT NOT NULL,
        status TEXT DEFAULT 'Due', invoice_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(case_id) REFERENCES cases(id));

    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL,
        practice_area TEXT DEFAULT '', booking_date TEXT NOT NULL,
        booking_time TEXT NOT NULL, method TEXT DEFAULT 'Phone Call',
        notes TEXT DEFAULT '', status TEXT DEFAULT 'New',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS inquiries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL,
        practice_area TEXT DEFAULT '', message TEXT NOT NULL,
        status TEXT DEFAULT 'New', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)

    # Migrate columns if upgrading existing db
    for col, dflt in [("name","'Admin'"),("role","'super_admin'"),("active","1"),("created_at","CURRENT_TIMESTAMP")]:
        try: c.execute(f"ALTER TABLE admin_users ADD COLUMN {col} TEXT DEFAULT {dflt}")
        except: pass

    # Seed admin accounts
    c.execute("SELECT COUNT(*) FROM admin_users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO admin_users(email,password_hash,name,role) VALUES(?,?,?,?)",
                  ('admin@davidchambers.ng', hp('admin2025'), 'RESCAIVA Admin', 'rescavia_admin'))
    c.execute("INSERT OR IGNORE INTO admin_users(email,password_hash,name,role) VALUES(?,?,?,?)",
              ('owner@davidchambers.ng', hp('owner2025'), 'Barr. David Chambers', 'firm_owner'))

    # Seed settings
    for k, v in {
        'firm_name': 'DAVID CHAMBERS',
        'tagline':   'Legal Practitioners & Estate Consultants',
        'phone':     '08037098327',
        'whatsapp':  '2348037098327',
        'email':     'davidchambers542@yahoo.com',
        'address':   'Abuja FCT, Nigeria',
        'hours':     'Monday – Friday: 9:00 AM – 5:00 PM WAT',
        'logo':      '',
        'founded':   '2010',
        'nba':       'NBA Abuja Branch',
    }.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

    # Seed team
    c.execute("SELECT COUNT(*) FROM team")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO team(name,role,bar_year,photo,sort_order) VALUES(?,?,?,?,?)",
          ('Barr. Love Chinyere Ebunoluwa', 'Founder & Managing Partner', '2015', 'images/team/team_2.jpg', 0))

    # Seed pricing
    c.execute("SELECT COUNT(*) FROM pricing")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO pricing(service,price,note,sort_order) VALUES(?,?,?,?)", [
            ('Free Consultation',     '₦0',          '15 minutes, no obligation',      0),
            ('Document Review',       'From ₦25,000', '1–5 pages, 48hr turnaround',    1),
            ('Business Incorporation','From ₦75,000', 'Full CAC registration',          2),
            ('Immigration Support',   'From ₦50,000', 'Visa, CERPAC, permits',         3),
            ('Family Law Matters',    'From ₦100,000','Divorce, custody, inheritance', 4),
            ('Property Conveyancing', 'From ₦150,000',"Title, Governor's Consent",     5),
            ('Criminal Defense',      'From ₦120,000','Bail, trial, appeals',          6),
            ('Civil Litigation',      'Custom Quote', 'Based on case complexity',       7),
        ])

    # Seed bank
    c.execute("SELECT COUNT(*) FROM bank")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO bank(bank_name,account_name,account_number) VALUES(?,?,?)",
                  ('First Bank Nigeria', 'David Chambers', '0000000000'))

    # Seed demo client + case
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO clients(email,password_hash,name,phone) VALUES(?,?,?,?)",
                  ('demo@client.com', hp('demo123'), 'Demo Client', '08012345678'))
        cid = c.lastrowid
        c.execute("""INSERT INTO cases(client_id,case_ref,case_type,counsel,status,
                     court,filed_date,next_date,next_event) VALUES(?,?,?,?,?,?,?,?,?)""",
                  (cid,'DC-2025-001','Civil Litigation','Barr. David Chambers','Active',
                   'Federal High Court, Abuja','May 1, 2025','June 12, 2025','Court Hearing – 9:00 AM'))
        caid = c.lastrowid
        c.executemany("INSERT INTO timeline(case_id,event_date,title,description,status,sort_order) VALUES(?,?,?,?,?,?)",[
            (caid,'May 1, 2025',  'Case File Opened',      'Engagement letter signed. Retainer received.',          'done',    0),
            (caid,'May 10, 2025', 'Writ of Summons Filed', 'Filed at Federal High Court Registry.',                 'done',    1),
            (caid,'May 21, 2025', 'Hearing Date Assigned', 'Court assigned June 12, 2025.',                         'done',    2),
            (caid,'Jun 12, 2025', 'First Mention / Hearing','Appearance before Justice M. Okafor.',                 'current', 3),
            (caid,'TBD',          'Trial Date',            'To be fixed at first mention.',                          'pending', 4),
        ])
        c.executemany("INSERT INTO documents(case_id,filename,file_type,file_size,upload_date) VALUES(?,?,?,?,?)",[
            (caid,'Writ_of_Summons.pdf',      'pdf',  '234 KB','May 10, 2025'),
            (caid,'Engagement_Letter.pdf',    'pdf',  '120 KB','May 1, 2025'),
            (caid,'Statement_of_Claim.docx',  'word', '45 KB', 'May 8, 2025'),
        ])
        c.executemany("INSERT INTO messages(case_id,sender,sender_type,message,is_read,created_at) VALUES(?,?,?,?,?,?)",[
            (caid,'Barr. David Chambers','firm',
             'Court confirmed June 12, 2025 as hearing date. Please ensure all supporting documents are uploaded by June 10.',
             0,'May 21, 2025 2:34 PM'),
            (caid,'DC Legal Team','firm',
             'Writ of Summons successfully filed. We will update you once a hearing date is assigned.',
             1,'May 10, 2025 10:12 AM'),
        ])
        c.executemany("INSERT INTO invoices(case_id,invoice_ref,description,amount,status,invoice_date) VALUES(?,?,?,?,?,?)",[
            (caid,'INV-2025-001','Initial Retainer',   '₦150,000','Paid','May 1, 2025'),
            (caid,'INV-2025-002','Court Filing Fees',  '₦75,000', 'Due', 'May 10, 2025'),
        ])

    conn.commit()
    conn.close()
    print(f"✅ Database ready: {DB_PATH}")

if __name__ == '__main__':
    init_db()
