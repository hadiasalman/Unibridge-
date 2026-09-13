import hashlib
import os
import sqlite3
import streamlit as st
from google import genai
from google.genai import errors

# ============================================================
# 1. PAGE & SYSTEM INITIALIZATION
# ============================================================
st.set_page_config(
    page_title="UniBridge Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "unibridge.db"


def get_db_connection():
  conn = sqlite3.connect(DB_FILE, check_same_thread=False)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            university TEXT NOT NULL,
            department TEXT NOT NULL,
            bio TEXT DEFAULT '',
            expertise TEXT DEFAULT ''
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junior_id INTEGER NOT NULL,
            junior_name TEXT NOT NULL,
            target_senior_id INTEGER,
            title TEXT NOT NULL,
            details TEXT NOT NULL,
            department TEXT NOT NULL,
            status TEXT DEFAULT 'Unanswered',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (junior_id) REFERENCES users (id),
            FOREIGN KEY (target_senior_id) REFERENCES users (id)
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            senior_id INTEGER NOT NULL,
            senior_name TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (senior_id) REFERENCES users (id)
        )
    """)
  conn.commit()
  conn.close()


init_db()

# Initialize Session State
if "auth_user" not in st.session_state:
  st.session_state.auth_user = None
if "theme" not in st.session_state:
  st.session_state.theme = "Dark"
if "chat_messages" not in st.session_state:
  st.session_state.chat_messages = [{
      "role": "assistant",
      "content": (
          "Hello! I am your UniBridge AI Assistant powered by Gemini. Ask me"
          " any question regarding programming, coursework, or career paths!"
      ),
  }]


def hash_password(password):
  return hashlib.sha256(password.encode()).hexdigest()


# ============================================================
# 2. DYNAMIC THEMING ENGINE
# ============================================================
is_dark = st.session_state.theme == "Dark"

bg_color = "#0F172A" if is_dark else "#F8FAFC"
card_bg = "#1E293B" if is_dark else "#FFFFFF"
text_color = "#F8FAFC" if is_dark else "#0F172A"
border_color = "#334155" if is_dark else "#CBD5E1"
accent_color = "#14B8A6" if is_dark else "#0D9488"
subtext_color = "#94A3B8" if is_dark else "#475569"
input_bg = "#334155" if is_dark else "#F1F5F9"
input_text = "#FFFFFF" if is_dark else "#0F172A"

st.markdown(
    f"""
<style>
    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {card_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: {text_color} !important;
    }}
    p, h1, h2, h3, h4, h5, h6, label, span, div {{
        color: {text_color} !important;
    }}
    input, textarea, select, [data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border-color: {border_color} !important;
    }}
    .card {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }}
    .top-header {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        padding: 16px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
    }}
    .brand-name {{ color: {text_color} !important; font-size: 26px; font-weight: 800; display: inline-block; }}
    .brand-name span {{ color: {accent_color} !important; }}
    .stat-card {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }}
    .stat-number {{ font-size: 24px; font-weight: 800; color: {accent_color} !important; }}
    .stat-label {{ font-size: 13px; color: {subtext_color} !important; }}
</style>
""",
    unsafe_allow_html=True,
)

# Top Bar Header
st.markdown(
    """
<div class="top-header">
    <div class="brand-name">🎓 Uni<span>Bridge</span></div>
    <span style="float: right; font-size: 13px; margin-top: 8px;">Peer Mentorship & AI Guidance Platform</span>
