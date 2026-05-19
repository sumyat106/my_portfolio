# app.py ရဲ့ ထိပ်ဆုံးစာကြောင်းမှာ session ကို ထည့်သွင်းပါ
from flask import Flask, render_template, request, redirect, flash, session, url_for
from functools import wraps # Middleware ဆောက်ရန် လိုအပ်သည်
from werkzeug.utils import secure_filename
import pymysql
import os
from flask_compress import Compress

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretportfolio_key_123'
Compress(app)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
# ပုံစံမပျက်စေရန် အောက်ပါ File Extension များကိုသာ ခွင့်ပြုမည်
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# XAMPP MySQL Database Connection Config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'my_portfolio_db',
    'autocommit': True
}

def get_db_connection():
    return pymysql.connect(**db_config)

# --- FR-2.1: Custom Middleware (Auth Guard) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Session ထဲမှာ logged_in ဆိုတဲ့ key မရှိရင် (သို့မဟုတ်) True ဖြစ်မနေရင်
        if 'logged_in' not in session or not session['logged_in']:
            flash('Please login first to access the admin panel.', 'danger')
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

# --- schema.sql ဖိုင်ကို လှမ်းဖတ်ပြီး Table ဆောက်ပေးမည့် Function ---
def init_db():
    # 1. XAMPP database နဲ့ အရင်ချိတ်မည်
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. schema.sql ဖိုင်ကို ဖွင့်ဖတ်မည်
    if os.path.exists('schema.sql'):
        with open('schema.sql', 'r', encoding='utf-8') as f:
            sql_commands = f.read().split(';') # Query တစ်ခုချင်းစီကို ';' နဲ့ ခွဲထုတ်မည်
            
        # 3. ဖတ်လို့ရလာတဲ့ SQL Query များကို cursor.execute ဖြင့် တစ်ခုချင်းစီ Run မည်
        for command in sql_commands:
            if command.strip(): # အလွတ်မဟုတ်မှသာ Run မည်
                cursor.execute(command)
                
    # 4. စမ်းသပ်ရန် Bio အချက်အလက် မရှိသေးပါက Default စာသား အော်တိုထည့်ပေးခြင်း
    cursor.execute("SELECT * FROM bio")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO bio (text, github_url, linkedin_url) 
            VALUES ('Welcome to my real-world SQL portfolio!', 'https://github.com', 'https://linkedin.com')
        """)
        
    cursor.close()
    conn.close()

# Flask App မပတ်ခင် Table တွေ အရင်ဆောက်ခိုင်းမည်
init_db()
# 1. Visitor Front-End Main Route (FR-1.1 မှ FR-1.4 ဒေတာများကို cursor.execute ဖြင့် ဆွဲထုတ်ခြင်း)
@app.route('/')
def index():
    conn = get_db_connection()
    # DictCursor သုံးရခြင်းမှာ HTML ဘက်ကနေ bio.text သို့မဟုတ် project['title'] ဟု နာမည်ဖြင့် လှမ်းခေါ်ရလွယ်ကူစေရန်ဖြစ်သည်
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Bio ဆွဲထုတ်ခြင်း
    cursor.execute("SELECT * FROM bio LIMIT 1")
    bio_data = cursor.fetchone()
    
    # Projects ဆွဲထုတ်ခြင်း
    cursor.execute("SELECT * FROM project")
    all_projects = cursor.fetchall()
    
    # Timeline ဆွဲထုတ်ခြင်း
    cursor.execute("SELECT * FROM timeline")
    timeline_items = cursor.fetchall()
    
    # Skills ကို display_order အတိုင်း စီပြီးဆွဲထုတ်ခြင်း
    cursor.execute("SELECT * FROM skill ORDER BY display_order ASC")
    skills = cursor.fetchall()
    
    # Skills တွေကို Category အလိုက် Group ဖွဲ့ခြင်း (HTML Dictionary ပုံစံအတွက်)
    categorized_skills = {}
    for skill in skills:
        cat = skill['category']
        if cat not in categorized_skills:
            categorized_skills[cat] = []
        categorized_skills[cat].append(skill)
        
    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                           bio=bio_data, 
                           projects=all_projects, 
                           timeline_items=timeline_items, 
                           categorized_skills=categorized_skills)


# 2. Contact Form တင်မည့် Route (FR-1.5: Raw SQL ဖြင့် INSERT လုပ်ခြင်း)
@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    if not name or not email or not message:
        flash('All fields are required!', 'danger')
        return redirect('/#contact')
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SQL Injection မဖြစ်အောင် %s placeholder များကို သုံးပြီး INSERT ရေးရပါမည်
        sql = "INSERT INTO contact_message (name, email, message) VALUES (%s, %s, %s)"
        cursor.execute(sql, (name, email, message))
        
        cursor.close()
        conn.close()
        flash('Your message has been sent successfully!', 'success')
    except Exception as e:
        print(e)
        flash('Something went wrong. Please try again.', 'danger')
        
    return redirect('/#contact')

# //////////////////Admin///////////////////////
# --- Admin Login Route ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # ရိုးရှင်းသော သတ်မှတ်ချက်ဖြင့် စစ်ဆေးခြင်း
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            flash('Welcome back, Admin!', 'success')
            return redirect('/admin/dashboard')
        else:
            flash('Invalid Username or Password!', 'danger')
            
    return render_template('admin/login.html')

# --- Admin Logout Route ---
@app.route('/admin/logout')
def admin_logout():
    session.clear() # Session အားလုံးကို ဖျက်ထုတ်ပစ်ခြင်း
    flash('Logged out successfully.', 'success')
    return redirect('/admin/login')


# --- FR-2.2: Admin Dashboard Route (Metrics ဒေတာများကို cursor.execute ဖြင့် ဆွဲထုတ်ခြင်း) ---
@app.route('/admin/dashboard')
@login_required # Auth Guard ဖြင့် လမ်းကြောင်းကို ပိတ်ထားခြင်း
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Projects စုစုပေါင်း အရေအတွက်ကို ရေတွက်ခြင်း
    cursor.execute("SELECT COUNT(*) FROM project")
    total_projects = cursor.fetchone()[0]
    
    # 2. Unread Messages (မဖတ်ရသေးသော မက်ဆေ့ခ်ျ) အရေအတွက်ကို ရေတွက်ခြင်း
    cursor.execute("SELECT COUNT(*) FROM contact_message WHERE is_read = FALSE")
    unread_messages = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dashboard.html', 
                           total_projects=total_projects, 
                           unread_messages=unread_messages)


# ==========================================
# FR-2.4: Project CRUD (Create, Read, Delete)
# ==========================================

# 1. Project အားလုံးကို Table ဖြင့်ပြသမည့် လမ်းကြောင်း
@app.route('/admin/projects')
@login_required
def admin_projects():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM project")
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/projects.html', projects=projects)

# 2. Project အသစ်ထည့်ခြင်း (Multi-part Form Data & File Upload ကို ကိုင်တွယ်ခြင်း)
@app.route('/admin/projects/add', methods=['POST'])
@login_required
def add_project():
    title = request.form.get('title')
    description = request.form.get('description')
    live_url = request.form.get('live_url')
    github_url = request.form.get('github_url')
    
    # File Upload အပိုင်းကို စစ်ဆေးခြင်း
    file = request.files.get('image')
    filename = None
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # static/uploads/ ဖိုဒါထဲသို့ ပုံကို လှမ်းသိမ်းလိုက်ခြင်း
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "INSERT INTO project (title, description, image, live_url, github_url) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(sql, (title, description, filename, live_url, github_url))
    cursor.close()
    conn.close()
    
    flash('Project added successfully!', 'success')
    return redirect('/admin/projects')

# 3. Project ဖျက်ခြင်း လမ်းကြောင်း
@app.route('/admin/projects/delete/<int:id>')
@login_required
def delete_project(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project WHERE id = %s", (id,))
    cursor.close()
    conn.close()
    flash('Project deleted successfully!', 'success')
    return redirect('/admin/projects')


# ==========================================
# FR-2.6: Inbox / Message Management
# ==========================================

# 1. Message အားလုံး ပြသရမည့် လမ်းကြောင်း
@app.route('/admin/inbox')
@login_required
def admin_inbox():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM contact_message ORDER BY created_at DESC")
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/inbox.html', messages=messages)

# 2. Toggle Read Status Feature (ဖတ်ပြီး/မဖတ်ရသေး အဖွင့်အပိတ်လုပ်ခြင်း)
@app.route('/admin/inbox/toggle/<int:id>')
@login_required
def toggle_message(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # လက်ရှိ Status ကို အရင်သွားကြည့်ခြင်း
    cursor.execute("SELECT is_read FROM contact_message WHERE id = %s", (id,))
    current_status = cursor.fetchone()[0]
    
    # ပြောင်းပြန်လှန်လိုက်ခြင်း (True ဖြစ်ရင် False၊ False ဖြစ်ရင် True)
    new_status = not current_status
    
    cursor.execute("UPDATE contact_message SET is_read = %s WHERE id = %s", (new_status, id))
    cursor.close()
    conn.close()
    flash('Message status updated!', 'success')
    return redirect('/admin/inbox')

# 3. Message ဖျက်ခြင်း လမ်းကြောင်း
@app.route('/admin/inbox/delete/<int:id>')
@login_required
def delete_message(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_message WHERE id = %s", (id,))
    cursor.close()
    conn.close()
    flash('Message deleted!', 'success')
    return redirect('/admin/inbox')

# ==========================================
# Skills Management (Admin CRUD)
# ==========================================

# 1. Skills အားလုံးကို ပြသမည့် လမ်းကြောင်း
@app.route('/admin/skills')
@login_required
def admin_skills():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM skill ORDER BY category, display_order")
    skills = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/skills.html', skills=skills)

# 2. Skill အသစ်ထည့်သည့် လမ်းကြောင်း
@app.route('/admin/skills/add', methods=['POST'])
@login_required
def add_skill():
    name = request.form.get('name')
    category = request.form.get('category')
    display_order = request.form.get('display_order', 0)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO skill (name, category, display_order) VALUES (%s, %s, %s)", 
                   (name, category, display_order))
    cursor.close()
    conn.close()
    flash('Skill added successfully!', 'success')
    return redirect('/admin/skills')

# 3. Skill ဖျက်သည့် လမ်းကြောင်း
@app.route('/admin/skills/delete/<int:id>')
@login_required
def delete_skill(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM skill WHERE id = %s", (id,))
    cursor.close()
    conn.close()
    flash('Skill deleted successfully!', 'success')
    return redirect('/admin/skills')


# ==========================================
# Timeline Management (Experience & Education CRUD)
# ==========================================

# 1. Timelines အားလုံးကို ပြသမည့် လမ်းကြောင်း
@app.route('/admin/timeline')
@login_required
def admin_timeline():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM timeline ORDER BY start_date DESC")
    timelines = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/timeline.html', timelines=timelines)

# 2. Timeline အသစ်ထည့်သည့် လမ်းကြောင်း
@app.route('/admin/timeline/add', methods=['POST'])
@login_required
def add_timeline():
    title = request.form.get('title')
    organization = request.form.get('organization')
    type_val = request.form.get('type') # 'experience' သို့မဟုတ် 'education'
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO timeline (title, organization, type, start_date, end_date, description) 
             VALUES (%s, %s, %s, %s, %s, %s)"""
    cursor.execute(sql, (title, organization, type_val, start_date, end_date, description))
    cursor.close()
    conn.close()
    flash('Timeline event added successfully!', 'success')
    return redirect('/admin/timeline')

# 3. Timeline ဖျက်သည့် လမ်းကြောင်း
@app.route('/admin/timeline/delete/<int:id>')
@login_required
def delete_timeline(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM timeline WHERE id = %s", (id,))
    cursor.close()
    conn.close()
    flash('Timeline event deleted successfully!', 'success')
    return redirect('/admin/timeline')
if __name__ == '__main__':
    app.run(debug=True)