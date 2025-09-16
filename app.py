import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import subprocess
import sys
import os

# Set page configuration
st.set_page_config(
    page_title="UofT Study Rooms Schedule",
    page_icon="📚",
    layout="wide"
)

@st.cache_data
def load_data_from_db(db_name="uoft_study_rooms.db"):
    """Load data from SQLite database"""
    try:
        conn = sqlite3.connect(db_name)
        
        # Fetch room info
        rooms_df = pd.read_sql_query("""
            SELECT space_id, room_name, gid, capacity_found_at 
            FROM rooms 
            ORDER BY space_id
        """, conn)
        
        # Fetch timeslot info
        slots_df = pd.read_sql_query("""
            SELECT ts.space_id, ts.start_time, ts.end_time, ts.status, 
                   r.room_name, r.gid, r.capacity_found_at
            FROM time_slots ts
            JOIN rooms r ON ts.space_id = r.space_id
            ORDER BY ts.space_id, ts.start_time
        """, conn)
        
        conn.close()
        
        # Convert datetime
        slots_df['start_time'] = pd.to_datetime(slots_df['start_time'])
        slots_df['end_time'] = pd.to_datetime(slots_df['end_time'])
        slots_df['date'] = slots_df['start_time'].dt.date
        
        return rooms_df, slots_df
        
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def create_schedule_table(slots_df, selected_date, max_rooms=20):
    """Create the schedule table HTML"""
    
    # Filter by date
    day_slots = slots_df[slots_df['date'] == selected_date].copy()
    
    if day_slots.empty:
        st.warning(f"No data found for {selected_date}")
        return
    
    # Create timeslots (every 30 minutes)
    time_slots = []
    for hour in range(8, 23):  # 8:00 AM to 11:00 PM
        for minute in [0, 30]:
            time_slots.append(f"{hour:02d}:{minute:02d}")
    
    # Get room list (limit displayed rooms)
    room_list = sorted(day_slots['space_id'].unique())[:max_rooms]
    
    # HTML + CSS styling
    style = """
    <style>
    .schedule-container {
        max-width: 100%;
        overflow-x: auto;
    }
    .schedule-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11px;
        margin: 20px 0;
    }
    .schedule-table th {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 8px 4px;
        text-align: center;
        font-weight: 600;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .schedule-table td {
        border: 1px solid #dee2e6;
        padding: 4px;
        text-align: center;
        min-width: 35px;
        height: 35px;
        vertical-align: middle;
    }
    .room-name {
        background-color: #f8f9fa;
        color: #000000;
        font-weight: 600;
        text-align: left;
        padding: 8px;
        min-width: 180px;
        position: sticky;
        left: 0;
        z-index: 5;
        border-right: 2px solid #6c757d;
    }
    .room-name small {
        color: #495057;
        font-weight: 500;
    }
    .time-header {
        min-width: 45px;
        writing-mode: vertical-rl;
        text-orientation: mixed;
        background-color: #f1f3f4;
        font-size: 10px;
        color: #000000;
        font-weight: 600;
    }
    .available {
        background-color: #28a745;
        color: #000000;
        font-weight: bold;
        font-size: 14px;
    }
    .unavailable {
        background-color: #f8d7da;
        color: #000000;
        font-weight: bold;
        font-size: 14px;
    }
    .empty {
        background-color: #f8f9fa;
    }
    </style>
    """
    
    html = style + '<div class="schedule-container"><table class="schedule-table">'
    
    # Table header
    html += '<thead><tr><th class="room-name">Room / Time</th>'
    for time_slot in time_slots:
        html += f'<th class="time-header">{time_slot}</th>'
    html += '</tr></thead><tbody>'
    
    # Rows for each room
    for room_id in room_list:
        room_data = day_slots[day_slots['space_id'] == room_id]
        room_name = room_data['room_name'].iloc[0] if not room_data.empty else f"Room {room_id}"
        
        # Simplify room name
        display_name = room_name.replace('Group Study Room ', 'GSR ') if 'Group Study Room' in room_name else room_name
        html += f'<tr><td class="room-name">{display_name}<br><small>({room_id})</small></td>'
        
        # Cells for each timeslot
        for time_slot in time_slots:
            slot_data = room_data[room_data['start_time'].dt.strftime('%H:%M') == time_slot]
            
            if not slot_data.empty:
                status = slot_data['status'].iloc[0]
                if status == 'available':
                    html += '<td class="available"></td>'
                else:
                    html += '<td class="unavailable"></td>'
            else:
                html += '<td class="empty"></td>'
        
        html += '</tr>'
    
    html += '</tbody></table></div>'
    
    return html

