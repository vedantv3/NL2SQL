"""
setup_database.py - Creates the clinic SQLite database with schema and realistic dummy data.

Run: python setup_database.py
Produces: clinic.db
"""

import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "clinic.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    date_of_birth DATE,
    gender TEXT,
    city TEXT,
    registered_date DATE
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialization TEXT,
    department TEXT,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    doctor_id INTEGER,
    appointment_date DATETIME,
    status TEXT,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER,
    treatment_name TEXT,
    cost REAL,
    duration_minutes INTEGER,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    invoice_date DATE,
    total_amount REAL,
    paid_amount REAL,
    status TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
"""

# ---------------------------------------------------------------------------
# Realistic dummy data pools
# ---------------------------------------------------------------------------

FIRST_NAMES_M = [
    "James", "Robert", "John", "Michael", "David", "William", "Richard",
    "Joseph", "Thomas", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
    "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin",
    "Brian", "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey",
    "Ryan", "Jacob", "Gary", "Nicholas", "Eric", "Jonathan", "Stephen",
    "Larry", "Justin", "Scott", "Brandon", "Benjamin", "Samuel",
]

FIRST_NAMES_F = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth",
    "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty",
    "Margaret", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily",
    "Donna", "Michelle", "Carol", "Amanda", "Melissa", "Deborah",
    "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia", "Kathleen",
    "Amy", "Angela", "Shirley", "Anna", "Brenda", "Pamela", "Emma",
    "Nicole", "Helen",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin",
]

SPECIALIZATIONS = [
    "Dermatology", "Cardiology", "Orthopedics", "General", "Pediatrics",
]

# Map specialization → department name
DEPT_MAP = {
    "Dermatology": "Dermatology",
    "Cardiology": "Cardiology",
    "Orthopedics": "Orthopedics",
    "General": "General Medicine",
    "Pediatrics": "Pediatrics",
}

DOCTOR_FIRST = [
    "Dr. Sarah", "Dr. James", "Dr. Priya", "Dr. Michael", "Dr. Anita",
    "Dr. Robert", "Dr. Emily", "Dr. David", "Dr. Maria", "Dr. William",
    "Dr. Jennifer", "Dr. Ahmed", "Dr. Laura", "Dr. Chen", "Dr. Raj",
]

DOCTOR_LAST = [
    "Patel", "Smith", "Kumar", "Johnson", "Williams",
    "Chen", "Martinez", "Brown", "Lee", "Garcia",
    "Anderson", "Wilson", "Taylor", "Thomas", "Moore",
]

TREATMENT_NAMES = [
    "Blood Test", "X-Ray", "MRI Scan", "ECG", "Ultrasound",
    "Physical Therapy", "Dental Cleaning", "Skin Biopsy", "Allergy Test",
    "Vaccination", "CT Scan", "Endoscopy", "Colonoscopy",
    "Joint Injection", "Wound Dressing", "Eye Exam", "Hearing Test",
    "Chemotherapy Session", "Dialysis", "Minor Surgery",
]

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]

NOTES_POOL = [
    "Follow-up required in 2 weeks.",
    "Patient reported improvement.",
    "Referred to specialist.",
    "Lab results pending.",
    "Prescription renewed.",
    "No complications observed.",
    "Patient needs further tests.",
    "Routine check-up.",
    None, None, None,  # ~27 % chance of NULL notes
]


def random_date(start: datetime, end: datetime) -> str:
    """Return a random date string between start and end."""
    delta = (end - start).days
    rand_days = random.randint(0, max(delta, 1))
    return (start + timedelta(days=rand_days)).strftime("%Y-%m-%d")


def random_datetime(start: datetime, end: datetime) -> str:
    """Return a random datetime string between start and end."""
    delta = int((end - start).total_seconds())
    rand_secs = random.randint(0, max(delta, 1))
    dt = start + timedelta(seconds=rand_secs)
    # Snap to working hours 08:00-18:00
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    dt = dt.replace(hour=hour, minute=minute, second=0)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def random_phone() -> str:
    return f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"


def build_database():
    """Create schema and insert all dummy data."""
    import os
    # Remove old DB if exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)

    now = datetime.now()
    one_year_ago = now - timedelta(days=365)

    # ------------------------------------------------------------------
    # 1. Doctors (15 across 5 specializations → 3 per specialization)
    # ------------------------------------------------------------------
    doctors = []
    for i, spec in enumerate(SPECIALIZATIONS):
        for j in range(3):
            idx = i * 3 + j
            name = f"{DOCTOR_FIRST[idx]} {DOCTOR_LAST[idx]}"
            phone = random_phone()
            doctors.append((name, spec, DEPT_MAP[spec], phone))

    cur.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
        doctors,
    )
    doctor_ids = list(range(1, len(doctors) + 1))

    # ------------------------------------------------------------------
    # 2. Patients (200)
    # ------------------------------------------------------------------
    patients = []
    for _ in range(200):
        gender = random.choice(["M", "F"])
        first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        last = random.choice(LAST_NAMES)
        # ~15 % chance email is NULL
        email = (
            f"{first.lower()}.{last.lower()}{random.randint(1,99)}@example.com"
            if random.random() > 0.15
            else None
        )
        # ~10 % chance phone is NULL
        phone = random_phone() if random.random() > 0.10 else None
        dob = random_date(datetime(1950, 1, 1), datetime(2010, 12, 31))
        city = random.choice(CITIES)
        reg_date = random_date(one_year_ago, now)
        patients.append((first, last, email, phone, dob, gender, city, reg_date))

    cur.executemany(
        "INSERT INTO patients (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date) "
        "VALUES (?,?,?,?,?,?,?,?)",
        patients,
    )
    patient_ids = list(range(1, len(patients) + 1))

    # ------------------------------------------------------------------
    # 3. Appointments (500) — spread across 12 months
    # ------------------------------------------------------------------
    # Create some "repeat visitors" (20 % of patients get 5-10 visits)
    repeat_patients = random.sample(patient_ids, k=40)  # 20 % of 200
    # Some doctors are busier
    busy_doctors = random.sample(doctor_ids, k=5)

    appointments = []
    for _ in range(500):
        # 40 % chance to pick a repeat patient
        if random.random() < 0.40 and repeat_patients:
            pid = random.choice(repeat_patients)
        else:
            pid = random.choice(patient_ids)

        # 50 % chance to pick a busy doctor
        if random.random() < 0.50 and busy_doctors:
            did = random.choice(busy_doctors)
        else:
            did = random.choice(doctor_ids)

        appt_dt = random_datetime(one_year_ago, now)
        # Weighted statuses: 55 % Completed, 20 % Scheduled, 15 % Cancelled, 10 % No-Show
        status = random.choices(
            APPOINTMENT_STATUSES, weights=[20, 55, 15, 10], k=1
        )[0]
        notes = random.choice(NOTES_POOL)
        appointments.append((pid, did, appt_dt, status, notes))

    cur.executemany(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes) "
        "VALUES (?,?,?,?,?)",
        appointments,
    )

    # ------------------------------------------------------------------
    # 4. Treatments (350) — linked to *completed* appointments
    #    Some appointments may have more than one treatment.
    # ------------------------------------------------------------------
    cur.execute("SELECT id FROM appointments WHERE status = 'Completed'")
    completed_ids = [row[0] for row in cur.fetchall()]

    treatments = []
    remaining = 350
    # First pass: one treatment per completed appointment
    shuffled = completed_ids.copy()
    random.shuffle(shuffled)
    for appt_id in shuffled:
        if remaining <= 0:
            break
        tname = random.choice(TREATMENT_NAMES)
        cost = round(random.uniform(50, 5000), 2)
        duration = random.choice([15, 20, 30, 45, 60, 90, 120])
        treatments.append((appt_id, tname, cost, duration))
        remaining -= 1

    # Second pass: add extra treatments to random completed appointments
    while remaining > 0:
        appt_id = random.choice(completed_ids)
        tname = random.choice(TREATMENT_NAMES)
        cost = round(random.uniform(50, 5000), 2)
        duration = random.choice([15, 20, 30, 45, 60, 90, 120])
        treatments.append((appt_id, tname, cost, duration))
        remaining -= 1

    cur.executemany(
        "INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes) "
        "VALUES (?,?,?,?)",
        treatments,
    )

    # ------------------------------------------------------------------
    # 5. Invoices (300) — mix of Paid / Pending / Overdue
    # ------------------------------------------------------------------
    invoices = []
    for _ in range(300):
        pid = random.choice(patient_ids)
        inv_date = random_date(one_year_ago, now)
        total = round(random.uniform(100, 8000), 2)
        # Weighted: 50 % Paid, 30 % Pending, 20 % Overdue
        status = random.choices(INVOICE_STATUSES, weights=[50, 30, 20], k=1)[0]
        if status == "Paid":
            paid = total
        elif status == "Pending":
            paid = round(random.uniform(0, total * 0.5), 2)
        else:  # Overdue
            paid = round(random.uniform(0, total * 0.3), 2)
        invoices.append((pid, inv_date, total, paid, status))

    cur.executemany(
        "INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status) "
        "VALUES (?,?,?,?,?)",
        invoices,
    )

    conn.commit()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    counts = {}
    for table in ["patients", "doctors", "appointments", "treatments", "invoices"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 — safe, table names are hardcoded
        counts[table] = cur.fetchone()[0]

    conn.close()

    print(
        f"Created {counts['patients']} patients, "
        f"{counts['doctors']} doctors, "
        f"{counts['appointments']} appointments, "
        f"{counts['treatments']} treatments, "
        f"{counts['invoices']} invoices."
    )
    print(f"Database saved to {DB_PATH}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible data
    build_database()
