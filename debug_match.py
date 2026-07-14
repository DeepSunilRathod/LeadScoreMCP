import csv

# Load transcript call_ids
transcript_ids = set()
with open("transcripts.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    print("Transcript CSV columns:", reader.fieldnames)
    for row in reader:
        transcript_ids.add(row["call_id"].strip())

print(f"\nTotal transcript call_ids: {len(transcript_ids)}")
print("Sample transcript call_ids:", list(transcript_ids)[:5])

# Load calls.csv ids
call_ids = set()
with open("calls.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    print("\nCalls CSV columns:", reader.fieldnames)
    for row in reader:
        call_ids.add(row["id"].strip())

print(f"\nTotal call ids: {len(call_ids)}")
print("Sample call ids:", list(call_ids)[:5])

# Check overlap
overlap = transcript_ids & call_ids
print(f"\n🔍 Matching IDs found: {len(overlap)}")
print("Sample matches:", list(overlap)[:5])

print(f"\ncalls.csv ID range: {min(int(i) for i in call_ids)} to {max(int(i) for i in call_ids)}")
print(f"transcripts.csv ID range: {min(int(i) for i in transcript_ids)} to {max(int(i) for i in transcript_ids)}")