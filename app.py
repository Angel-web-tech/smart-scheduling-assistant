import streamlit as st
import pandas as pd
import datetime
import sqlite3
from streamlit_calendar import calendar

# =====================================================
# DATABASE
# =====================================================
conn = sqlite3.connect("meetings.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS meetings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    start TEXT,
    end TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tasks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    priority TEXT
)
""")

conn.commit()


# ------------------ DB FUNCTIONS ---------------------

def save_meeting(title, start, end):
    c.execute("INSERT INTO meetings(title,start,end) VALUES (?,?,?)", (title, start, end))
    conn.commit()


def load_meetings():
    c.execute("SELECT id,title,start,end FROM meetings")
    return c.fetchall()


def delete_meeting(mid):
    c.execute("DELETE FROM meetings WHERE id=?", (mid,))
    conn.commit()


def save_task(name, priority):
    c.execute("INSERT INTO tasks(name,priority) VALUES (?,?)", (name, priority))
    conn.commit()


def load_tasks():
    c.execute("SELECT name,priority FROM tasks")
    return c.fetchall()


# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Smart Scheduling Assistant",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Smart Scheduling Assistant")
st.write("AI-powered meeting scheduler with conflict detection & smart suggestions")


# =====================================================
# SIDEBAR SETTINGS
# =====================================================
st.sidebar.header("⚙ Settings")

work_start = st.sidebar.time_input("Work start", datetime.time(9, 0))
work_end = st.sidebar.time_input("Work end", datetime.time(17, 0))
duration = st.sidebar.slider("Meeting duration (min)", 15, 180, 30)
buffer_time = st.sidebar.slider("Buffer between meetings (min)", 0, 30, 10)
avoid_lunch = st.sidebar.checkbox("Avoid lunch (12–1)", True)


# =====================================================
# HELPER FUNCTIONS
# =====================================================
def to_minutes(t):
    return t.hour * 60 + t.minute


def parse(slot):
    s, e = slot.split("-")
    sh, sm = map(int, s.split(":"))
    eh, em = map(int, e.split(":"))
    return sh * 60 + sm, eh * 60 + em


def fmt(m):
    return f"{m//60:02}:{m%60:02}"


# =====================================================
# ADD MEETING FORM
# =====================================================
st.subheader("➕ Add Meeting")

with st.form("add_meeting"):
    title = st.text_input("Meeting Title")
    start_time = st.time_input("Start Time")
    end_time = st.time_input("End Time")

    if st.form_submit_button("Add Meeting"):
        save_meeting(title, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"))
        st.success("Meeting added!")
        st.rerun()


# =====================================================
# SHOW + DELETE MEETINGS (CRUD)
# =====================================================
st.subheader("📋 Saved Meetings")

rows = load_meetings()

for mid, title, s, e in rows:
    col1, col2 = st.columns([4, 1])
    col1.write(f"**{title}**  |  {s} - {e}")
    if col2.button("Delete", key=f"del{mid}"):
        delete_meeting(mid)
        st.rerun()


# =====================================================
# BUILD BUSY SLOTS
# =====================================================
busy = []

for _, _, s, e in rows:
    busy.append(parse(f"{s}-{e}"))

if avoid_lunch:
    busy.append((12 * 60, 13 * 60))

busy = [(s - buffer_time, e + buffer_time) for s, e in busy]
busy = sorted(busy)


# =====================================================
# FIND FREE SLOTS
# =====================================================
day_start = to_minutes(work_start)
day_end = to_minutes(work_end)

free = []
start = day_start

for s, e in busy:
    if start < s:
        free.append((start, s))
    start = max(start, e)

if start < day_end:
    free.append((start, day_end))


# =====================================================
# METRICS
# =====================================================
total = day_end - day_start
busy_time = sum(max(0, e - s) for s, e in busy)
free_time = total - busy_time

c1, c2, c3 = st.columns(3)
c1.metric("Total Work", f"{total} min")
c2.metric("Busy", f"{busy_time} min")
c3.metric("Free", f"{free_time} min")


# =====================================================
# BAR CHART
# =====================================================
st.subheader("📊 Time Usage Chart")

chart_df = pd.DataFrame({
    "Type": ["Busy", "Free"],
    "Minutes": [busy_time, free_time]
})

st.bar_chart(chart_df.set_index("Type"))


# =====================================================
# EXPORT CSV
# =====================================================
st.subheader("⬇ Export Schedule")

export_slots = [(fmt(s), fmt(e)) for s, e in free]
df = pd.DataFrame(export_slots, columns=["Start", "End"])

st.download_button(
    "Download CSV",
    df.to_csv(index=False).encode(),
    "schedule.csv",
    "text/csv"
)


# =====================================================
# CALENDAR VIEW
# =====================================================
st.subheader("📅 Calendar View")

events = []
today = datetime.date.today().isoformat()

for _, title, s, e in rows:
    events.append({
        "title": title,
        "start": f"{today}T{s}:00",
        "end": f"{today}T{e}:00"
    })

calendar(events=events, options={
    "initialView": "timeGridDay",
    "allDaySlot": False
}, key="calendar")


# =====================================================
# SMART SUGGESTIONS
# =====================================================
st.subheader("✨ Smart Suggestions")

suggestions = []

for s, e in free:
    if e - s >= duration:
        score = 0
        if s < 12 * 60:
            score += 2
        if e > 16 * 60:
            score -= 1
        suggestions.append((score, s, e))

suggestions.sort(reverse=True)

if suggestions:
    best = suggestions[0]
    st.success(f"Best Slot → {fmt(best[1])} - {fmt(best[2])}")
    for score, s, e in suggestions:
        st.info(f"{fmt(s)} - {fmt(e)}")
else:
    st.error("No slots available")


# =====================================================
# CONFLICT DETECTION
# =====================================================
st.subheader("🚨 Conflict Detection")

conflict = False
for i in range(len(busy) - 1):
    if busy[i][1] > busy[i + 1][0]:
        conflict = True

if conflict:
    st.warning("Meetings overlap!")
else:
    st.success("No conflicts detected")


# =====================================================
# TASK MANAGER
# =====================================================
st.subheader("📝 Tasks")

task_name = st.text_input("Task")
priority = st.selectbox("Priority", ["High", "Medium", "Low"])

if st.button("Add Task"):
    save_task(task_name, priority)
    st.success("Task saved!")

for name, p in load_tasks():
    st.write(f"{name} ({p})")