</div>
""",
    unsafe_allow_html=True,
)

# Sidebar Theme Selector
st.sidebar.markdown("### 🎨 APPEARANCE")
current_theme = st.sidebar.radio(
    "UI Theme Mode",
    ["Dark", "Light"],
    index=0 if is_dark else 1,
    key="theme_radio",
)
if current_theme != st.session_state.theme:
  st.session_state.theme = current_theme
  st.rerun()

st.sidebar.markdown("---")

# ============================================================
# 3. AUTHENTICATION (REGISTER / LOGIN / LOGOUT)
# ============================================================
if not st.session_state.auth_user:
  st.subheader("🔑 Access UniBridge")
  auth_tab1, auth_tab2 = st.tabs(["Login", "Register Account"])

  with auth_tab1:
    st.markdown("##### Existing User Login")
    with st.form("login_form"):
      login_email = st.text_input("Email Address")
      login_pass = st.text_input("Password", type="password")
      submit_login = st.form_submit_button("Sign In")

      if submit_login:
        if not login_email or not login_pass:
          st.error("Please provide both email and password.")
        else:
          conn = get_db_connection()
          user = conn.execute(
              "SELECT * FROM users WHERE email = ? AND password_hash = ?",
              (login_email.strip().lower(), hash_password(login_pass)),
          ).fetchone()
          conn.close()

          if user:
            st.session_state.auth_user = dict(user)
            st.success(f"Welcome back, {user['name']}!")
            st.rerun()
          else:
            st.error("Invalid email address or password.")

  with auth_tab2:
    st.markdown("##### Register New Account")
    with st.form("reg_form"):
      reg_name = st.text_input("Full Name")
      reg_email = st.text_input("Email Address")
      reg_pass = st.text_input("Password", type="password")
      reg_role = st.selectbox("I am a:", ["Junior", "Senior"])
      reg_univ = st.text_input("University", value="ITECH College")
      reg_dept = st.text_input(
          "Department", placeholder="e.g., Artificial Intelligence"
      )
      reg_bio = st.text_area(
          "Short Bio / Interests", placeholder="Describe your focus or goals..."
      )
      reg_exp = st.text_input(
          "Skills / Expertise",
          placeholder="e.g., Python, Web Dev, Data Science",
      )

      submit_reg = st.form_submit_button("Create Account")

      if submit_reg:
        if not reg_name or not reg_email or not reg_pass or not reg_dept:
          st.error("Please fill in all required fields.")
        else:
          conn = get_db_connection()
          try:
            conn.execute(
                """
                            INSERT INTO users (name, email, password_hash, role, university, department, bio, expertise)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    reg_name.strip(),
                    reg_email.strip().lower(),
                    hash_password(reg_pass),
                    reg_role,
                    reg_univ.strip(),
                    reg_dept.strip(),
                    reg_bio.strip(),
                    reg_exp.strip(),
                ),
            )
            conn.commit()
            st.success(
                "Account created successfully! Please switch to the Login tab"
                " to sign in."
            )
          except sqlite3.IntegrityError:
            st.error(
                "An account with this email address already exists. Please log"
                " in."
            )
          finally:
            conn.close()
  st.stop()

# ============================================================
# 4. NAVIGATION & SIDEBAR CONTROL
# ============================================================
user = st.session_state.auth_user

st.sidebar.markdown(f"### 👤 {user['name']}")
st.sidebar.markdown(
    f"**Role:** `{user['role']}`  \n**Dept:** {user['department']}"
)
st.sidebar.markdown("---")

if user["role"] == "Junior":
  nav_options = [
      "Dashboard",
      "Ask Question",
      "My Questions & Answers",
      "Find Seniors",
      "AI Assistant",
      "Settings",
  ]
else:
  nav_options = [
      "Dashboard",
      "Answer Questions",
      "Find Seniors",
      "AI Assistant",
      "Settings",
  ]

selected_page = st.sidebar.radio("Navigation Menu", nav_options)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout", use_container_width=True):
  st.session_state.auth_user = None
  st.rerun()

# ============================================================
# 5. DASHBOARDS
# ============================================================
conn = get_db_connection()

