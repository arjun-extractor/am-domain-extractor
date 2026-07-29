import streamlit as st
import sqlite3
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from concurrent.futures import ThreadPoolExecutor
import time
import threading
import pandas as pd
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="AM Domain Extractor Pro", layout="wide")

# Custom UI Styling
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #ffffff; }
    
    div[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        width: 320px !important;
    }

    .sidebar-title {
        font-size: 1.8rem !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        margin-bottom: 5px !important;
    }
    
    .sidebar-subhead {
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        color: #38bdf8 !important;
        margin-top: 15px !important;
        margin-bottom: 10px !important;
        text-transform: uppercase;
    }

    div[data-testid="stSidebar"] div.stButton > button {
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        padding: 0.8rem 1rem !important;
        border-radius: 10px !important;
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 2px solid #3b82f6 !important;
        text-align: left !important;
        margin-bottom: 8px !important;
        width: 100% !important;
    }

    div[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    .stMetric { 
        background-color: #161f30; 
        padding: 14px !important; 
        border-radius: 12px !important; 
        border: 2px solid #2a3b5c !important; 
    }
    
    .big-title {
        font-size: 2.3rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }
    .big-subtitle {
        font-size: 1.1rem !important;
        color: #94a3b8 !important;
        margin-bottom: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Database Setup with Upgrades
def init_db():
    conn = sqlite3.connect("leads.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            expiry_date TEXT,
            domain_limit INTEGER DEFAULT 1000,
            role TEXT DEFAULT 'User'
        )
    ''')
    
    cursor.execute("PRAGMA table_info(users)")
    u_cols = [col[1] for col in cursor.fetchall()]
    if 'domain_limit' not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN domain_limit INTEGER DEFAULT 1000")

    # Default Admin Creation
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, status, role, domain_limit) VALUES ('admin', 'admin123', 'Approved', 'Admin', -1)")

    # Domains Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            keyword TEXT,
            country TEXT,
            location TEXT,
            domain TEXT UNIQUE,
            full_url TEXT,
            email TEXT DEFAULT 'N/A',
            phone TEXT DEFAULT 'N/A',
            has_ssl TEXT DEFAULT 'Yes',
            speed_status TEXT DEFAULT 'Fast',
            status TEXT,
            session_id INTEGER DEFAULT 0
        )
    ''')
    
    # Activity Logs Table (For Admin Analytics)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            timestamp TEXT
        )
    ''')

    # System Stats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_stats (
            id INTEGER PRIMARY KEY,
            progress INTEGER,
            skipped INTEGER,
            is_running INTEGER,
            current_session_id INTEGER DEFAULT 0,
            processed_queries INTEGER DEFAULT 0,
            total_queries INTEGER DEFAULT 0,
            current_query TEXT DEFAULT ''
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO system_stats (id, progress, skipped, is_running, current_session_id, processed_queries, total_queries, current_query) VALUES (1, 0, 0, 0, 0, 0, 0, '')")
    conn.commit()
    conn.close()

init_db()

def log_activity(u_id, username, action):
    try:
        conn = sqlite3.connect("leads.db", check_same_thread=False)
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO activity_logs (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)", (u_id, username, action, now_str))
        conn.commit()
        conn.close()
    except Exception:
        pass

# Session State Setup
if "user_logged_in" not in st.session_state:
    st.session_state["user_logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Dashboard"

# LOGIN / SIGNUP PAGE
if not st.session_state["user_logged_in"]:
    st.markdown("<h1 style='text-align: center;'>⚡ AM Domain Extractor Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8;'>Client Access Portal • Login or Request Access</p>", unsafe_allow_html=True)
    st.markdown("---")

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Request Account (Sign Up)"])

        with tab1:
            login_user = st.text_input("Username", key="l_user")
            login_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", type="primary", use_container_width=True):
                conn = sqlite3.connect("leads.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, password, status, expiry_date, role, domain_limit FROM users WHERE username=?", (login_user,))
                user = cursor.fetchone()
                conn.close()

                if user:
                    u_id, u_name, u_pass, u_status, u_expiry, u_role, u_limit = user
                    if u_pass != login_pass:
                        st.error("Incorrect Password!")
                    elif u_status == "Pending":
                        st.warning("⏳ Aapka account approval ke liye pending hai. Admin se approval ke baad hi login ho sakega.")
                    elif u_status in ["Rejected", "Revoked"]:
                        st.error("❌ Aapka account access disable kar diya gaya hai.")
                    elif u_role != "Admin" and u_expiry:
                        exp_dt = datetime.strptime(u_expiry, "%Y-%m-%d").date()
                        if datetime.now().date() > exp_dt:
                            st.error("⚠️ Aapke account ka access subscription period expire ho chuka hai!")
                        else:
                            st.session_state["user_logged_in"] = True
                            st.session_state["user_info"] = {"id": u_id, "username": u_name, "role": u_role, "expiry": u_expiry, "limit": u_limit}
                            log_activity(u_id, u_name, "User Logged In")
                            st.rerun()
                    else:
                        st.session_state["user_logged_in"] = True
                        st.session_state["user_info"] = {"id": u_id, "username": u_name, "role": u_role, "expiry": u_expiry, "limit": u_limit}
                        log_activity(u_id, u_name, "User Logged In")
                        st.rerun()
                else:
                    st.error("User not found!")

        with tab2:
            signup_user = st.text_input("Create Username", key="s_user")
            signup_pass = st.text_input("Create Password", type="password", key="s_pass")
            if st.button("Submit Request for Approval", use_container_width=True):
                if signup_user and signup_pass:
                    try:
                        conn = sqlite3.connect("leads.db")
                        cursor = conn.cursor()
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        cursor.execute("INSERT INTO users (username, password, status, created_at, role, domain_limit) VALUES (?, ?, 'Pending', ?, 'User', 1000)", (signup_user, signup_pass, now_str))
                        conn.commit()
                        conn.close()
                        st.success("✅ Account request submit ho gayi hai! Admin approval ke baad aap login kar sakenge.")
                    except sqlite3.IntegrityError:
                        st.error("Username pehle se exist karta hai.")
                else:
                    st.warning("Sabhi fields fill karein.")
    st.stop()

# LOGGED IN APP CODE
current_user = st.session_state["user_info"]

def update_sys_stats(progress=0, skipped=0, is_running=0, session_id=0, processed=0, total=0, current_q=""):
    conn = sqlite3.connect("leads.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE system_stats 
        SET progress=?, skipped=?, is_running=?, current_session_id=?, processed_queries=?, total_queries=?, current_query=?
        WHERE id=1
    ''', (progress, skipped, is_running, session_id, processed, total, current_q))
    conn.commit()
    conn.close()

