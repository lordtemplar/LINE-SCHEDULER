import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="LINE Scheduler", initial_sidebar_state="collapsed")

# Light theme accent, very mild
st.markdown("""
    <style>
    h1, h2, h3, .stTabs [data-baseweb="tab-list"] {color:#174EA6 !important;}
    .stButton button, .stForm button {background: #F3F8FE; color: #174EA6; border-radius:6px;}
    .stButton button:hover, .stForm button:hover {background: #E1EDFA;}
    .stTextInput > div > div > input, .stTextArea textarea {background-color: #FBFCFE;}
    .stDataFrame thead tr th {background: #F3F8FE !important; color:#222;}
    </style>
""", unsafe_allow_html=True)

# Google Sheets Setup
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]
# ดึงจาก secrets
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_NAME = "LINE Scheduler"
SCHEDULER_SHEET = "Scheduler Table"
TARGET_SHEET = "User/Group Table"

sheet_scheduler = client.open(SPREADSHEET_NAME).worksheet(SCHEDULER_SHEET)
sheet_targets = client.open(SPREADSHEET_NAME).worksheet(TARGET_SHEET)

# Load data
scheduler = pd.DataFrame(sheet_scheduler.get_all_records())
targets = pd.DataFrame(sheet_targets.get_all_records())

st.title("LINE Message Scheduler")

tabs = st.tabs([
    "New Message",
    "Edit/Delete Message",
    "New Recipient",
    "Edit/Delete Recipient"
])

# TAB 1: NEW SCHEDULE
with tabs[0]:
    st.header("New Scheduled Message")
    st.dataframe(scheduler, use_container_width=True, hide_index=True)

    # Default values (set only on first load)
    if 'msg_text' not in st.session_state:
        st.session_state.msg_text = ''
    if 'msg_date' not in st.session_state:
        st.session_state.msg_date = datetime.now().date()
    if 'msg_time' not in st.session_state:
        st.session_state.msg_time = (datetime.now() + pd.Timedelta(minutes=1)).time().replace(second=0, microsecond=0)
    if not targets.empty and 'msg_target' not in st.session_state:
        target_options = [f"{row['Name']} | {row['TargetID']}" for idx, row in targets.iterrows()]
        st.session_state.msg_target = target_options[0]
    
    with st.form("add_schedule"):
        message = st.text_area("Message", max_chars=500, value=st.session_state.msg_text)
        date = st.date_input("Date", value=st.session_state.msg_date)
        time = st.time_input("Time", value=st.session_state.msg_time)
        if not targets.empty:
            target_options = [f"{row['Name']} | {row['TargetID']}" for idx, row in targets.iterrows()]
            target_choice = st.selectbox(
                "Recipient (User/Group)",
                options=target_options,
                index=target_options.index(st.session_state.msg_target)
            )
            target_id = target_choice.split('|')[-1].strip()
        else:
            target_id = ""
            st.warning("No recipients found. Please add a recipient first.")
        submitted = st.form_submit_button("Add Message")
        if submitted:
            if message and target_id:
                dt = datetime.combine(date, time)
                new_row = [
                    dt.strftime("%Y-%m-%d %H:%M"),
                    message,
                    target_id,
                    "Pending"
                ]
                sheet_scheduler.append_row(new_row)
                st.success("Message scheduled successfully.")
                # ----------- KEEP ALL FORM VALUES (do not reset session_state) -----------
                st.session_state.msg_text = message
                st.session_state.msg_date = date
                st.session_state.msg_time = time
                st.session_state.msg_target = target_choice
                st.rerun()
            else:
                st.error("Please fill in all fields.")

