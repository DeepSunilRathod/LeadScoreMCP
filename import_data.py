"""
import_data.py — Import calls.csv as PRIMARY dataset (1000 rows = Total Leads)
Then import call_recordings.csv rows (marked source='recording') to bring in
transcripts, WITHOUT affecting the primary lead count.
"""

import csv
from datetime import datetime
from lib.db import get_conn

CALLS_CSV = "calls.csv"
RECORDINGS_CSV = "call_recordings.csv"
TRANSCRIPTS_CSV = "transcripts.csv"


def parse_datetime(value):
    if not value or value == "NULL":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def duration_to_seconds(duration_str):
    if not duration_str or duration_str == "NULL":
        return 0
    try:
        parts = duration_str.split(":")
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        return 0


def load_transcripts():
    transcripts = {}
    with open(TRANSCRIPTS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            call_id = row["call_id"].strip()
            transcripts[call_id] = {
                "transcript": row["transcript"],
                "status": row["status"],
            }
    print(f"Loaded {len(transcripts)} transcripts")
    return transcripts


def build_rows(csv_file, transcripts, source_label):
    rows = []
    with_transcript = 0
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            call_id = row["id"].strip()

            transcript_data = transcripts.get(call_id)
            transcript_text = None
            transcript_status = "pending"

            if transcript_data and transcript_data["status"] == "done":
                transcript_text = transcript_data["transcript"]
                transcript_status = "done"
                with_transcript += 1

            rows.append((
                call_id,
                row["lead_id"],
                row["agent_name"],
                row["to_number"],
                duration_to_seconds(row["call_duration"]),
                parse_datetime(row["start_time"]),
                row["status"],
                transcript_text,
                transcript_status,
                row.get("call_type", ""),
                row.get("recording_url", ""),
                source_label,
            ))
    return rows, with_transcript


def insert_rows(rows):
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT IGNORE INTO calls
        (id, lead_id, agent_name, phone_number, call_duration_sec,
         call_date, status, transcript, transcript_status,
         call_type, recording_url, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )
    conn.commit()
    inserted = cur.rowcount
    cur.close()
    conn.close()
    return inserted


def import_calls():
    transcripts = load_transcripts()

    # Step 1: Import calls.csv (PRIMARY — this defines "Total Leads")
    primary_rows, primary_with_transcript = build_rows(CALLS_CSV, transcripts, "primary")
    print(f"\nPrepared {len(primary_rows)} PRIMARY calls from {CALLS_CSV}")
    primary_inserted = insert_rows(primary_rows)
    print(f"Inserted: {primary_inserted} primary calls (transcripts matched: {primary_with_transcript})")

    # Step 2: Import call_recordings.csv (SECONDARY — brings in transcripts only)
    recording_rows, recording_with_transcript = build_rows(RECORDINGS_CSV, transcripts, "recording")
    print(f"\nPrepared {len(recording_rows)} RECORDING calls from {RECORDINGS_CSV}")
    recording_inserted = insert_rows(recording_rows)
    print(f"Inserted: {recording_inserted} recording calls (transcripts matched: {recording_with_transcript})")

    print(f"\nDone! Total transcripts available: {primary_with_transcript + recording_with_transcript}")


if __name__ == "__main__":
    import_calls()