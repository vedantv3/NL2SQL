import sqlite3

db = sqlite3.connect('clinic.db')

queries = [
    ('Q1', 'SELECT COUNT(*) AS total_patients FROM patients'),
    ('Q2', 'SELECT name, specialization, department FROM doctors ORDER BY name'),
    ('Q3', "SELECT * FROM appointments WHERE appointment_date >= date('now','start of month','-1 month') AND appointment_date < date('now','start of month')"),
    ('Q4', 'SELECT d.name, COUNT(a.id) AS appt_count FROM doctors d JOIN appointments a ON d.id=a.doctor_id GROUP BY d.id ORDER BY appt_count DESC LIMIT 1'),
    ('Q5', 'SELECT SUM(total_amount) AS total_revenue FROM invoices'),
    ('Q6', 'SELECT d.name, SUM(i.total_amount) AS revenue FROM doctors d JOIN appointments a ON d.id=a.doctor_id JOIN invoices i ON a.patient_id=i.patient_id GROUP BY d.name ORDER BY revenue DESC'),
    ('Q7', "SELECT COUNT(*) AS cancelled FROM appointments WHERE status='Cancelled' AND appointment_date>=date('now','-3 months')"),
    ('Q8', 'SELECT p.first_name, p.last_name, SUM(i.total_amount) AS spent FROM patients p JOIN invoices i ON p.id=i.patient_id GROUP BY p.id ORDER BY spent DESC LIMIT 5'),
    ('Q9', 'SELECT d.specialization, AVG(t.cost) AS avg_cost FROM doctors d JOIN appointments a ON d.id=a.doctor_id JOIN treatments t ON a.id=t.appointment_id GROUP BY d.specialization'),
    ('Q10', "SELECT strftime('%Y-%m',appointment_date) AS month, COUNT(*) AS cnt FROM appointments WHERE appointment_date>=date('now','-6 months') GROUP BY month ORDER BY month"),
    ('Q11', 'SELECT city, COUNT(*) AS cnt FROM patients GROUP BY city ORDER BY cnt DESC LIMIT 1'),
    ('Q12', 'SELECT p.first_name, p.last_name, COUNT(a.id) AS visits FROM patients p JOIN appointments a ON p.id=a.patient_id GROUP BY p.id HAVING visits > 3'),
    ('Q13', "SELECT * FROM invoices WHERE status IN ('Pending','Overdue')"),
    ('Q14', "SELECT ROUND(100.0 * SUM(CASE WHEN status='No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct FROM appointments"),
    ('Q15', "SELECT strftime('%w', appointment_date) AS dow, COUNT(*) AS cnt FROM appointments GROUP BY dow ORDER BY cnt DESC"),
    ('Q16', "SELECT strftime('%Y-%m', invoice_date) AS month, SUM(total_amount) AS revenue FROM invoices GROUP BY month ORDER BY month"),
    ('Q17', 'SELECT d.name, AVG(t.duration_minutes) AS avg_dur FROM doctors d JOIN appointments a ON d.id=a.doctor_id JOIN treatments t ON a.id=t.appointment_id GROUP BY d.id'),
    ('Q18', "SELECT DISTINCT p.first_name, p.last_name, i.total_amount FROM patients p JOIN invoices i ON p.id=i.patient_id WHERE i.status='Overdue'"),
    ('Q19', 'SELECT d.department, SUM(i.total_amount) AS rev FROM doctors d JOIN appointments a ON d.id=a.doctor_id JOIN invoices i ON a.patient_id=i.patient_id GROUP BY d.department ORDER BY rev DESC'),
    ('Q20', "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS cnt FROM patients GROUP BY month ORDER BY month"),
]

for qid, sql in queries:
    try:
        cur = db.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        sample = str(rows[0]) if rows else "empty"
        print(f"{qid}: OK | {len(rows)} rows | cols={cols} | sample={sample}")
    except Exception as e:
        print(f"{qid}: ERR | {e}")

db.close()
