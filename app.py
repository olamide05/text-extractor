import streamlit as st
from task_extractor import extract_task_info
from datetime import datetime

st.set_page_config(page_title="Smart Task Extractor", layout="wide")

# ---------------- SESSION STATE (Task History)
if "tasks" not in st.session_state:
    st.session_state.tasks = []

# ---------------- SIDEBAR
st.sidebar.title("⚙️ Controls")
show_history = st.sidebar.checkbox("Show Task History", True)

st.sidebar.markdown("### Examples")
st.sidebar.info("Try:\n- Assignment due tomorrow\n- Submit report by May 3\n- Exam deadline next Friday")

# ---------------- HEADER
st.title("📋 Smart Task Extractor")
st.caption("Turn messy text into structured tasks instantly")

# ---------------- INPUT UI (Chat-style feel)
user_input = st.text_area("Enter your task:", height=120)

col1, col2 = st.columns([1,1])

with col1:
    run = st.button("🚀 Extract Task")

with col2:
    clear = st.button("🧹 Clear History")

if clear:
    st.session_state.tasks = []

# ---------------- MAIN LOGIC
if run and user_input.strip():

    result = extract_task_info(user_input)

    # store history
    st.session_state.tasks.append({
        "input": user_input,
        "result": result,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    st.success("Task Extracted!")

    # ---------------- RESULT CARDS
    c1, c2, c3 = st.columns(3)

    c1.metric("Task", result["task"])
    c2.metric("Deadline", result["deadline"])
    c3.metric("Days Left", result["days_left"])

    # priority badge
    priority = result["priority"]

    if priority == "HIGH":
        st.error(f"🔴 HIGH PRIORITY")
    elif priority == "MEDIUM":
        st.warning(f"🟡 MEDIUM PRIORITY")
    elif priority == "LOW":
        st.success(f"🟢 LOW PRIORITY")
    elif priority == "OVERDUE":
        st.error(f"⚫ OVERDUE")
    else:
        st.info("⚪ UNKNOWN")

    st.json(result)

# ---------------- HISTORY PANEL
if show_history:
    st.divider()
    st.subheader("📜 Task History")

    for t in reversed(st.session_state.tasks):
        st.markdown(f"""
        **🕒 {t['time']}**  
        **Input:** {t['input']}  
        **Task:** {t['result']['task']}  
        **Priority:** {t['result']['priority']}  
        ---
        """)