import streamlit as st
import datetime as dt
import plotly.express as px
import pandas as pd
import json
from solver import get_schedule
# disaply wide
st.set_page_config(layout="wide")

school_tab, classes_tab, teachers_tab, schedule_tab = st.tabs(["School info", "Classes", "Teachers", "Schedule"])
st.session_state.start_date = dt.datetime(2024, 2, 12)

def plot_schedule(schedule, weekday):
    
    schedule = [event for event in schedule if event["weekday"] == weekday]
    df_events = pd.DataFrame(schedule, columns=["classroom", "weekday", "start_period", "duration", "subject", "teacher"])
    df_events["start"] = df_events["start_period"]*30
    df_events["end"] = df_events["start"] + df_events["duration"]
    df_events["start"] = st.session_state.start_date + pd.to_timedelta(df_events["start"], unit="m")
    df_events["end"] = st.session_state.start_date + pd.to_timedelta(df_events["end"], unit="m")
    
    fig = px.timeline(df_events, x_start="start", x_end="end", y="classroom", color="subject", labels={"weekday": "Weekday", "start_period": "Start period", "end_period": "End period", "subject": "Subject"}, title="Schedule", hover_data={"teacher": True})
    fig.update_yaxes(categoryorder="category descending")
    fig.update_xaxes(title_text="30 minutes periods")
    # set x ticks every 30 minutes until 24 hours
    fig.update_xaxes(range=[st.session_state.start_date, st.session_state.start_date + pd.Timedelta(24, "h")])
    tickvals = pd.date_range(st.session_state.start_date, st.session_state.start_date + pd.Timedelta(24, "h"), freq="60min")
    # keep time only without date
    ticktext = [time.strftime("%H:%M") for time in tickvals]
    fig.update_xaxes(tickmode="array", tickvals=tickvals, ticktext=ticktext)
    # y range 0 to 7
    fig.update_yaxes(range=[-0.5, st.session_state.num_classrooms - 0.5])
    fig.update_layout(width=1400, showlegend=True, legend_title_text="Subject", legend_traceorder="reversed")
    # width of elements
    fig.update_traces(width= 0.6)
    return fig


exmaple_file = "example.json"
if "default_example" not in st.session_state:
    with open(exmaple_file, "r") as file:
        st.session_state.default_example = json.load(file)
    

with school_tab:
    st.title("School information")
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    st.session_state.weekdays_info = [None]*len(weekdays)
    st.header("Number of classrooms")
    num_classrooms_col, _ = st.columns([1, 3])
    st.session_state.num_classrooms = num_classrooms_col.number_input("Number of classrooms", 1, 100, value=st.session_state.default_example["num_classrooms"])
    st.header("Opening hours")
    for i in range(len(weekdays)):
        st.subheader(weekdays[i])
        start_col, end_col, open_col, _ = st.columns([2, 2, 1, 3])
        st.session_state.weekdays_info[i] = {
            "weekday": weekdays[i],
            "start": start_col.time_input(f"Start time", value=dt.time(hour=8), key=f"start_weekday_{i}"),
            "end": end_col.time_input(f"End time", value=dt.time(hour=21), key=f"end_weekday_{i}"),
            "open": open_col.checkbox(f"Open", value=True, key=f"open_weekday_{i}")
        }

with classes_tab:
    def add_classroom():
        st.session_state.classes_info.append({
            "subject": "",
            "amount": 1,
            "duration_hours": 1,
            "duration_minutes": 0,
        })

    def delete_classroom(index):
        st.session_state.classes_info.pop(index)

    st.title("Classes")
    if "classes_info" not in st.session_state:
        st.session_state.classes_info = st.session_state.default_example["classes"]
    for i in range(len(st.session_state.classes_info)):
        subject_col, amount_col, duration_hours_col, duration_minutes_col, delete_col, _ = st.columns([3, 1, 1, 1, 1, 3])
        st.session_state.classes_info[i] = {
            "subject": subject_col.text_input("Subject", value=st.session_state.classes_info[i]["subject"], key=f"subject_{i}"),
            "amount": amount_col.number_input("Amount", 1, 100, value=st.session_state.classes_info[i]["amount"], key=f"amount_{i}"),
            "duration_hours": duration_hours_col.number_input("Duration (hours)", 0, 24, st.session_state.classes_info[i]["duration_hours"], key=f"duration_hours_{i}"),
            "duration_minutes": duration_minutes_col.number_input("Duration (minutes)", 0, 59, st.session_state.classes_info[i]["duration_minutes"], key=f"duration_minutes_{i}"),
        }
        # delete col with cross emoji
        delete_col.button("❌", on_click=delete_classroom, args=(i,), key=f"delete_{i}")
    # add classtoom with + emoji
    st.button("➕ Add subject", on_click=add_classroom, key="add_classroom")
    st.session_state.subjects_list = set([classroom["subject"] for classroom in st.session_state.classes_info])

with teachers_tab:
    def add_teacher():
        st.session_state.teachers_info.append({
            "name": "",
            "subjects": [],
        })

    def delete_teacher(index):
        st.session_state.teachers_info.pop(index)

    st.title("Teachers")
    if "teachers_info" not in st.session_state:
        st.session_state.teachers_info = st.session_state.default_example["teachers"]
    for i in range(len(st.session_state.teachers_info)):
        name_col, subjects_col, delete_col, _ = st.columns([2, 2, 1, 3])
        st.session_state.teachers_info[i] = {
            "name": name_col.text_input("Name", value=st.session_state.teachers_info[i]["name"], key=f"name_{i}"),
            "subjects": subjects_col.multiselect("Subjects", list(st.session_state.subjects_list), default=list(set(st.session_state.teachers_info[i]["subjects"]).intersection(set(st.session_state.subjects_list))), key=f"subjects_{i}"),
        }
        # delete col with cross emoji
        delete_col.button("❌", on_click=delete_teacher, args=(i,), key=f"delete_teacher_{i}")
    # add teacher with + emoji
    st.button("➕ Add teacher", on_click=add_teacher, key="add_teacher")

with schedule_tab:
    st.title("Schedule")
    
    # button schedule with rocket emoji
    if st.button("🚀 Generate schedule", key="generate_schedule"):
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule = get_schedule(st.session_state.num_classrooms, st.session_state.weekdays_info, st.session_state.classes_info, st.session_state.teachers_info)
        if schedule:
            for weekday in range(len(st.session_state.weekdays_info)):
                st.subheader(weekdays[weekday])
                fig = plot_schedule(schedule, weekday)
                st.plotly_chart(fig)

