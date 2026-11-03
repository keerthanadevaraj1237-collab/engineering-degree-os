from pathlib import Path
from datetime import date, timedelta
import pandas as pd
import streamlit as st

st.set_page_config(page_title="My Engineering Degree OS", page_icon="🎓", layout="wide")

DATA_DIR = Path(__file__).parent / "data"
FILES = {
    "semesters": "semesters.csv",
    "courses": "courses.csv",
    "calendar": "academic_calendar.csv",
    "assessments": "assessments.csv",
    "scores": "scores.csv",
    "plan": "plan_checklist.csv",
}
DEFAULTS = {
    "semesters": ["semester","status","total_credits","completed_credits"],
    "courses": ["semester","course_code","course_name","credits","faculty","syllabus","status"],
    "calendar": ["academic_year","semester","date","event_type","title"],
    "assessments": ["semester","course_code","assessment_type","date","max_marks","status"],
    "scores": ["semester","course_code","assessment_type","score","max_marks","grade"],
    "plan": ["category","item","target_date","status","notes"],
}

def load_data(key):
    path = DATA_DIR / FILES[key]
    if not path.exists():
        st.warning(f"Missing file: data/{FILES[key]}. Create it to use this section.")
        return pd.DataFrame(columns=DEFAULTS[key])
    try:
        df = pd.read_csv(path)
        for col in DEFAULTS[key]:
            if col not in df.columns:
                df[col] = ""
        return df[DEFAULTS[key]]
    except Exception as exc:
        st.error(f"Could not read {FILES[key]}: {exc}")
        return pd.DataFrame(columns=DEFAULTS[key])

def save_data(key, df):
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(DATA_DIR / FILES[key], index=False)

def as_dates(series):
    return pd.to_datetime(series, errors="coerce").dt.date

data = {key: load_data(key) for key in FILES}
semesters, courses = data["semesters"], data["courses"]
calendar, assessments, scores, plan = data["calendar"], data["assessments"], data["scores"], data["plan"]

st.title("🎓 My Engineering Degree OS")
st.caption("A personal command centre for your 1st-to-8th semester engineering journey.")
pages = ["Dashboard", "Semesters 1-8", "Courses & Syllabus", "University Syllabus",
         "Academic / Leave Calendar", "Internal Assessments", "Status Tracker",
         "Scorecard", "Plan & Checklist", "Ask Degree AI", "Data Admin"]
page = st.sidebar.radio("Navigate", pages)
st.sidebar.divider()
st.sidebar.caption("Prototype data is provided for demonstration. Replace it with your official college information.")

