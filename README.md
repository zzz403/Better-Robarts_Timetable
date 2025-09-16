# Better Robarts Timetable

University of Toronto Robarts Library Study Room Availability Query System

## Features

* Batch retrieval of all study room availability
* Supports multiple data sources (direct API, local JSON import)
* SQLite database storage for efficient querying
* Web interface display (based on Streamlit)
* Supports queries by date range

## Usage

### 1. Data Retrieval

Run the main script to fetch study room data:

```bash
python script.py
```

In the menu, choose **Option 2** - "Batch fetch availability for all rooms (API)"

* Enter start date (format: YYYY-MM-DD, default: today)
* Enter end date (format: YYYY-MM-DD, default: tomorrow)
* Confirm to start batch data retrieval

### 2. Launch Web Interface

After data retrieval is complete, start the web application:

```bash
streamlit run app.py
```

Then open the displayed address in your browser to view study room availability.

## Project Structure

* `script.py` - Main data retrieval and processing script
* `app.py` - Streamlit web application
* `uoft_study_rooms.db` - SQLite database file
* `uoft_study_rooms.csv` - Study room metadata file

## Notes

* First-time use requires running `script.py` to fetch data
* Data retrieval may take a few minutes, please be patient
* It is recommended to update data regularly for the latest availability

## Dependencies

* Python 3.x
* requests
* sqlite3
* streamlit
* csv
* datetime

## Quick Start

1. Clone the project
2. Run `python script.py`, choose Option 2 to fetch data
3. Run `streamlit run app.py` to launch the web interface
4. Open your browser to view study room availability