INVALID_EXTENSIONS = ('.gov', '.edu', '.org', '.xyz', '.biz', '.info', '.top', '.online', '.site', '.wiki', '.mil')
EXACT_BLOCKED_DOMAINS = {
    'yahoo.com', 'bing.com', 'google.com', 'duckduckgo.com', 'facebook.com', 'instagram.com',
    'twitter.com', 'linkedin.com', 'wikipedia.org', 'youtube.com', 'pinterest.com', 'reddit.com',
    'yelp.com', 'yellowpages.com', 'angi.com', 'thumbtack.com', 'bbb.org'
}

def is_clean_domain(domain):
    if not domain or "." not in domain or len(domain) < 4 or domain.count("-") > 2:
        return False
    if domain.endswith(INVALID_EXTENSIONS) or domain in EXACT_BLOCKED_DOMAINS:
        return False
    return True

def audit_and_extract_contact(target_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'}
    email = "N/A"
    phone = "N/A"
    has_ssl = "Yes" if target_url.startswith("https") else "No"
    speed = "Fast"

    try:
        start_time = time.time()
        res = requests.get(target_url, headers=headers, timeout=5)
        load_time = time.time() - start_time
        
        if load_time > 2.5:
            speed = "Slow"
            
        if res.status_code == 200:
            text = res.text
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.webp', '.svg'))]
            if valid_emails:
                email = valid_emails[0]
            
            phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            if phones:
                phone = phones[0]
    except Exception:
        has_ssl = "No"
        speed = "Slow"

    return email, phone, has_ssl, speed

def scrape_multi_engine(kw, loc, country, session_id, u_id):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'}
    query = f"{kw} {loc} {country}"
    encoded_query = urllib.parse.quote_plus(query)
    target_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    extracted_leads = []
    skipped = 0
    
    try:
        res = requests.get(target_url, headers=headers, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                if len(extracted_leads) >= 20:
                    break

                href = a['href']
                if 'uddg=' in href:
                    match = re.search(r'uddg=([^&]+)', href)
                    clean_url = urllib.parse.unquote(match.group(1)) if match else href
                else:
                    clean_url = href
                
                if not clean_url.startswith('http'):
                    continue
                
                parsed = urllib.parse.urlparse(clean_url)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                
                if is_clean_domain(domain):
                    email, phone, ssl, speed = audit_and_extract_contact(clean_url)
                    extracted_leads.append((u_id, kw, country, loc, domain, clean_url, email, phone, ssl, speed, session_id))
                else:
                    skipped += 1
    except Exception:
        pass

    if extracted_leads:
        conn = sqlite3.connect("leads.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR IGNORE INTO domains (user_id, keyword, country, location, domain, full_url, email, phone, has_ssl, speed_status, status, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
        ''', extracted_leads)
        conn.commit()
        conn.close()

    return skipped, query

def run_scraper_parallel(keywords, locations, country, session_id, u_id):
    max_threads = 5
    all_tasks = [(kw, loc) for kw in keywords for loc in locations]
    
    conn = sqlite3.connect("leads.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT keyword, location FROM domains WHERE country=? AND user_id=?", (country, u_id))
    completed_pairs = set(cursor.fetchall())
    conn.close()
    
    remaining_tasks = [(kw, loc) for kw, loc in all_tasks if (kw, loc) not in completed_pairs]
    total_queries = len(all_tasks)
    processed = total_queries - len(remaining_tasks)
    total_skipped = 0
    
    update_sys_stats(
        progress=int((processed / total_queries) * 100) if total_queries else 0,
        skipped=0, is_running=1, session_id=session_id,
        processed=processed, total=total_queries, current_q="Extracting..."
    )
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for kw, loc in remaining_tasks:
            chk_conn = sqlite3.connect("leads.db", check_same_thread=False)
            chk_cur = chk_conn.cursor()
            chk_cur.execute("SELECT is_running FROM system_stats WHERE id=1")
            run_status = chk_cur.fetchone()[0]
            chk_conn.close()
            
            if run_status == 0:
                break
                
            f = executor.submit(scrape_multi_engine, kw, loc, country, session_id, u_id)
            futures.append(f)
            
        for future in futures:
            try:
                sk, last_q = future.result()
                total_skipped += sk
                processed += 1
                prog = int((processed / total_queries) * 100)
                update_sys_stats(prog, total_skipped, 1, session_id, processed, total_queries, last_q)
            except Exception:
                pass

    update_sys_stats(100, total_skipped, 0, session_id, processed, total_queries, "Completed")

# --- SIDEBAR UI ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚡ AM Domain Pro</div>', unsafe_allow_html=True)
    st.caption(f"👤 Logged as: *{current_user['username']}* ({current_user['role']})")
    
    if current_user["expiry"]:
        st.caption(f"⏳ Expiry: *{current_user['expiry']}*")
        
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["user_logged_in"] = False
        st.session_state["user_info"] = None
        st.rerun()

    st.markdown('<div class="sidebar-subhead">NAVIGATION</div>', unsafe_allow_html=True)
    
    if st.button("📊 DASHBOARD", use_container_width=True):
        st.session_state["nav_page"] = "Dashboard"
        st.rerun()
        
    if st.button("📥 DOWNLOAD RESULTS", use_container_width=True):
        st.session_state["nav_page"] = "Download"
        st.rerun()

    if st.button("✉️ COLD PITCH TEMPLATES", use_container_width=True):
        st.session_state["nav_page"] = "Templates"
        st.rerun()

    if current_user["role"] == "Admin":
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        if st.button("👑 ADMIN CONTROL PANEL", use_container_width=True):
            st.session_state["nav_page"] = "AdminPanel"
            st.rerun()
        
    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

    try:
        conn = sqlite3.connect("leads.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT progress, skipped, is_running, current_session_id, processed_queries, total_queries FROM system_stats WHERE id=1")
        stat_row = cursor.fetchone()
        live_prog = stat_row[0] if stat_row else 0
        live_skipped = stat_row[1] if stat_row else 0
        live_running = stat_row[2] if stat_row else 0
        active_session = stat_row[3] if stat_row else 0
        proc_q = stat_row[4] if stat_row else 0
        tot_q = stat_row[5] if stat_row else 0
        
        cursor.execute("SELECT COUNT(*) FROM domains WHERE session_id=? AND user_id=?", (active_session, current_user["id"]))
        fresh_domains = cursor.fetchone()[0] if active_session > 0 else 0
        
        cursor.execute("SELECT COUNT(*) FROM domains WHERE user_id=?", (current_user["id"],))
        total_domains = cursor.fetchone()[0]
        conn.close()
    except Exception:
        fresh_domains, total_domains, live_prog, live_skipped, live_running, proc_q, tot_q, active_session = 0, 0, 0, 0, 0, 0, 0, 0

    st.metric("📊 Extract Progress", f"{live_prog}%")
    st.metric("🔥 Today / Current Run Domains", fresh_domains)
    st.metric("📂 Directories Blocked", live_skipped)
    
    # Quota Display
    limit_txt = "Unlimited" if current_user["limit"] == -1 else f"{total_domains} / {current_user['limit']}"
    st.metric("🗄️ Domain Quota Used", limit_txt)

# --- DASHBOARD PAGE ---
if st.session_state["nav_page"] == "Dashboard":
    st.markdown("<p class='big-title'>🚀 AM Domain Extractor Pro</p>", unsafe_allow_html=True)
    st.markdown("<p class='big-subtitle'>Clean Local Business Domain Extractor • Speed Locked (5 Threads, 1-20 Limits)</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Check Quota Exceeded
    if current_user["role"] != "Admin" and current_user["limit"] != -1 and total_domains >= current_user["limit"]:
        st.error(f"⚠️ Aapka Domain Extraction Quota Limit ({current_user['limit']} Domains) reach ho gaya hai. Agle run ke liye admin se limit extend karayein.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        target_country = st.selectbox("1. Target Country", ["United States", "India", "United Kingdom", "Canada", "Australia"])
    with col2:
        user_keywords = st.text_area("2. Keywords (One per line)", value=st.session_state.get("kw_val", ""), height=140, placeholder="E.g.\nPLUMBER\nROOFER")
    with col3:
        user_locations = st.text_area("3. Cities / States (One per line)", value=st.session_state.get("loc_val", ""), height=140, placeholder="E.g.\nTEXAS\nMUMBAI")

    col_b1, col_b2, col_b3 = st.columns([2, 2, 1])
    with col_b1:
        start_btn = st.button("🚀 Start Extraction Process", type="primary", use_container_width=True)
    with col_b2:
        pause_btn = st.button("⏹️ Pause / Stop Extraction", use_container_width=True)
    with col_b3:
        clear_btn = st.button("🔄 Clear Inputs & Reset", use_container_width=True)

    if clear_btn:
        st.session_state["kw_val"] = ""
        st.session_state["loc_val"] = ""
        update_sys_stats(0, 0, 0, 0, 0, 0, "")
        st.rerun()

    if start_btn:
        if current_user["role"] != "Admin" and current_user["limit"] != -1 and total_domains >= current_user["limit"]:
            st.error("Quota exceeded! Contact Admin.")
        else:
            kw_list = [k.strip() for k in user_keywords.split("\n") if k.strip()]
            loc_list = [l.strip() for l in user_locations.split("\n") if l.strip()]
            
            if kw_list and loc_list:
                if live_running == 0:
                    new_session_id = int(time.time())
                    st.session_state["kw_val"] = user_keywords
                    st.session_state["loc_val"] = user_locations
                    
                    log_activity(current_user["id"], current_user["username"], f"Started Extraction for {len(kw_list)} KWs, {len(loc_list)} Locs")
                    threading.Thread(target=run_scraper_parallel, args=(kw_list, loc_list, target_country, new_session_id, current_user["id"]), daemon=True).start()
                    time.sleep(1)
                    st.rerun()

    if pause_btn:
        update_sys_stats(live_prog, live_skipped, 0, active_session, proc_q, tot_q, "Stopped")
        st.rerun()

    st.markdown("---")
    if live_running == 1:
        st.info(f"⚡ *Extraction Active...* Processed: {proc_q}/{tot_q} queries")
        st.progress(live_prog / 100)

    st.markdown("<h3 style='margin-top: 15px;'>Live Extracted Data Stream (Current Run Only)</h3>", unsafe_allow_html=True)
    try:
        conn = sqlite3.connect("leads.db", check_same_thread=False)
        df_live = pd.read_sql(
            "SELECT keyword AS 'Keyword', location AS 'Region', domain AS 'Clean Domain', email AS 'Email', phone AS 'Phone', has_ssl AS 'SSL Status', speed_status AS 'Site Speed', full_url AS 'Full URL' FROM domains WHERE session_id = ? AND user_id = ? ORDER BY id DESC LIMIT 50",
            conn, params=(active_session, current_user["id"])
        )
        conn.close()
        if not df_live.empty and active_session > 0:
            st.dataframe(df_live, use_container_width=True, height=350)
        else:
            st.info("Iss session me abhi tak naye domains nahi mile hain. Scraper start karein.")
    except Exception as e:
        st.error(f"Error: {e}")

    if live_running == 1:
        time.sleep(1.5)
        st.rerun()

# --- DOWNLOAD RESULTS PAGE ---
elif st.session_state["nav_page"] == "Download":
    st.markdown("<p class='big-title'>📥 Download Results & Export Data</p>", unsafe_allow_html=True)
    st.markdown("<p class='big-subtitle'>Export clean business domains extracted by the tool</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        download_scope = st.selectbox("1. Data Scope to Download", ["🔥 Current Run Only (Naye Domains)", "🗄️ All Time Saved Database"])
    with col_f2:
        ssl_filter = st.selectbox("2. Filter by SSL Status", ["All Domains", "Missing SSL", "Valid SSL"])
    with col_f3:
        email_filter = st.selectbox("3. Filter by Email Availability", ["All Domains", "Only Domains with Email Found"])
        
    try:
        conn = sqlite3.connect("leads.db", check_same_thread=False)
        query_sql = "SELECT keyword AS 'Keyword', country AS 'Country', location AS 'Region', domain AS 'Clean Domain', email AS 'Email', phone AS 'Phone', has_ssl AS 'SSL Status', speed_status AS 'Site Speed', full_url AS 'Full URL' FROM domains WHERE user_id = ?"
        params = [current_user["id"]]

        if download_scope == "🔥 Current Run Only (Naye Domains)":
            query_sql += " AND session_id = ?"
            params.append(active_session)
            
        if ssl_filter == "Missing SSL":
            query_sql += " AND has_ssl = 'No'"
        elif ssl_filter == "Valid SSL":
            query_sql += " AND has_ssl = 'Yes'"
            
        if email_filter == "Only Domains with Email Found":
            query_sql += " AND email != 'N/A'"

        df_all = pd.read_sql(query_sql, conn, params=params)
        conn.close()
        
        if not df_all.empty:
            csv_data = df_all.to_csv(index=False).encode('utf-8')
            filename = "Current_Run_Domains.csv" if download_scope.startswith("🔥") else "All_Business_Domains.csv"
            st.download_button(f"📥 Download CSV ({len(df_all)} Domains)", csv_data, filename, "text/csv", use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(df_all, use_container_width=True, height=500)
        else:
            st.warning("Iss selection me abhi koi domains nahi hain.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- COLD PITCH TEMPLATES PAGE ---
elif st.session_state["nav_page"] == "Templates":
    st.markdown("<p class='big-title'>✉️ B2B Outreach Pitch Templates</p>", unsafe_allow_html=True)
    st.markdown("<p class='big-subtitle'>Copy-paste high converting pitches designed for Web Design and SEO outreach</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.subheader("1. Web Redesign Pitch (For Sites with Slow Speed/No SSL)")
    st.code("""
Subject: Quick question regarding {Domain} website design

Hi {Business_Owner},

I came across {Domain} while looking for local service providers in {Location}. 

I noticed a couple of technical items on your site (like missing HTTPS security certificate and slow mobile loading speed) that might be causing you to lose potential local customers to competitors.

We recently helped a similar business redesign their site, which increased their online inquiries by 35%. 

Would you be open to a quick 3-minute video showing what can be improved?

Best regards,
Arjun Mishra
Content & SEO Specialist
    """, language="markdown")
    
    st.subheader("2. SEO Ranking Pitch (For Low Search Visibility)")
    st.code("""
Subject: Local ranking issue for {Keyword} in {Location}

Hi {Business_Owner},

I was searching for top-rated {Keyword} services in {Location}, and noticed {Domain} isn't showing up on page 1 of Google local search results.

Since 80% of local customers choose businesses on Page 1, fixing a few basic SEO factors can bring direct organic calls to your business every week.

I have prepared a quick 1-page SEO audit report for {Domain}. Should I send it over?

Best regards,
Arjun Mishra
Content & SEO Specialist
    """, language="markdown")

# --- ADMIN CONTROL PANEL PAGE ---
elif st.session_state["nav_page"] == "AdminPanel" and current_user["role"] == "Admin":
    st.markdown("<p class='big-title'>👑 Admin Master Control Panel</p>", unsafe_allow_html=True)
    st.markdown("<p class='big-subtitle'>User Approvals, Custom Limits, Password Resets & Live Analytics</p>", unsafe_allow_html=True)
    st.markdown("---")

    tab_a1, tab_a2, tab_a3, tab_a4 = st.tabs(["👥 User Management & Approval", "🔑 Change Admin Password", "🔄 Reset Client Password", "📊 System Analytics & Logs"])

    conn = sqlite3.connect("leads.db")
    cursor = conn.cursor()

    # TAB 1: User Approval & Limits
    with tab_a1:
        cursor.execute("SELECT id, username, status, created_at, expiry_date, domain_limit FROM users WHERE role='User' ORDER BY id DESC")
        users_list = cursor.fetchall()
        
        if users_list:
            df_users = pd.DataFrame(users_list, columns=["ID", "Username", "Status", "Requested On", "Expiry Date", "Domain Limit"])
            st.dataframe(df_users, use_container_width=True)
            st.markdown("---")

            st.subheader("⚙️ Edit User Status & Limits")
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                pending_users = [u[1] for u in users_list]
                selected_user = st.selectbox("Select User", pending_users)
            with col_a2:
                duration = st.selectbox("Set Duration", ["1 Month", "2 Months", "6 Months", "1 Year", "Custom Days"])
                custom_days = 30
                if duration == "Custom Days":
                    custom_days = st.number_input("Enter Days", min_value=1, value=30)
            with col_a3:
                set_limit = st.number_input("Domain Extraction Limit (-1 for Unlimited)", value=1000)
            with col_a4:
                action = st.radio("Action", ["Approve", "Reject", "Revoke Access"])

            if st.button("Update User Profile", type="primary"):
                if duration == "1 Month":
                    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                elif duration == "2 Months":
                    exp_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
                elif duration == "6 Months":
                    exp_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
                elif duration == "1 Year":
                    exp_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                else:
                    exp_date = (datetime.now() + timedelta(days=int(custom_days))).strftime("%Y-%m-%d")

                new_status = "Approved" if action == "Approve" else ("Rejected" if action == "Reject" else "Revoked")
                
                cursor.execute("UPDATE users SET status=?, expiry_date=?, domain_limit=? WHERE username=?", (new_status, exp_date if action == "Approve" else None, set_limit, selected_user))
                conn.commit()
                st.success(f"✅ User '{selected_user}' updated to *{new_status}! Limit set to: *{set_limit}**")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Abhi koi user registration requests nahi hain.")

    # TAB 2: Change Admin Password
    with tab_a2:
        st.subheader("🔑 Change Admin Password")
        old_pass = st.text_input("Current Admin Password", type="password")
        new_pass = st.text_input("New Admin Password", type="password")
        confirm_pass = st.text_input("Confirm New Admin Password", type="password")

        if st.button("Update Admin Password"):
            cursor.execute("SELECT password FROM users WHERE username='admin'")
            real_admin_pass = cursor.fetchone()[0]
            if old_pass != real_admin_pass:
                st.error("Current admin password wrong hai.")
            elif new_pass != confirm_pass:
                st.error("New password match nahi ho raha.")
            elif len(new_pass) < 4:
                st.error("Password kam se kam 4 characters ka hona chahiye.")
            else:
                cursor.execute("UPDATE users SET password=? WHERE username='admin'", (new_pass,))
                conn.commit()
                st.success("✅ Admin Password successfully change ho gaya hai!")

    # TAB 3: Reset Client Password
    with tab_a3:
        st.subheader("🔄 Reset Client Password")
        cursor.execute("SELECT username FROM users WHERE role='User'")
        all_clients = [c[0] for c in cursor.fetchall()]
        if all_clients:
            c_user = st.selectbox("Select Client", all_clients)
            c_new_pass = st.text_input("Enter New Password for Client", type="password")
            if st.button("Reset Client Password"):
                if c_new_pass:
                    cursor.execute("UPDATE users SET password=? WHERE username=?", (c_new_pass, c_user))
                    conn.commit()
                    st.success(f"✅ Client '{c_user}' ka password successfully update ho gaya hai!")
                else:
                    st.warning("Naya password likhein.")
        else:
            st.info("Koi registered clients nahi hain.")

    # TAB 4: System Analytics & Activity Logs
    with tab_a4:
        st.subheader("📊 Live Client Activity Logs")
        df_logs = pd.read_sql("SELECT username AS 'User', action AS 'Action Performed', timestamp AS 'Timestamp' FROM activity_logs ORDER BY id DESC LIMIT 100", conn)
        if not df_logs.empty:
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("Abhi tak koi activity record nahi hui hai.")

    conn.close()