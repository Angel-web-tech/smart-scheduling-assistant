import streamlit as st
import datetime

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
        busy.append(parse(x.strip()))

# add lunch block
if avoid_lunch:
    busy.append((12 * 60, 13 * 60))

# apply buffer
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

# ================= SUGGESTIONS =================
st.subheader("✨ Suggested Time Slots")

suggestions = []

for s, e in free:
    if e - s >= duration:
        score = 0

        if s < 12 * 60:  # prefer morning
            score += 2
        if e > 16 * 60:  # avoid late
            score -= 1

        suggestions.append((score, s, e))

suggestions.sort(reverse=True)

if not suggestions:
    st.error("No available slots found")
else:
    for score, s, e in suggestions:
        st.success(f"{fmt(s)} - {fmt(e)}")

# ================= CONFLICT DETECTION =================
st.subheader("🚨 Conflict Detection")

conflict = False

for i in range(len(busy) - 1):
    if busy[i][1] > busy[i + 1][0]:
        conflict = True

if conflict:
    st.warning("⚠ Some meetings overlap!")
else:
    st.info("✅ No conflicts detected")
