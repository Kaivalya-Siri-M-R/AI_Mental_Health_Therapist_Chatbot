import os
from dotenv import load_dotenv

load_dotenv()
import sqlite3
import smtplib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- CONFIGURATION ---

# 1. GOOGLE GEMINI API KEY
# I have inserted your specific key here.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# 2. Email Configuration
SENDER_EMAIL = "therapistaimentalhealth@gmail.com"
# CORRECTED PASSWORD (Spaces removed so Python can read it)
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        age INTEGER,
        city TEXT,
        state TEXT,
        guardian_email TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp DATETIME
    )''')
    conn.commit()
    conn.close()

# --- HELPER FUNCTIONS ---

def send_guardian_alert(user_email, guardian_email, user_location, message_content):
    try:
        subject = "URGENT: Mental Health Alert"
        body = f"""
        Warning: The user ({user_email}) has expressed critical distress.
        Location: {user_location}
        Triggering Message: "{message_content}"
        
        Please contact them immediately or call emergency services."""
        msg = f"Subject: {subject}\n\n{body}"
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, guardian_email, msg)
        server.quit()
        print(f"ALERT SENT TO {guardian_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def get_ai_response(user_input, history_context):
    try:
        # --- CRITICAL FIX: Using 'gemini-1.5-flash' ---
        # Your previous error was because 'gemini-pro' is not allowed for your key.
        # 'gemini-1.5-flash' is the correct model for new free keys.
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        chat_history = []
        
        system_prompt = "You are a professional, empathetic mental health therapist chatbot. Provide thorough, supportive advice. Do not be minimal. If the user mentions self-harm, offer support but prioritize safety."
        chat_history.append({'role': 'user', 'parts': [system_prompt]})
        chat_history.append({'role': 'model', 'parts': ["I understand. I am ready to act as a professional therapist."]})

        # Add context (Last 10 messages)
        for role, content in history_context[-10:]:
            gemini_role = 'user' if role == 'user' else 'model'
            chat_history.append({'role': gemini_role, 'parts': [content]})

        chat_history.append({'role': 'user', 'parts': [user_input]})

        response = model.generate_content(chat_history)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "I am having trouble connecting to the server. Please try again."

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        age = request.form['age']
        city = request.form['city']
        state = request.form['state']
        guardian = request.form['guardian_email']
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, age, city, state, guardian_email) VALUES (?, ?, ?, ?, ?, ?)",
                      (username, password, age, city, state, guardian))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['location'] = f"{user[4]}, {user[5]}"
            session['guardian_email'] = user[6]
            return redirect(url_for('chat'))
        else:
            flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("SELECT role, content FROM chats WHERE user_id = ? ORDER BY id ASC", (user_id,))
    history = c.fetchall()
    
    if request.method == 'POST':
        user_input = request.form['message']
        
        # 1. Save User Message
        c.execute("INSERT INTO chats (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)", 
                  (user_id, 'user', user_input, datetime.now()))
        conn.commit()
        
        # 2. Safety Check
        critical_triggers = [
            "suicide", 
            "kill myself", 
            "end my life", 
            "die", 
            "cutting myself", 
            "overdose", 
            "hurting myself",
            # --- ADD YOUR NEW ONES BELOW ---
            "i want to disappear",
            "no reason to live",
            "everyone would be better off without me",
            "planning to jump",
            "took all the pills"
        ]
        if any(trigger in user_input.lower() for trigger in critical_triggers):
            print("CRITICAL TRIGGER DETECTED")
            send_guardian_alert(session['username'], session['guardian_email'], session['location'], user_input)
            
            crisis_response = f"I am detecting that you are in severe distress. I have notified your emergency contact ({session['guardian_email']}). Please call the Suicide Prevention Lifeline immediately (988)."
            
            c.execute("INSERT INTO chats (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)", 
                      (user_id, 'assistant', crisis_response, datetime.now()))
            conn.commit()
        else:
            # 3. AI RESPONSE MODE
            ai_reply = get_ai_response(user_input, history)
            
            c.execute("INSERT INTO chats (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)", 
                      (user_id, 'assistant', ai_reply, datetime.now()))
            conn.commit()
        
        conn.close()
        return redirect(url_for('chat'))
    
    conn.close()
    return render_template('chat.html', history=history)

if __name__ == '__main__':
    init_db()
    print("\n----------------------------------------------")
    print("--- SERVER UPDATED: RUNNING WITH GEMINI FLASH ---")
    print("----------------------------------------------\n")
    app.run(debug=True)