def get_available_dates_from_db(db_name="uoft_study_rooms.db"):
    """Get list of available dates from DB"""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT query_date, COUNT(*) as slot_count 
            FROM time_slots 
            GROUP BY query_date 
            ORDER BY query_date
        ''')
        dates_data = cursor.fetchall()
        conn.close()
        return dates_data
    except Exception as e:
        print(f"Failed to fetch dates: {e}")
        return []

def fetch_schedule_for_date(target_date, force_refresh=False):
    """Call script.py to fetch schedule for a given date"""
    try:
        if isinstance(target_date, str):
            target_date_str = target_date
        else:
            target_date_str = target_date.strftime('%Y-%m-%d')
        
        # Skip if already present (unless refresh forced)
        if not force_refresh:
            conn = sqlite3.connect("uoft_study_rooms.db")
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM time_slots WHERE query_date = ?', (target_date_str,))
            existing_count = cursor.fetchone()[0]
            conn.close()
            
            if existing_count > 0:
                return True, f"Data for {target_date_str} already exists ({existing_count} records). Use refresh to update."
        
        # Import and run script.py
        script_path = os.path.join(os.getcwd(), 'script.py')
        import importlib.util
        spec = importlib.util.spec_from_file_location("script", script_path)
        script_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script_module)
        
        script_module.check_all_rooms_availability_sqlite(target_date_str, target_date_str)
        
        action = "refreshed" if force_refresh else "fetched"
        return True, f"Successfully {action} data for {target_date_str}"
        
    except Exception as e:
        return False, f"Failed to fetch schedule: {str(e)}"

def main():
    st.title("📚 UofT Study Rooms - Schedule View")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        rooms_df, slots_df = load_data_from_db()
    
    if rooms_df.empty or slots_df.empty:
        st.error("Could not load data. Please ensure DB file exists and contains data.")
        return
    
    # Sidebar
    st.sidebar.header("📅 Options")
    
    gid_options = {
        "All Rooms": None,
        "Robarts Common": 7314,
        "Robarts Library Stacks": 7466,
        "Robarts Library Ground Floor": 7474,
        "Robarts Library 3rd Floor": 7708,
        "Individual Study Rooms": 7816
    }
    
    selected_gid_label = st.sidebar.selectbox(
        "Select room type",
        list(gid_options.keys())
    )
    selected_gid = gid_options[selected_gid_label]
    
    # Filter by gid
    if selected_gid is not None:
        filtered_rooms_df = rooms_df[rooms_df['gid'] == selected_gid]
        filtered_slots_df = slots_df[slots_df['gid'] == selected_gid]
    else:
        filtered_rooms_df = rooms_df
        filtered_slots_df = slots_df
    
    # Date selection
    available_dates = sorted(filtered_slots_df['date'].unique())
    if not available_dates:
        st.error("No data for selected room type")
        return
        
    selected_date = st.sidebar.date_input(
        "Select date",
        value=available_dates[0],
        min_value=min(available_dates),
        max_value=max(available_dates)
    )
    
    # Show all rooms
    max_rooms = len(filtered_rooms_df)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rooms of this type", len(filtered_rooms_df))
    with col2:
        day_data = filtered_slots_df[filtered_slots_df['date'] == selected_date]
        st.metric("Total slots today", len(day_data))
    with col3:
        available_today = len(day_data[day_data['status'] == 'available']) if not day_data.empty else 0
        st.metric("Available today", available_today)
    with col4:
        unavailable_today = len(day_data[day_data['status'] == 'unavailable']) if not day_data.empty else 0
        st.metric("Unavailable today", unavailable_today)
    
    st.markdown("---")
    
    # Legend
    st.markdown("### 📋 Legend")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🟢 **✓ Available** - Timeslot can be booked")
    with col2:
        st.markdown("🔴 **✗ Unavailable** - Timeslot already booked or not available")
    with col3:
        st.markdown("⚪ **Blank** - No data or closed")
    
    st.markdown("---")
    
    # Schedule table
    st.markdown(f"### 📅 {selected_date} - {selected_gid_label}")
    
    html_table = create_schedule_table(filtered_slots_df, selected_date, max_rooms)
    if html_table:
        st.markdown(html_table, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