# --- Tab 2: Edit/Delete Message ---
with tabs[1]:
    st.header("Edit / Delete Scheduled Message")
    # เพิ่มปุ่มไปยัง Google Sheets
    st.markdown(
        """
        <a href="https://docs.google.com/spreadsheets/d/1L4zdfGcNw1a0ckYEDOMcYBTTkf1XgfSsvh8hFZNcH7Q/edit?usp=sharing" target="_blank">
            <button style="background-color:#174EA6;color:#fff;padding:6px 16px;border:none;border-radius:6px;font-weight:bold;cursor:pointer;">
                Open Google Sheets
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )
    # เพิ่มช่องว่าง
    st.markdown("<br>", unsafe_allow_html=True)  # สามารถใช้หลายบรรทัดได้ "<br><br>"
    
    if not scheduler.empty:
        for idx, row in scheduler.iterrows():
            with st.expander(f"{row['Datetime']} | {row['Message'][:30]}..."):
                with st.form(f"edit_sched_{idx}", clear_on_submit=True):
                    new_msg = st.text_area("Edit Message", value=row["Message"])
                    date_e = st.date_input("Edit Date", value=pd.to_datetime(row["Datetime"]).date(), key=f"edit_date_{idx}")
                    time_e = st.time_input("Edit Time", value=pd.to_datetime(row["Datetime"]).time().replace(second=0, microsecond=0), key=f"edit_time_{idx}")
                    dt_e = datetime.combine(date_e, time_e)
                    if not targets.empty and row["TargetID"] in targets["TargetID"].values:
                        target_idx = int(targets.index[targets["TargetID"] == row["TargetID"]][0])
                        target_options = [f"{t['Name']} | {t['TargetID']}" for _, t in targets.iterrows()]
                        new_target = st.selectbox(
                            "Edit Recipient (User/Group)",
                            options=target_options,
                            index=target_idx,
                            key=f"edit_target_{idx}"
                        )
                        new_target_id = new_target.split('|')[-1].strip()
                    else:
                        new_target_id = row["TargetID"]
                    update = st.form_submit_button("Update")
                    delete = st.form_submit_button("Delete")
                    if update:
                        sheet_scheduler.update_cell(idx + 2, 1, dt_e.strftime("%Y-%m-%d %H:%M"))
                        sheet_scheduler.update_cell(idx + 2, 2, new_msg)
                        sheet_scheduler.update_cell(idx + 2, 3, new_target_id)
                        st.success("Message updated successfully.")
                        st.rerun()
                    if delete:
                        sheet_scheduler.delete_rows(idx + 2)
                        st.success("Message deleted successfully.")
                        st.rerun()
    else:
        st.info("No scheduled messages found.")

# --- Tab 3: New Recipient ---
with tabs[2]:
    st.header("New Recipient")
    st.dataframe(targets, use_container_width=True, hide_index=True)
    with st.form("add_target", clear_on_submit=True):
        t_type = st.selectbox("Type", options=["Person", "Group"], key="addtype")
        name = st.text_input("Name", key="addname")
        target_id = st.text_input("TargetID (LINE ID: Uxxx or Cxxx)", key="addid")
        submitted_add = st.form_submit_button("Add Recipient")
        if submitted_add:
            if target_id and (name or t_type == "Group"):
                sheet_targets.append_row([target_id, t_type, name])
                st.success("Recipient added successfully.")
                st.rerun()
            else:
                st.warning("Please fill in all fields.")

# --- Tab 4: Edit/Delete Recipient ---
with tabs[3]:
    st.header("Edit / Delete Recipient")
    if not targets.empty:
        for idx, row in targets.iterrows():
            with st.expander(f"{row['Name']} | {row['TargetID']}"):
                with st.form(f"edit_target_{idx}", clear_on_submit=True):
                    t_type_e = st.selectbox("Type", options=["Person", "Group"], index=0 if row["Type"] == "Person" else 1, key=f"edittype_{idx}")
                    name_e = st.text_input("Name", value=row["Name"], key=f"editname_{idx}")
                    target_id_e = st.text_input("TargetID", value=row["TargetID"], key=f"editid_{idx}")
                    update = st.form_submit_button("Update")
                    delete = st.form_submit_button("Delete")
                    if update:
                        sheet_targets.update_cell(idx + 2, 1, target_id_e)
                        sheet_targets.update_cell(idx + 2, 2, t_type_e)
                        sheet_targets.update_cell(idx + 2, 3, name_e)
                        st.success("Recipient updated successfully.")
                        st.rerun()
                    if delete:
                        sheet_targets.delete_rows(idx + 2)
                        st.success("Recipient deleted successfully.")
                        st.rerun()
    else:
        st.info("No recipients found.")
