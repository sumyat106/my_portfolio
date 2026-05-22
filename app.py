from flask import Flask, render_template, request, redirect, flash, session, url_for
from functools import wraps 
from werkzeug.utils import secure_filename
import pymysql
import os
from flask_compress import Compress

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretportfolio_key_123'
app.config['DEBUG'] = True  # <--- အမှားအမှန် အသေးစိတ်မြင်ရအောင် ဒါကို True ပေးထားရပါမယ်
Compress(app)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Database Connection Config (Railway ပုံစံ) ---
def get_db_connection():
    return pymysql.connect(
        host=os.environ.get('MYSQLHOST', 'mysql.railway.internal'),
        user=os.environ.get('MYSQLUSER'),
        password=os.environ.get('MYSQLPASSWORD'),
        database=os.environ.get('MYSQLDATABASE'),
        port=int(os.environ.get('MYSQLPORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

# --- FR-2.1: Custom Middleware (Auth Guard) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Session ထဲမှာ logged_in မရှိရင် Login Page ကို ပို့မယ်
        if not session.get('logged_in'):
            flash('Please login first to access the admin panel.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- schema.sql ဖိုင်ကို လှမ်းဖတ်ပြီး Table ဆောက်ပေးမည့် Function ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if os.path.exists('schema.sql'):
        with open('schema.sql', 'r', encoding='utf-8') as f:
            sql_commands = f.read().split(';')
            
        for command in sql_commands:
            if command.strip(): 
                cursor.execute(command)
                
    cursor.execute("SELECT * FROM bio")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO bio (text, github_url, linkedin_url) 
            VALUES ('Welcome to my real-world SQL portfolio!', 'https://github.com', 'https://linkedin.com')
        """)
        
    cursor.close()
    conn.close()

# Table တွေ အရင်ဆောက်ခိုင်းမည်
init_db()

# 1. Visitor Front-End Main Route
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT * FROM bio LIMIT 1")
    bio_data = cursor.fetchone()
    
    cursor.execute("SELECT * FROM project")
    all_projects = cursor.fetchall()
    
    cursor.execute("SELECT * FROM timeline")
    timeline_items = cursor.fetchall()
    
    cursor.execute("SELECT * FROM skill ORDER BY display_order ASC")
    skills = cursor.fetchall()
    
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

# 2. Contact Form တင်မည့် Route
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
    # ✨ မစုမြတ်နိုး အလိုရှိတဲ့ Logic: တစ်ခါဝင်ထားပြီးသားဖြစ်ရင် Dashboard ကို တန်းပို့ပေးမည်
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'suu_myat' and password == 'suu1353@mubF':
            session['logged_in'] = True
            session['username'] = username
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid Username or Password!', 'danger')
            
    return render_template('admin/login.html')

# --- Admin Logout Route ---
@app.route('/admin/logout')
def admin_logout():
    session.clear() 
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

# --- FR-2.2: Admin Dashboard Route ---
@app.route('/admin/dashboard')
@login_required 
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor) # DictCursor ဖြစ်အောင် ပြောင်းလဲထားသည်
    
    # DictCursor ကြောင့် Dict format (result['COUNT(*)']) ဖြင့် စနစ်တကျ ဖတ်ရပါမည်
    cursor.execute("SELECT COUNT(*) FROM project")
    result_proj = cursor.fetchone()
    total_projects = result_proj['COUNT(*)'] if result_proj else 0
    
    cursor.execute("SELECT COUNT(*) FROM contact_message WHERE is_read = 0")
    result_msg = cursor.fetchone()
    unread_messages = result_msg['COUNT(*)'] if result_msg else 0
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dashboard.html', 
                           total_projects=total_projects, 
                           unread_messages=unread_messages)

# FR-2.4: Project CRUD
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

@app.route('/admin/projects/add', methods=['POST'])
@login_required
def add_project():
    title = request.form.get('title')
    description = request.form.get('description')
    live_url = request.form.get('live_url')
    github_url = request.form.get('github_url')
    
    file = request.files.get('image')
    filename = None
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "INSERT INTO project (title, description, image, live_url, github_url) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(sql, (title, description, filename, live_url, github_url))
    cursor.close()
    conn.close()
    
    flash('Project added successfully!', 'success')
    return redirect('/admin/projects')

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

# FR-2.6: Inbox / Message Management
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

@app.route('/admin/inbox/toggle/<int:id>')
@login_required
def toggle_message(id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor) # DictCursor သို့ ပြောင်းလဲထားသည်
    
    cursor.execute("SELECT is_read FROM contact_message WHERE id = %s", (id,))
    row = cursor.fetchone()
    current_status = row['is_read'] if row else 0
    
    new_status = not current_status
    
    cursor.execute("UPDATE contact_message SET is_read = %s WHERE id = %s", (new_status, id))
    cursor.close()
    conn.close()
    flash('Message status updated!', 'success')
    return redirect('/admin/inbox')

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

# Skills Management (Admin CRUD)
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

# Timeline Management
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

@app.route('/admin/timeline/add', methods=['POST'])
@login_required
def add_timeline():
    title = request.form.get('title')
    organization = request.form.get('organization')
    type_val = request.form.get('type') 
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Gunicorn ဖြင့် Run မည်ဖြစ်သောကြောင့် ဤနေရာတွင် normal execution သာ ထားရှိပါသည်
    app.run(host="0.0.0.0", port=port)