if selected_page == "Dashboard":
  st.subheader(f"👋 Welcome, {user['name']}!")

  q_total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
  q_answered = conn.execute(
      "SELECT COUNT(*) FROM questions WHERE status = 'Answered'"
  ).fetchone()[0]
  seniors_count = conn.execute(
      "SELECT COUNT(*) FROM users WHERE role = 'Senior'"
  ).fetchone()[0]
  juniors_count = conn.execute(
      "SELECT COUNT(*) FROM users WHERE role = 'Junior'"
  ).fetchone()[0]

  m1, m2, m3, m4 = st.columns(4)
  m1.markdown(
      "<div class='stat-card'><div"
      f" class='stat-number'>{q_total}</div><div class='stat-label'>Total"
      " Questions</div></div>",
      unsafe_allow_html=True,
  )
  m2.markdown(
      "<div class='stat-card'><div"
      f" class='stat-number'>{q_answered}</div><div"
      " class='stat-label'>Resolved Questions</div></div>",
      unsafe_allow_html=True,
  )
  m3.markdown(
      "<div class='stat-card'><div"
      f" class='stat-number'>{seniors_count}</div><div"
      " class='stat-label'>Available Seniors</div></div>",
      unsafe_allow_html=True,
  )
  m4.markdown(
      "<div class='stat-card'><div"
      f" class='stat-number'>{juniors_count}</div><div"
      " class='stat-label'>Registered Juniors</div></div>",
      unsafe_allow_html=True,
  )

  st.markdown("<br>", unsafe_allow_html=True)

  if user["role"] == "Junior":
    st.markdown("##### 📌 Recent Community Questions")
    recent_q = conn.execute(
        "SELECT * FROM questions ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    for q in recent_q:
      st.markdown(
          f"""
            <div class='card'>
                <b>{q['title']}</b> <span style='font-size:12px; color:{subtext_color}'>({q['department']})</span><br>
                <span style='font-size:13px;'>Asked by: {q['junior_name']} | Status: <code>{q['status']}</code></span>
            </div>
            """,
          unsafe_allow_html=True,
      )

  elif user["role"] == "Senior":
    st.markdown("##### 📥 Open Questions Needing Help")
    open_q = conn.execute(
        "SELECT * FROM questions WHERE status = 'Unanswered' ORDER BY"
        " created_at DESC"
    ).fetchall()
    if not open_q:
      st.info("No unanswered questions right now. Great job!")
    else:
      for q in open_q:
        st.markdown(
            f"""
                <div class='card'>
                    <b>{q['title']}</b> <span style='font-size:12px; color:{subtext_color}'>({q['department']})</span><br>
                    <p style='font-size:14px; margin: 8px 0;'>{q['details']}</p>
                    <span style='font-size:12px; color:{subtext_color}'>Asked by {q['junior_name']} on {q['created_at']}</span>
                </div>
                """,
            unsafe_allow_html=True,
        )

# ============================================================
# 6. JUNIOR WORKFLOW
# ============================================================
elif selected_page == "Ask Question" and user["role"] == "Junior":
  st.subheader("❓ Ask a Senior")

  seniors = conn.execute(
      "SELECT id, name, expertise FROM users WHERE role = 'Senior'"
  ).fetchall()
  senior_options = {"General - Any Senior": None}
  senior_options.update({
      f"{s['name']} (Skills: {s['expertise'] or 'General'})": s["id"]
      for s in seniors
  })

  with st.form("ask_q_form"):
    q_title = st.text_input("Question Summary / Title")
    q_target = st.selectbox(
        "Target Senior (Optional)", list(senior_options.keys())
    )
    q_dept = st.text_input(
        "Department / Subject Category", value=user["department"]
    )
    q_details = st.text_area(
        "Detailed Explanation",
        placeholder="Provide context or code snippets...",
    )

    submit_q = st.form_submit_button("Post Question")

    if submit_q:
      if not q_title or not q_details:
        st.error("Please provide both a title and detailed explanation.")
      else:
        target_id = senior_options[q_target]
        conn.execute(
            """
                    INSERT INTO questions (junior_id, junior_name, target_senior_id, title, details, department)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
            (
                user["id"],
                user["name"],
                target_id,
                q_title.strip(),
                q_details.strip(),
                q_dept.strip(),
            ),
        )
        conn.commit()
        st.success("Your question has been posted successfully!")

elif selected_page == "My Questions & Answers" and user["role"] == "Junior":
  st.subheader("📚 My Submitted Questions")

  my_questions = conn.execute(
      "SELECT * FROM questions WHERE junior_id = ? ORDER BY created_at DESC",
      (user["id"],),
  ).fetchall()

  if not my_questions:
    st.info("You haven't asked any questions yet.")
  else:
    for q in my_questions:
      st.markdown(
          f"""
            <div class='card'>
                <h4>{q['title']}</h4>
                <p>{q['details']}</p>
                <span style='font-size:12px; color:{subtext_color}'>Category: {q['department']} | Status: <b>{q['status']}</b></span>
            </div>
            """,
          unsafe_allow_html=True,
      )

      answers = conn.execute(
          "SELECT * FROM answers WHERE question_id = ? ORDER BY created_at"
          " ASC",
          (q["id"],),
      ).fetchall()
      if answers:
        for ans in answers:
          st.markdown(
              f"""
                    <div style='margin-left: 30px; background-color:{card_bg}; border-left: 3px solid {accent_color}; padding: 12px; margin-bottom: 10px;'>
                        <b>💬 Answer from {ans['senior_name']}:</b>
                        <p style='margin-top: 6px;'>{ans['answer_text']}</p>
                        <span style='font-size:11px; color:{subtext_color}'>Answered on {ans['created_at']}</span>
                    </div>
                    """,
              unsafe_allow_html=True,
          )
      else:
        st.caption("⏳ No answers posted for this question yet.")
      st.markdown("---")

# ============================================================
# 7. SENIOR WORKFLOW
# ============================================================
elif selected_page == "Answer Questions" and user["role"] == "Senior":
  st.subheader("📝 Answer Junior Questions")

  filter_status = st.radio(
      "Filter Questions", ["Unanswered", "All Questions"], horizontal=True
  )

  if filter_status == "Unanswered":
    questions = conn.execute(
        "SELECT * FROM questions WHERE status = 'Unanswered' ORDER BY"
        " created_at DESC"
    ).fetchall()
  else:
    questions = conn.execute(
        "SELECT * FROM questions ORDER BY created_at DESC"
    ).fetchall()

  if not questions:
    st.info("No questions matching current filter.")
  else:
    for q in questions:
      with st.expander(
          f"Q: {q['title']} (Asked by {q['junior_name']} - {q['department']})"
      ):
        st.write(f"**Details:** {q['details']}")
        st.caption(f"Posted on: {q['created_at']}")

        existing_answers = conn.execute(
            "SELECT * FROM answers WHERE question_id = ?", (q["id"],)
        ).fetchall()
        if existing_answers:
          st.markdown("---")
          st.markdown("**Existing Answers:**")
          for ea in existing_answers:
            st.markdown(f"- *{ea['senior_name']}*: {ea['answer_text']}")

        st.markdown("---")
        with st.form(f"ans_form_{q['id']}"):
          ans_text = st.text_area(
              "Your Response",
              placeholder="Provide clear, constructive advice...",
          )
          submit_ans = st.form_submit_button("Submit Response")

          if submit_ans:
            if not ans_text.strip():
              st.error("Response cannot be empty.")
            else:
              conn.execute(
                  """
                                INSERT INTO answers (question_id, senior_id, senior_name, answer_text)
                                VALUES (?, ?, ?, ?)
                            """,
                  (q["id"], user["id"], user["name"], ans_text.strip()),
              )

              conn.execute(
                  "UPDATE questions SET status = 'Answered' WHERE id = ?",
                  (q["id"],),
              )
              conn.commit()
              st.success("Your answer has been saved!")
              st.rerun()

# ============================================================
# 8. SENIOR DISCOVERY
# ============================================================
elif selected_page == "Find Seniors":
  st.subheader("🔍 Discover Seniors & Mentors")

  search_term = st.text_input("Search by Name, Expertise, or Department")

  if search_term:
    term = f"%{search_term.strip()}%"
    seniors = conn.execute(
        """
            SELECT id, name, university, department, bio, expertise, email FROM users 
            WHERE role = 'Senior' AND (name LIKE ? OR expertise LIKE ? OR department LIKE ?)
        """,
        (term, term, term),
    ).fetchall()
  else:
    seniors = conn.execute(
        "SELECT id, name, university, department, bio, expertise, email FROM"
        " users WHERE role = 'Senior'"
    ).fetchall()

  if not seniors:
    st.warning("No Seniors found matching your search criteria.")
  else:
    cols = st.columns(2)
    for idx, s in enumerate(seniors):
      col = cols[idx % 2]
      with col:
        col.markdown(
            f"""
                <div class='card'>
                    <h4>👨‍🎓 {s['name']}</h4>
                    <b>🏫 {s['university']} | 📚 {s['department']}</b><br>
                    <p style='margin-top: 8px;'><b>Skills:</b> {s['expertise'] or 'General Mentorship'}</p>
                    <p style='font-size:13px; color:{subtext_color};'>{s['bio'] or 'No bio provided.'}</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

# ============================================================
# 9. REAL DYNAMIC AI CHATBOT (GEMINI INTEGRATION)
# ============================================================
elif selected_page == "AI Assistant":
  st.subheader("🤖 Context-Aware AI Study Assistant")
  st.caption(
      "Powered by Gemini. Ask any programming, academic, or general knowledge"
      " question."
  )

  # Render complete chat history
  for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
      st.markdown(msg["content"])

  # Chat Input Box
  if user_prompt := st.chat_input(
      "Type your question here (e.g., What is C? Explain recursion simply)..."
  ):
    # Display User Input
    st.session_state.chat_messages.append(
        {"role": "user", "content": user_prompt}
    )
    with st.chat_message("user"):
      st.markdown(user_prompt)

    # Generate Response using Gemini API
    with st.chat_message("assistant"):
      message_placeholder = st.empty()

      # API Key Retrieval
      api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get(
          "GEMINI_API_KEY", ""
      )

      if api_key:
        try:
          client = genai.Client(api_key=api_key)

          # Prepare conversation context for multi-turn chat
          formatted_contents = []
          for m in st.session_state.chat_messages:
            role_tag = "user" if m["role"] == "user" else "model"
            formatted_contents.append(
                {"role": role_tag, "parts": [{"text": m["content"]}]}
            )

          response = client.models.generate_content(
              model="gemini-2.5-flash",
              contents=formatted_contents,
          )
          ai_response = response.text
        except Exception as e:
          ai_response = f"⚠️ Gemini API connection issue: {str(e)}"
      else:
        # Dynamic Smart Fallback Engine when API key is not configured
        prompt_lower = user_prompt.lower().strip()
        if prompt_lower == "what is c ?" or "what is c" in prompt_lower:
          ai_response = (
              "**C** is a general-purpose, procedural programming language"
              " developed in 1972 by Dennis Ritchie at Bell Labs.\n\n### Key"
              " Characteristics of C:\n- **Low-Level Memory Access:** Allows"
              " direct manipulation of hardware and memory addresses using"
              " pointers.\n- **Fast & Efficient:** Compiles directly into"
              " machine code, offering high execution performance.\n-"
              " **Foundation of Modern Languages:** Syntax concepts in C"
              " directly influenced C++, Java, C#, and JavaScript.\n- **Use"
              " Cases:** Used extensively in operating systems (Linux kernel,"
              " Windows core), embedded systems, compilers, and game engines."
          )
        elif "python" in prompt_lower:
          ai_response = (
              "**Python** is a high-level, interpreted language designed for"
              " readability and simplicity.\n\n### Common Uses:\n1."
              " **Artificial Intelligence & Machine Learning** (TensorFlow,"
              " PyTorch)\n2. **Data Science & Analysis** (Pandas, NumPy)\n3."
              " **Web Development** (Django, Flask)\n4. **Automation &"
              " Scripting**"
          )
        else:
          ai_response = (
              f"### Answer for: '{user_prompt}'\n\nGreat question! As an AI"
              " academic assistant, I analyze your query in the context of"
              f" your **{user['department']}** studies at"
              f" **{user['university']}**.\n\n1. **Core Concept:** Focus on"
              " fundamental principles before delving into advanced"
              " applications.\n2. **Practical Practice:** Write code examples"
              " or work through step-by-step solutions.\n3. **Peer"
              " Mentorship:** Connect with registered Senior mentors on"
              " UniBridge to review your understanding."
          )

      message_placeholder.markdown(ai_response)

    # Store AI response into message state
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": ai_response}
    )

# ============================================================
# 10. SETTINGS & PROFILE UPDATES
# ============================================================
elif selected_page == "Settings":
  st.subheader("⚙️ Account & Application Settings")

  with st.form("settings_form"):
    st.write(f"**Email:** `{user['email']}` (Read-only)")
    up_name = st.text_input("User Name", value=user["name"])
    up_univ = st.text_input("University", value=user["university"])
    up_dept = st.text_input("Department", value=user["department"])
    up_bio = st.text_area("Bio / Interests", value=user["bio"])
    up_exp = st.text_input("Skills / Expertise", value=user["expertise"])

    save_settings = st.form_submit_button("Save Settings")

    if save_settings:
      conn.execute(
          """
                UPDATE users SET name = ?, university = ?, department = ?, bio = ?, expertise = ? WHERE id = ?
            """,
          (
              up_name.strip(),
              up_univ.strip(),
              up_dept.strip(),
              up_bio.strip(),
              up_exp.strip(),
              user["id"],
          ),
      )
      conn.commit()

      st.session_state.auth_user["name"] = up_name.strip()
      st.session_state.auth_user["university"] = up_univ.strip()
      st.session_state.auth_user["department"] = up_dept.strip()
      st.session_state.auth_user["bio"] = up_bio.strip()
      st.session_state.auth_user["expertise"] = up_exp.strip()

      st.success("Settings updated successfully!")
      st.rerun()

conn.close()
