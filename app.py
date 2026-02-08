import streamlit as st
import pandas as pd
import datetime
import sqlite3
from streamlit_calendar import calendar

# ================= DATABASE =================
conn = sqlite3.connect("meetings.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS meetings(
    start TEXT,
    end TEXT
)
""")
conn.commit()

def save_meeting(start, end):
    c.execute("INSERT INTO meetings VALUES (?,?)", (start, end))
    conn.commit()

# ================= PAGE SETTINGS =================
st.set_page_config(
    page_title="Smart Scheduling Assistant",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Smart Scheduling Assistant")
st.write("AI-powered meeting scheduler with conflict detection & smart suggestions")

# ================= SIDEBAR =================
st.sidebar.header("⚙ Settings")

work_start = st.sidebar.time_input("Work start time", datetime.time(9, 0))
work_end = st.sidebar.time_input("Work end time", datetime.time(17, 0))

duration = st.sidebar.slider("Meeting duration (minutes)", 15, 180, 30)
buffer_time = st.sidebar.slider("Buffer between meetings (minutes)", 0, 30, 10)

avoid_lunch = st.sidebar.checkbox("Avoid lunch (12–1 PM)", True)

# ================= INPUT =================
st.subheader("📌 Existing Meetings")

meetings_input = st.text_area(
    "Enter meetings (HH:MM-HH:MM, comma separated)",
    "09:00-10:00, 13:00-14:00"
)

# ================= FUNCTIONS =================
def to_minutes(t):
    return t.hour * 60 + t.minute

def parse(slot):
    s, e = slot.split("-")
    sh, sm = map(int, s.split(":"))
    eh, em = map(int, e.split(":"))
    return sh * 60 + sm, eh * 60 + em

def fmt(m):
    return f"{m//60:02}:{m%60:02}"

# ================= PROCESS =================
busy = []

for x in meetings_input.split(","):
    if x.strip():
        s, e = parse(x.strip())
        busy.append((s, e))
        save_meeting(fmt(s), fmt(e))

if avoid_lunch:
    busy.append((12 * 60, 13 * 60))

busy = [(s - buffer_time, e + buffer_time) for s, e in busy]
busy = sorted(busy)

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

# ================= METRICS =================
total = day_end - day_start
busy_time = sum(max(0, e - s) for s, e in busy)
free_time = total - busy_time

c1, c2, c3 = st.columns(3)
c1.metric("Total Work Time", f"{total} min")
c2.metric("Busy Time", f"{busy_time} min")
c3.metric("Free Time", f"{free_time} min")

# ================= EXPORT CSV =================
st.subheader("⬇ Export Schedule")

export_slots = [(fmt(s), fmt(e)) for s, e in free]
df = pd.DataFrame(export_slots, columns=["Start", "End"])

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Schedule (CSV)",
    data=csv,
    file_name="schedule.csv",
    mime="text/csv"
)

# ================= CALENDAR VIEW =================
st.subheader("📅 Calendar View")

events = []
today = datetime.date.today().isoformat()

for s, e in free:
    events.append({
        "title": "Free Slot",
        "start": f"{today}T{fmt(s)}:00",
        "end": f"{today}T{fmt(e)}:00"
    })

calendar_options = {
    "initialView": "timeGridDay",
    "slotMinTime": "08:00:00",
    "slotMaxTime": "18:00:00",
    "allDaySlot": False,
}

if not events:
    st.info("No free slots to display on calendar.")

calendar(
    events=events,
    options=calendar_options,
    key="calendar",
)

# ================= SMART SUGGESTIONS =================
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

if not suggestions:
    st.error("No available slots found")
else:
    best = suggestions[0]
    st.success(f"💡 Best Slot: {fmt(best[1])} - {fmt(best[2])}")

    for score, s, e in suggestions:
        st.info(f"{fmt(s)} - {fmt(e)}")

# ================= CONFLICT DETECTION =================
st.subheader("🚨 Conflict Detection")

conflict = False
for i in range(len(busy) - 1):
    if busy[i][1] > busy[i + 1][0]:
        conflict = True

if conflict:
    st.warning("⚠ Some meetings overlap!")
else:
    st.success("✅ No conflicts detected")
