import streamlit as st
from datetime import time, datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(page_title="Smart Scheduling Assistant", layout="wide")

# -----------------------
# Helpers
# -----------------------

def time_to_float(t):
    return t.hour + t.minute / 60


def float_to_time(h):
    hour = int(h)
    minute = int((h - hour) * 60)
    return f"{hour:02d}:{minute:02d}"


# -----------------------
# Calendar Plot
# -----------------------

def draw_calendar(meetings, start_hour, end_hour):
    fig, ax = plt.subplots(figsize=(10, 2))

    for s, e in meetings:
        s = time_to_float(s)
        e = time_to_float(e)
        ax.barh(0, e - s, left=s)

    ax.set_xlim(start_hour, end_hour)
    ax.set_yticks([])
    ax.set_xlabel("Time (hours)")
    ax.set_title("Daily Schedule Timeline")

    st.pyplot(fig)


# -----------------------
# Free Slot Finder
# -----------------------

def find_free_slots(start_hour, end_hour, duration, buffer_mins, meetings):

    meetings_sorted = sorted(meetings, key=lambda x: x[0])
    current = start_hour
    free = []

    duration_hr = duration / 60
    buffer_hr = buffer_mins / 60

    for s, e in meetings_sorted:

        s = time_to_float(s)
        e = time_to_float(e)

        if s - current >= duration_hr:
            free.append((current, s))

        current = e + buffer_hr

    if end_hour - current >= duration_hr:
        free.append((current, end_hour))

    return free


# -----------------------
# Title
# -----------------------

st.title("📅 Smart Scheduling Assistant")
st.caption("AI-powered meeting scheduler with conflict detection & smart suggestions")

# -----------------------
# Sidebar Settings
# -----------------------

st.sidebar.header("⚙ Settings")

work_start = st.sidebar.time_input("Work start time", time(9, 0))
work_end = st.sidebar.time_input("Work end time", time(17, 0))

duration = st.sidebar.slider("Meeting duration (minutes)", 15, 120, 30)
buffer_time = st.sidebar.slider("Buffer between meetings (minutes)", 0, 30, 10)

avoid_lunch = st.sidebar.checkbox("Avoid lunch (12–1 PM)", True)


# -----------------------
# Session state
# -----------------------

if "meetings" not in st.session_state:
    st.session_state.meetings = []


# -----------------------
# Add Meeting UI
# -----------------------

st.subheader("➕ Add Meeting")

col1, col2, col3 = st.columns(3)

start = col1.time_input("Start time")
end = col2.time_input("End time")

if col3.button("Add Meeting"):
    if start < end:
        st.session_state.meetings.append((start, end))
    else:
        st.warning("End time must be after start time")


# -----------------------
# Existing Meetings
# -----------------------

st.subheader("📌 Existing Meetings")

for i, (s, e) in enumerate(st.session_state.meetings):
    c1, c2 = st.columns([5, 1])

    c1.write(f"{s.strftime('%H:%M')} - {e.strftime('%H:%M')}")

    if c2.button("❌", key=i):
        st.session_state.meetings.pop(i)
        st.rerun()


# -----------------------
# Lunch Block
# -----------------------

meetings_for_calc = list(st.session_state.meetings)

if avoid_lunch:
    meetings_for_calc.append((time(12, 0), time(13, 0)))


# -----------------------
# Stats
# -----------------------

start_hour = time_to_float(work_start)
end_hour = time_to_float(work_end)

total_time = (end_hour - start_hour) * 60

busy = sum(
    (time_to_float(e) - time_to_float(s)) * 60
    for s, e in meetings_for_calc
)

free = total_time - busy

c1, c2, c3 = st.columns(3)

c1.metric("Total Work Time", f"{int(total_time)} min")
c2.metric("Busy Time", f"{int(busy)} min")
c3.metric("Free Time", f"{int(free)} min")


# -----------------------
# Calendar View
# -----------------------

st.subheader("🗓 Calendar View")
draw_calendar(meetings_for_calc, start_hour, end_hour)


# -----------------------
# Free Slot Suggestions
# -----------------------

st.subheader("💡 Suggested Free Slots")

slots = find_free_slots(
    start_hour,
    end_hour,
    duration,
    buffer_time,
    meetings_for_calc
)

for s, e in slots:
    st.write(f"✅ {float_to_time(s)} - {float_to_time(e)}")


# -----------------------
# Export CSV
# -----------------------

st.subheader("⬇ Export Schedule")

data = [
    {
        "Start": s.strftime("%H:%M"),
        "End": e.strftime("%H:%M")
    }
    for s, e in meetings_for_calc
]

df = pd.DataFrame(data)

st.download_button(
    "Download CSV",
    df.to_csv(index=False),
    file_name="schedule.csv"
)