if page == "Dashboard":
    st.header("Dashboard")
    current = semesters[semesters["status"].astype(str).str.lower().eq("in progress")]
    current_sem = int(current.iloc[0]["semester"]) if not current.empty else 1
    total_credits = pd.to_numeric(semesters.get("total_credits", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    completed_credits = pd.to_numeric(semesters.get("completed_credits", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    completion = (completed_credits / total_credits * 100) if total_credits else 0
    next_assessment = assessments.copy()
    if not next_assessment.empty:
        next_assessment["date_parsed"] = pd.to_datetime(next_assessment["date"], errors="coerce")
        next_assessment = next_assessment[next_assessment["date_parsed"] >= pd.Timestamp.today().normalize()].sort_values("date_parsed")
    next_holiday = calendar[calendar["event_type"].astype(str).str.lower().isin(["holiday","leave"])] .copy()
    if not next_holiday.empty:
        next_holiday["date_parsed"] = pd.to_datetime(next_holiday["date"], errors="coerce")
        next_holiday = next_holiday[next_holiday["date_parsed"] >= pd.Timestamp.today().normalize()].sort_values("date_parsed")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Current semester", f"Semester {current_sem}")
    c2.metric("Degree completion", f"{completion:.1f}%")
    c3.metric("Credits completed", f"{completed_credits:g} / {total_credits:g}")
    score_pct = None
    if not scores.empty:
        got = pd.to_numeric(scores["score"], errors="coerce").sum()
        maximum = pd.to_numeric(scores["max_marks"], errors="coerce").sum()
        score_pct = got / maximum * 100 if maximum else None
    c4.metric("Prototype score", f"{score_pct:.1f}%" if score_pct is not None else "No scores")
    st.subheader("Semester progress")
    chart = semesters.copy()
    chart["completed_credits"] = pd.to_numeric(chart["completed_credits"], errors="coerce").fillna(0)
    chart["total_credits"] = pd.to_numeric(chart["total_credits"], errors="coerce").fillna(0)
    chart["Progress %"] = chart.apply(lambda r: (r["completed_credits"]/r["total_credits"]*100) if r["total_credits"] else 0, axis=1)
    if not chart.empty:
        st.bar_chart(chart.set_index("semester")["Progress %"])
    left,right = st.columns(2)
    with left:
        st.subheader("Next assessment")
        if not next_assessment.empty:
            r = next_assessment.iloc[0]
            st.info(f'{r["assessment_type"]} — {r["course_code"]} on {r["date"]}')
        else:
            st.write("No upcoming assessment found in the current data.")
    with right:
        st.subheader("Next holiday / leave")
        if not next_holiday.empty:
            r = next_holiday.iloc[0]
            st.info(f'{r["title"]} — {r["date"]}')
        else:
            st.write("No upcoming holiday found in the current data.")

elif page == "Semesters 1-8":
    st.header("Semesters 1-8")
    cols = st.columns(4)
    for idx, row in semesters.sort_values("semester").iterrows():
        with cols[int(row["semester"]-1) % 4]:
            sem = int(row["semester"])
            sem_courses = courses[pd.to_numeric(courses["semester"], errors="coerce") == sem]
            st.subheader(f"Semester {sem}")
            st.write(f'**Status:** {row["status"]}')
            st.write(f'**Courses:** {len(sem_courses)}')
            st.write(f'**Credits:** {row["completed_credits"]} / {row["total_credits"]}')
            total = pd.to_numeric(pd.Series([row["total_credits"]]), errors="coerce").fillna(0).iloc[0]
            done = pd.to_numeric(pd.Series([row["completed_credits"]]), errors="coerce").fillna(0).iloc[0]
            st.progress(min(1.0, done/total) if total else 0.0)

elif page == "Courses & Syllabus":
    st.header("Courses & Syllabus")
    sem = st.selectbox("Select semester", list(range(1,9)), index=2)
    filtered = courses[pd.to_numeric(courses["semester"], errors="coerce") == sem]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption("Update course codes, credits, faculty and topics in Data Admin.")

elif page == "University Syllabus":
    st.header("University Syllabus")
    st.write("Programme-level syllabus overview")
    st.write("- Programme: Engineering (edit this to your branch and university)")
    st.write("- Duration: 8 semesters")
    st.write("- Expected credits: enter the official programme total after verification.")
    st.text_input("Official syllabus source / reference", key="syllabus_source",
                  placeholder="Paste your university syllabus URL or document reference")
    st.warning("This prototype does not contain a verified university regulation or official CGPA formula. Add the official source before relying on programme rules.")

elif page == "Academic / Leave Calendar":
    st.header("Academic / Leave Calendar")
    if not calendar.empty:
        years = sorted(calendar["academic_year"].dropna().astype(str).unique().tolist())
        year = st.selectbox("Academic year", years) if years else None
        sems = sorted(pd.to_numeric(calendar["semester"], errors="coerce").dropna().astype(int).unique().tolist())
        selected_sem = st.selectbox("Semester", sems) if sems else None
        view = calendar.copy()
        if year is not None: view = view[view["academic_year"].astype(str) == year]
        if selected_sem is not None: view = view[pd.to_numeric(view["semester"], errors="coerce") == selected_sem]
        st.dataframe(view.sort_values("date"), use_container_width=True, hide_index=True)
    else:
        st.info("No calendar records yet. Add them in Data Admin.")

elif page == "Internal Assessments":
    st.header("Internal Assessments")
    if not assessments.empty:
        sem = st.selectbox("Filter by semester", list(range(1,9)), index=2)
        view = assessments[pd.to_numeric(assessments["semester"], errors="coerce") == sem]
        st.dataframe(view.sort_values("date"), use_container_width=True, hide_index=True)
    else: st.info("No assessment records yet.")

elif page == "Status Tracker":
    st.header("Status Tracker")
    if not courses.empty:
        sem = st.selectbox("Select semester", list(range(1,9)), key="status_sem")
        view = courses[pd.to_numeric(courses["semester"], errors="coerce") == sem]
        counts = view["status"].value_counts()
        a,b,c = st.columns(3)
        a.metric("Not Started", int(counts.get("Not Started",0)))
        b.metric("In Progress", int(counts.get("In Progress",0)))
        c.metric("Completed", int(counts.get("Completed",0)))
        done = int((view["status"] == "Completed").sum())
        st.progress(done/len(view) if len(view) else 0.0, text=f"{done} of {len(view)} courses completed")
        st.dataframe(view[["course_code","course_name","status"]], use_container_width=True, hide_index=True)
    else: st.info("No course data yet.")

elif page == "Scorecard":
    st.header("Scorecard")
    if not scores.empty:
        view = scores.copy()
        view["score"] = pd.to_numeric(view["score"], errors="coerce")
        view["max_marks"] = pd.to_numeric(view["max_marks"], errors="coerce")
        st.dataframe(view, use_container_width=True, hide_index=True)
        total_score = view["score"].sum()
        total_max = view["max_marks"].sum()
        pct = total_score/total_max*100 if total_max else 0
        st.metric("Prototype score percentage", f"{pct:.2f}%")
        st.caption("This is a simple total-score percentage, not an official university CGPA.")
    else: st.info("No scores available. Add sample or actual scores in Data Admin.")

elif page == "Plan & Checklist":
    st.header("Plan & Checklist")
    if not plan.empty:
        editable = st.data_editor(plan, use_container_width=True, hide_index=True,
                                  num_rows="dynamic", key="plan_editor")
        if st.button("Save checklist changes", type="primary"):
            save_data("plan", editable)
            st.success("Checklist saved to data/plan_checklist.csv")
            st.rerun()
        dates = pd.to_datetime(plan["target_date"], errors="coerce").dt.date
        today = date.today()
        done_count = int((plan["status"].astype(str).str.lower() == "done").sum())
        due_soon = int(((dates >= today) & (dates <= today + timedelta(days=7)) & (plan["status"] != "Done")).sum())
        overdue = int(((dates < today) & (plan["status"] != "Done")).sum())
        x,y,z = st.columns(3)
        x.metric("Done", done_count); y.metric("Due soon", due_soon); z.metric("Overdue", overdue)
    else: st.info("Add checklist rows in Data Admin.")

elif page == "Ask Degree AI":
    st.header("Ask Degree AI")
    st.caption("This version answers from your CSV files using local rules. It does not need an API key.")
    question = st.text_input("Ask about your degree", placeholder="What courses are incomplete in Semester 3?")
    if st.button("Ask", type="primary") and question.strip():
        q = question.lower()
        answer = None
        source = "Degree data"
        if "incomplete" in q or "left" in q or "remaining" in q:
            import re
            match = re.search(r"sem(?:ester)?\s*(\d+)", q)
            sem = int(match.group(1)) if match else 3
            rows = courses[(pd.to_numeric(courses["semester"], errors="coerce") == sem) & (courses["status"] != "Completed")]
            answer = f"Semester {sem} incomplete courses: " + (", ".join(rows["course_name"].astype(str)) if not rows.empty else "None found.")
            source = "Courses"
        elif "assessment" in q or "ia" in q or "exam" in q:
            tmp = assessments.copy()
            tmp["parsed"] = pd.to_datetime(tmp["date"], errors="coerce")
            tmp = tmp[tmp["parsed"] >= pd.Timestamp.today().normalize()].sort_values("parsed")
            answer = ("Next assessment: " + str(tmp.iloc[0]["assessment_type"]) + " for " + str(tmp.iloc[0]["course_code"]) + " on " + str(tmp.iloc[0]["date"])) if not tmp.empty else "No upcoming assessment is listed."
            source = "Assessments"
        elif "holiday" in q or "leave" in q:
            tmp = calendar[calendar["event_type"].astype(str).str.lower().isin(["holiday","leave"])].copy()
            tmp["parsed"] = pd.to_datetime(tmp["date"], errors="coerce")
            tmp = tmp[tmp["parsed"] >= pd.Timestamp.today().normalize()].sort_values("parsed")
            answer = ("Next holiday: " + str(tmp.iloc[0]["title"]) + " on " + str(tmp.iloc[0]["date"])) if not tmp.empty else "No upcoming holiday is listed."
            source = "Calendar"
        elif "topic" in q or "syllabus" in q:
            matches = courses[courses["course_name"].astype(str).str.lower().apply(lambda n: any(word in q for word in n.split() if len(word)>3))]
            answer = "; ".join(matches["course_name"].astype(str) + ": " + matches["syllabus"].astype(str)) if not matches.empty else "I cannot verify that from the current Degree OS data."
            source = "Courses"
        elif "checklist" in q or "task" in q or "plan" in q:
            answer = "; ".join(plan["item"].astype(str) + " — " + plan["status"].astype(str)) if not plan.empty else "No checklist items are listed."
            source = "Plan"
        elif "cgpa" in q or "eligibility" in q or "regulation" in q or "official" in q:
            answer = "I cannot verify that from the current Degree OS data."
            source = "Not available"
        else:
            answer = "I cannot verify that from the current Degree OS data. Try asking about incomplete courses, assessments, holidays, syllabus topics or checklist tasks."
            source = "Not available"
        st.success(answer)
        st.caption(f"Data area used: {source}")

elif page == "Data Admin":
    st.header("Data Admin")
    st.write("Edit a table below and save it. Changes are stored in the matching CSV file.")
    labels = {"semesters":"Semesters","courses":"Courses","calendar":"Academic calendar",
              "assessments":"Assessments","scores":"Scores","plan":"Plan & checklist"}
    chosen = st.selectbox("Choose data table", list(labels.keys()), format_func=lambda x: labels[x])
    edited = st.data_editor(data[chosen], use_container_width=True, hide_index=True,
                            num_rows="dynamic", key=f"admin_{chosen}")
    if st.button("Save table to CSV", type="primary"):
        save_data(chosen, edited)
        st.success(f"Saved data/{FILES[chosen]}")
        st.rerun()

st.divider()
st.caption("My Engineering Degree OS • Student prototype • Verify all official academic dates, credits and regulations with your institution.")
