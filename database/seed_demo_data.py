"""
TransitNotice – Demo Data Seed Script
Seeds realistic Tamil Nadu transport data for MTC, TNSTC, SETC, CMRL.
Run once after init_db.py:
    python database/seed_demo_data.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from database.db import init_pool, DBCursor, fetchone
from config import get_config

cfg = get_config()
init_pool(cfg)

print("Seeding demo transport data...")

# ── 1. Ensure transport_sources exist and are seeded ─────────────────────────
SOURCES = [
    (1, "MTC",   "MTC Chennai Official Website",          "https://www.mtcbus.org",              1, 0),
    (2, "TNSTC", "TNSTC Official Website",                "https://www.tnstc.in",                1, 0),
    (3, "SETC",  "SETC Official Website",                 "https://www.tnstc.in/setc",           1, 0),
    (4, "CMRL",  "CMRL GTFS Open Data Feed",              "https://www.chennaimetrorail.org",     1, 0),
]

with DBCursor() as cur:
    for sid, provider, name, url, auth, enabled in SOURCES:
        cur.execute("SELECT id FROM transport_sources WHERE id=%s", (sid,))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO transport_sources
                   (id, provider, source_name, source_url, is_authorized, is_enabled, fetch_status)
                   VALUES (%s,%s,%s,%s,%s,%s,'success')""",
                (sid, provider, name, url, auth, enabled),
            )
    print("  ✓ transport_sources seeded")

# ── 2. Route data ─────────────────────────────────────────────────────────────
ROUTES = [
    # (source_id, provider, route_number, route_name, direction, origin, destination, service_type, distance_km)
    # MTC Chennai Routes
    (1, "MTC", "1",    "Parry's Corner – Thiruvanmiyur",        "outbound", "Parry's Corner",        "Thiruvanmiyur",        "Ordinary", 18.0),
    (1, "MTC", "5",    "Koyambedu – Chrompet",                  "outbound", "Koyambedu CMBT",        "Chrompet",             "Ordinary", 15.5),
    (1, "MTC", "11",   "Thiruvotriyur – Guindy",                "outbound", "Thiruvotriyur",         "Guindy",               "Ordinary", 22.0),
    (1, "MTC", "18",   "Parry's Corner – Tambaram",             "outbound", "Parry's Corner",        "Tambaram",             "Ordinary", 25.0),
    (1, "MTC", "21C",  "Koyambedu – Thiruvanmiyur (Via OMR)",   "outbound", "Koyambedu CMBT",        "Thiruvanmiyur",        "Express",  28.5),
    (1, "MTC", "23B",  "Broadway – Anna Nagar",                 "outbound", "Broadway",              "Anna Nagar 2nd Avenue","Ordinary", 12.0),
    (1, "MTC", "47",   "Chennai Central – Velachery",           "outbound", "Chennai Central",       "Velachery",            "Ordinary", 17.0),
    (1, "MTC", "70",   "Broadway – Sholinganallur",             "outbound", "Broadway",              "Sholinganallur",       "Express",  26.0),
    (1, "MTC", "88",   "Koyambedu – Perambur",                  "outbound", "Koyambedu CMBT",        "Perambur",             "Ordinary", 11.0),
    (1, "MTC", "9E",   "Chennai Central – Tambaram (AC)",       "outbound", "Chennai Central",       "Tambaram",             "AC",       26.5),
    (1, "MTC", "500",  "Koyambedu – Airport (Via GST)",         "outbound", "Koyambedu CMBT",        "Chennai Airport",      "AC",       28.0),
    (1, "MTC", "570",  "Chennai Central – Perungudi",           "outbound", "Chennai Central",       "Perungudi",            "Ordinary", 20.0),
    # TNSTC Routes
    (2, "TNSTC", "T-1",   "Chennai – Coimbatore Super Fast",    "outbound", "Chennai (CMBT)",        "Coimbatore",           "Express",  491.0),
    (2, "TNSTC", "T-2",   "Chennai – Madurai Deluxe",           "outbound", "Chennai (CMBT)",        "Madurai",              "Express",  462.0),
    (2, "TNSTC", "T-3",   "Chennai – Salem Ordinary",           "outbound", "Chennai (CMBT)",        "Salem",                "Ordinary", 340.0),
    (2, "TNSTC", "T-4",   "Chennai – Tirunelveli Express",      "outbound", "Chennai (CMBT)",        "Tirunelveli",          "Express",  627.0),
    (2, "TNSTC", "T-5",   "Chennai – Trichy Fast Passenger",    "outbound", "Chennai (CMBT)",        "Trichy",               "Ordinary", 332.0),
    (2, "TNSTC", "T-6",   "Chennai – Vellore Ordinary",         "outbound", "Chennai (CMBT)",        "Vellore",              "Ordinary", 145.0),
    (2, "TNSTC", "T-7",   "Chennai – Pondicherry Express",      "outbound", "Chennai (CMBT)",        "Pondicherry",          "Express",  162.0),
    (2, "TNSTC", "T-8",   "Coimbatore – Madurai Express",       "outbound", "Coimbatore",            "Madurai",              "Express",  205.0),
    (2, "TNSTC", "T-9",   "Chennai – Kanchipuram Ordinary",     "outbound", "Chennai (CMBT)",        "Kanchipuram",          "Ordinary",  75.0),
    (2, "TNSTC", "T-10",  "Chennai – Tirupati Express",         "outbound", "Chennai (CMBT)",        "Tirupati",             "Express",  145.0),
    # SETC Routes
    (3, "SETC", "S-1",  "Chennai – Bangalore AC Sleeper",       "outbound", "Chennai (CMBT)",        "Bangalore Majestic",   "AC",       350.0),
    (3, "SETC", "S-2",  "Chennai – Coimbatore AC Volvo",        "outbound", "Chennai (CMBT)",        "Coimbatore",           "AC",       491.0),
    (3, "SETC", "S-3",  "Chennai – Madurai AC Semi-Sleeper",    "outbound", "Chennai (CMBT)",        "Madurai",              "AC",       462.0),
    (3, "SETC", "S-4",  "Chennai – Tirupati AC Express",        "outbound", "Chennai (CMBT)",        "Tirupati",             "AC",       145.0),
    (3, "SETC", "S-5",  "Chennai – Hyderabad Ultra Deluxe",     "outbound", "Chennai (CMBT)",        "Hyderabad",            "AC",       625.0),
    (3, "SETC", "S-6",  "Chennai – Ooty AC Hill Service",       "outbound", "Chennai (CMBT)",        "Ooty",                 "AC",       540.0),
    # CMRL Metro Lines
    (4, "CMRL", "BL",   "Blue Line – Airport to Wimco Nagar",   "outbound", "Chennai Airport",       "Wimco Nagar",          "Metro",    23.1),
    (4, "CMRL", "GL",   "Green Line – St. Thomas Mount to Nehru Park","outbound","St. Thomas Mount",  "Nehru Park",           "Metro",    22.0),
    (4, "CMRL", "BL-R", "Blue Line – Wimco Nagar to Airport",   "inbound",  "Wimco Nagar",           "Chennai Airport",      "Metro",    23.1),
    (4, "CMRL", "GL-R", "Green Line – Nehru Park to St. Thomas Mount","inbound","Nehru Park",         "St. Thomas Mount",     "Metro",    22.0),
]

route_ids = {}
with DBCursor() as cur:
    for source_id, provider, route_num, name, direction, origin, dest, stype, dist in ROUTES:
        cur.execute("SELECT id FROM routes WHERE route_number=%s AND provider=%s AND direction=%s",
                    (route_num, provider, direction))
        row = cur.fetchone()
        if row:
            route_ids[(provider, route_num, direction)] = row["id"] if isinstance(row, dict) else row[0]
        else:
            cur.execute(
                """INSERT INTO routes
                   (source_id, provider, route_number, route_name, direction,
                    origin, destination, service_type, distance_km, is_active)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)""",
                (source_id, provider, route_num, name, direction, origin, dest, stype, dist),
            )
            route_ids[(provider, route_num, direction)] = cur.lastrowid

print(f"  ✓ {len(ROUTES)} routes seeded")

# ── 3. Schedules ─────────────────────────────────────────────────────────────
# (provider, route_num, direction, departure, arrival, days, trip_num)
SCHEDULES = [
    # MTC Route 1
    ("MTC","1","outbound","05:30:00","06:15:00","1234567","T1-001"),
    ("MTC","1","outbound","06:00:00","06:45:00","1234567","T1-002"),
    ("MTC","1","outbound","07:00:00","07:50:00","1234567","T1-003"),
    ("MTC","1","outbound","08:00:00","08:55:00","1234567","T1-004"),
    ("MTC","1","outbound","09:00:00","09:50:00","1234567","T1-005"),
    ("MTC","1","outbound","10:30:00","11:20:00","1234567","T1-006"),
    ("MTC","1","outbound","12:00:00","12:50:00","1234567","T1-007"),
    ("MTC","1","outbound","14:00:00","14:50:00","1234567","T1-008"),
    ("MTC","1","outbound","16:00:00","16:55:00","1234567","T1-009"),
    ("MTC","1","outbound","18:00:00","18:55:00","1234567","T1-010"),
    ("MTC","1","outbound","20:00:00","20:50:00","1234567","T1-011"),
    ("MTC","1","outbound","21:30:00","22:20:00","1234567","T1-012"),
    # MTC 21C
    ("MTC","21C","outbound","06:00:00","07:10:00","1234567","21C-001"),
    ("MTC","21C","outbound","07:30:00","08:40:00","1234567","21C-002"),
    ("MTC","21C","outbound","09:00:00","10:10:00","1234567","21C-003"),
    ("MTC","21C","outbound","11:00:00","12:10:00","1234567","21C-004"),
    ("MTC","21C","outbound","13:00:00","14:10:00","1234567","21C-005"),
    ("MTC","21C","outbound","15:30:00","16:40:00","1234567","21C-006"),
    ("MTC","21C","outbound","17:30:00","18:45:00","1234567","21C-007"),
    ("MTC","21C","outbound","19:30:00","20:45:00","1234567","21C-008"),
    # MTC 500 (Airport AC)
    ("MTC","500","outbound","04:30:00","05:30:00","1234567","500-001"),
    ("MTC","500","outbound","06:00:00","07:00:00","1234567","500-002"),
    ("MTC","500","outbound","08:00:00","09:00:00","1234567","500-003"),
    ("MTC","500","outbound","10:00:00","11:00:00","1234567","500-004"),
    ("MTC","500","outbound","12:00:00","13:00:00","1234567","500-005"),
    ("MTC","500","outbound","14:00:00","15:00:00","1234567","500-006"),
    ("MTC","500","outbound","16:00:00","17:00:00","1234567","500-007"),
    ("MTC","500","outbound","18:00:00","19:00:00","1234567","500-008"),
    ("MTC","500","outbound","20:00:00","21:00:00","1234567","500-009"),
    ("MTC","500","outbound","22:00:00","23:00:00","1234567","500-010"),
    # MTC 9E
    ("MTC","9E","outbound","06:30:00","07:30:00","1234567","9E-001"),
    ("MTC","9E","outbound","08:30:00","09:30:00","1234567","9E-002"),
    ("MTC","9E","outbound","10:30:00","11:30:00","1234567","9E-003"),
    ("MTC","9E","outbound","12:30:00","13:30:00","1234567","9E-004"),
    ("MTC","9E","outbound","14:30:00","15:30:00","1234567","9E-005"),
    ("MTC","9E","outbound","16:30:00","17:30:00","1234567","9E-006"),
    ("MTC","9E","outbound","18:30:00","19:30:00","1234567","9E-007"),
    ("MTC","9E","outbound","20:30:00","21:30:00","1234567","9E-008"),
    # TNSTC Chennai-Coimbatore
    ("TNSTC","T-1","outbound","06:00:00","14:30:00","1234567","T1-TN-001"),
    ("TNSTC","T-1","outbound","08:00:00","16:30:00","1234567","T1-TN-002"),
    ("TNSTC","T-1","outbound","10:00:00","18:30:00","1234567","T1-TN-003"),
    ("TNSTC","T-1","outbound","12:00:00","20:30:00","1234567","T1-TN-004"),
    ("TNSTC","T-1","outbound","14:00:00","22:30:00","1234567","T1-TN-005"),
    ("TNSTC","T-1","outbound","18:00:00","02:30:00","1234567","T1-TN-006"),
    ("TNSTC","T-1","outbound","21:00:00","05:30:00","1234567","T1-TN-007"),
    ("TNSTC","T-1","outbound","22:30:00","07:00:00","1234567","T1-TN-008"),
    # TNSTC Chennai-Madurai
    ("TNSTC","T-2","outbound","05:30:00","13:00:00","1234567","T2-TN-001"),
    ("TNSTC","T-2","outbound","07:00:00","14:30:00","1234567","T2-TN-002"),
    ("TNSTC","T-2","outbound","09:30:00","17:00:00","1234567","T2-TN-003"),
    ("TNSTC","T-2","outbound","11:00:00","18:30:00","1234567","T2-TN-004"),
    ("TNSTC","T-2","outbound","13:30:00","21:00:00","1234567","T2-TN-005"),
    ("TNSTC","T-2","outbound","16:00:00","23:30:00","1234567","T2-TN-006"),
    ("TNSTC","T-2","outbound","20:00:00","03:30:00","1234567","T2-TN-007"),
    ("TNSTC","T-2","outbound","22:00:00","05:30:00","1234567","T2-TN-008"),
    # TNSTC Pondicherry
    ("TNSTC","T-7","outbound","06:00:00","09:00:00","1234567","T7-TN-001"),
    ("TNSTC","T-7","outbound","07:30:00","10:30:00","1234567","T7-TN-002"),
    ("TNSTC","T-7","outbound","09:00:00","12:00:00","1234567","T7-TN-003"),
    ("TNSTC","T-7","outbound","11:00:00","14:00:00","1234567","T7-TN-004"),
    ("TNSTC","T-7","outbound","13:00:00","16:00:00","1234567","T7-TN-005"),
    ("TNSTC","T-7","outbound","15:00:00","18:00:00","1234567","T7-TN-006"),
    ("TNSTC","T-7","outbound","17:00:00","20:00:00","1234567","T7-TN-007"),
    ("TNSTC","T-7","outbound","19:00:00","22:00:00","1234567","T7-TN-008"),
    # SETC Chennai-Bangalore
    ("SETC","S-1","outbound","07:00:00","13:00:00","1234567","S1-SE-001"),
    ("SETC","S-1","outbound","09:00:00","15:00:00","1234567","S1-SE-002"),
    ("SETC","S-1","outbound","11:00:00","17:00:00","1234567","S1-SE-003"),
    ("SETC","S-1","outbound","14:00:00","20:00:00","1234567","S1-SE-004"),
    ("SETC","S-1","outbound","16:00:00","22:00:00","1234567","S1-SE-005"),
    ("SETC","S-1","outbound","19:00:00","01:00:00","1234567","S1-SE-006"),
    ("SETC","S-1","outbound","21:00:00","03:00:00","1234567","S1-SE-007"),
    ("SETC","S-1","outbound","23:00:00","05:00:00","1234567","S1-SE-008"),
    # SETC Chennai-Coimbatore AC
    ("SETC","S-2","outbound","06:30:00","14:00:00","1234567","S2-SE-001"),
    ("SETC","S-2","outbound","08:30:00","16:00:00","1234567","S2-SE-002"),
    ("SETC","S-2","outbound","10:30:00","18:00:00","1234567","S2-SE-003"),
    ("SETC","S-2","outbound","14:30:00","22:00:00","1234567","S2-SE-004"),
    ("SETC","S-2","outbound","20:30:00","04:00:00","1234567","S2-SE-005"),
    ("SETC","S-2","outbound","22:30:00","06:00:00","1234567","S2-SE-006"),
    # CMRL Blue Line – every 10 min from 05:00 to 23:00
    ("CMRL","BL","outbound","05:00:00","05:45:00","1234567","BL-001"),
    ("CMRL","BL","outbound","05:10:00","05:55:00","1234567","BL-002"),
    ("CMRL","BL","outbound","05:20:00","06:05:00","1234567","BL-003"),
    ("CMRL","BL","outbound","05:30:00","06:15:00","1234567","BL-004"),
    ("CMRL","BL","outbound","06:00:00","06:45:00","1234567","BL-005"),
    ("CMRL","BL","outbound","06:10:00","06:55:00","1234567","BL-006"),
    ("CMRL","BL","outbound","06:20:00","07:05:00","1234567","BL-007"),
    ("CMRL","BL","outbound","07:00:00","07:45:00","1234567","BL-008"),
    ("CMRL","BL","outbound","07:30:00","08:15:00","1234567","BL-009"),
    ("CMRL","BL","outbound","08:00:00","08:45:00","1234567","BL-010"),
    ("CMRL","BL","outbound","08:30:00","09:15:00","1234567","BL-011"),
    ("CMRL","BL","outbound","09:00:00","09:45:00","1234567","BL-012"),
    ("CMRL","BL","outbound","10:00:00","10:45:00","1234567","BL-013"),
    ("CMRL","BL","outbound","11:00:00","11:45:00","1234567","BL-014"),
    ("CMRL","BL","outbound","12:00:00","12:45:00","1234567","BL-015"),
    ("CMRL","BL","outbound","13:00:00","13:45:00","1234567","BL-016"),
    ("CMRL","BL","outbound","14:00:00","14:45:00","1234567","BL-017"),
    ("CMRL","BL","outbound","15:00:00","15:45:00","1234567","BL-018"),
    ("CMRL","BL","outbound","16:00:00","16:45:00","1234567","BL-019"),
    ("CMRL","BL","outbound","17:00:00","17:45:00","1234567","BL-020"),
    ("CMRL","BL","outbound","17:30:00","18:15:00","1234567","BL-021"),
    ("CMRL","BL","outbound","18:00:00","18:45:00","1234567","BL-022"),
    ("CMRL","BL","outbound","18:30:00","19:15:00","1234567","BL-023"),
    ("CMRL","BL","outbound","19:00:00","19:45:00","1234567","BL-024"),
    ("CMRL","BL","outbound","20:00:00","20:45:00","1234567","BL-025"),
    ("CMRL","BL","outbound","21:00:00","21:45:00","1234567","BL-026"),
    ("CMRL","BL","outbound","22:00:00","22:45:00","1234567","BL-027"),
    ("CMRL","BL","outbound","23:00:00","23:45:00","1234567","BL-028"),
    # CMRL Green Line
    ("CMRL","GL","outbound","05:00:00","05:50:00","1234567","GL-001"),
    ("CMRL","GL","outbound","06:00:00","06:50:00","1234567","GL-002"),
    ("CMRL","GL","outbound","07:00:00","07:50:00","1234567","GL-003"),
    ("CMRL","GL","outbound","08:00:00","08:50:00","1234567","GL-004"),
    ("CMRL","GL","outbound","09:00:00","09:50:00","1234567","GL-005"),
    ("CMRL","GL","outbound","10:00:00","10:50:00","1234567","GL-006"),
    ("CMRL","GL","outbound","12:00:00","12:50:00","1234567","GL-007"),
    ("CMRL","GL","outbound","14:00:00","14:50:00","1234567","GL-008"),
    ("CMRL","GL","outbound","16:00:00","16:50:00","1234567","GL-009"),
    ("CMRL","GL","outbound","17:30:00","18:20:00","1234567","GL-010"),
    ("CMRL","GL","outbound","18:00:00","18:50:00","1234567","GL-011"),
    ("CMRL","GL","outbound","19:00:00","19:50:00","1234567","GL-012"),
    ("CMRL","GL","outbound","21:00:00","21:50:00","1234567","GL-013"),
    ("CMRL","GL","outbound","23:00:00","23:50:00","1234567","GL-014"),
]

sched_count = 0
with DBCursor() as cur:
    for provider, route_num, direction, dep, arr, days, trip in SCHEDULES:
        rid = route_ids.get((provider, route_num, direction))
        if not rid:
            continue
        cur.execute("SELECT id FROM schedules WHERE route_id=%s AND trip_number=%s", (rid, trip))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO schedules
                   (route_id, trip_number, departure_time, arrival_time, days_of_week, is_active)
                   VALUES (%s,%s,%s,%s,%s,1)""",
                (rid, trip, dep, arr, days),
            )
            sched_count += 1

print(f"  ✓ {sched_count} schedules seeded")

# ── 4. Stops ─────────────────────────────────────────────────────────────────
STOPS = {
    # (provider, route_num, direction): [(seq, name, code)]
    ("MTC","1","outbound"): [
        (1,"Parry's Corner","PRC"),(2,"Park Town","PRT"),(3,"Egmore","EGM"),
        (4,"Kilpauk","KPK"),(5,"Aminjikarai","AMJ"),(6,"Shenoy Nagar","SNR"),
        (7,"Anna Nagar","ANN"),(8,"Koyambedu","KYB"),(9,"Porur","PRR"),
        (10,"Adyar","ADY"),(11,"Besant Nagar","BSN"),(12,"Thiruvanmiyur","TVM"),
    ],
    ("MTC","21C","outbound"): [
        (1,"Koyambedu CMBT","KYB"),(2,"MMDA Colony","MMD"),(3,"Taramani","TAR"),
        (4,"Perungudi","PRG"),(5,"Sholinganallur","SGL"),(6,"Medavakkam","MDV"),
        (7,"Thoraipakkam","TRP"),(8,"Thiruvanmiyur","TVM"),
    ],
    ("MTC","500","outbound"): [
        (1,"Koyambedu CMBT","KYB"),(2,"CMBT Phase 2","CMB2"),(3,"Ashok Nagar","ASN"),
        (4,"Vadapalani","VDP"),(5,"Saidapet","SDP"),(6,"Guindy","GDY"),
        (7,"St. Thomas Mount","STM"),(8,"Meenambakkam","MNB"),(9,"Chennai Airport","MAA"),
    ],
    ("CMRL","BL","outbound"): [
        (1,"Chennai Airport","MAA"),(2,"Meenambakkam","MNB"),(3,"Nanganallur Road","NGR"),
        (4,"Alandur","ALR"),(5,"St. Thomas Mount","STM"),(6,"Guindy","GDY"),
        (7,"Little Mount","LMT"),(8,"Saidapet","SDP"),(9,"Nandanam","NDN"),
        (10,"Thousand Lights","THL"),(11,"AG-DMS","AGD"),(12,"Teynampet","TYN"),
        (13,"Shastri Nagar","SHN"),(14,"Egmore","EGM"),(15,"Government Estate","GVE"),
        (16,"High Court","HCT"),(17,"Chennai Central","CHC"),(18,"Washermanpet","WSP"),
        (19,"Sir Theagaraya College","STC"),(20,"Wimco Nagar","WMN"),
    ],
    ("CMRL","GL","outbound"): [
        (1,"St. Thomas Mount","STM"),(2,"Nanganallur Road","NGR"),(3,"Alandur","ALR"),
        (4,"Ekkattuthangal","EKT"),(5,"Ashok Nagar","ASN"),(6,"Vadapalani","VDP"),
        (7,"Arumbakkam","ARB"),(8,"Koyambedu","KYB"),(9,"CMBT","CMB"),
        (10,"Pachaiyappa's College","PAC"),(11,"Nehru Park","NEP"),
    ],
    ("TNSTC","T-1","outbound"): [
        (1,"Chennai (CMBT)","CMBT"),(2,"Sriperumbudur","SPB"),(3,"Ranipet","RNP"),
        (4,"Vellore","VLR"),(5,"Krishnagiri","KRG"),(6,"Dharmapuri","DHR"),
        (7,"Salem","SLM"),(8,"Erode","ERD"),(9,"Tiruppur","TPR"),
        (10,"Coimbatore","CBE"),
    ],
    ("TNSTC","T-2","outbound"): [
        (1,"Chennai (CMBT)","CMBT"),(2,"Chengalpattu","CGP"),(3,"Villupuram","VPM"),
        (4,"Cuddalore","CDL"),(5,"Chidambaram","CDM"),(6,"Kumbakonam","KBK"),
        (7,"Thanjavur","TJR"),(8,"Trichy","TCY"),(9,"Dindigul","DDG"),
        (10,"Madurai","MDU"),
    ],
    ("TNSTC","T-7","outbound"): [
        (1,"Chennai (CMBT)","CMBT"),(2,"Chengalpattu","CGP"),(3,"Tindivanam","TDV"),
        (4,"Villupuram","VPM"),(5,"Pondicherry","PDY"),
    ],
    ("SETC","S-1","outbound"): [
        (1,"Chennai (CMBT)","CMBT"),(2,"Krishnagiri","KRG"),(3,"Hosur","HSR"),
        (4,"Electronic City","ELC"),(5,"Bangalore Majestic","BJT"),
    ],
    ("SETC","S-2","outbound"): [
        (1,"Chennai (CMBT)","CMBT"),(2,"Salem","SLM"),(3,"Erode","ERD"),
        (4,"Tiruppur","TPR"),(5,"Coimbatore","CBE"),
    ],
}

stop_count = 0
with DBCursor() as cur:
    for (provider, route_num, direction), stop_list in STOPS.items():
        rid = route_ids.get((provider, route_num, direction))
        if not rid:
            continue
        for seq, name, code in stop_list:
            cur.execute("SELECT id FROM stops WHERE route_id=%s AND stop_sequence=%s", (rid, seq))
            if not cur.fetchone():
                cur.execute(
                    """INSERT INTO stops (route_id, stop_sequence, stop_name, stop_code)
                       VALUES (%s,%s,%s,%s)""",
                    (rid, seq, name, code),
                )
                stop_count += 1

print(f"  ✓ {stop_count} stops seeded")

# ── 5. Announcements ─────────────────────────────────────────────────────────
ANNOUNCEMENTS = [
    ("MTC",  "Route 21C – Revised Timings from 1 Nov",
     "Effective November 1, 2026, Route 21C (Koyambedu–Thiruvanmiyur) departure times have been shifted forward by 15 minutes to accommodate traffic on OMR. Last service now at 20:45 hrs.",
     "schedule_change", "warning", 1),
    ("CMRL", "Blue Line – Extended Service Till 00:30 on Weekends",
     "Starting November 2026, the Blue Line (Airport–Wimco Nagar) will operate extended services until 00:30 hrs on Saturdays and Sundays. Additional trains will run at 23:15 and 00:00.",
     "new_service", "info", 1),
    ("TNSTC","Chennai–Bangalore Route T-10 – Tirupati Festival Special Services",
     "Special services to Tirupati will operate on November 14–16 during Brahmotsavam. 6 additional trips added from Chennai CMBT. Advance booking recommended.",
     "new_service", "info", 1),
    ("SETC", "Chennai–Bangalore S-1 – Partial Suspension due to Highway Maintenance",
     "SETC Route S-1 (Chennai–Bangalore) services will be partially suspended on Nov 3 between 10:00–16:00 due to National Highway 44 maintenance work. Affected passengers should check alternative routes.",
     "cancellation", "critical", 1),
    ("MTC",  "MTC Bus Route 500 Airport AC – Schedule Adjustment",
     "The 04:30 departure of Route 500 (Koyambedu–Airport) is rescheduled to 04:15 effective immediately to ensure connectivity with early morning international flights.",
     "schedule_change", "warning", 1),
    ("CMRL", "Green Line – Single-Track Operation Notice",
     "Due to track maintenance between Koyambedu and Arumbakkam, Green Line services will operate on a single track with reduced frequency on November 5 between 08:00–11:00.",
     "maintenance", "warning", 1),
]

ann_count = 0
with DBCursor() as cur:
    cur.execute("SELECT COUNT(*) AS c FROM announcements")
    existing = cur.fetchone()
    existing_count = existing["c"] if isinstance(existing, dict) else existing[0]
    if existing_count == 0:
        for provider, title, body, ann_type, severity, verified in ANNOUNCEMENTS:
            cur.execute(
                """INSERT INTO announcements
                   (provider, title, body, announcement_type, severity, is_verified)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (provider, title, body, ann_type, severity, verified),
            )
            ann_count += 1

print(f"  ✓ {ann_count} announcements seeded")

# ── 6. Mark sources as having been fetched ───────────────────────────────────
with DBCursor() as cur:
    cur.execute(
        "UPDATE transport_sources SET fetch_status='success', "
        "last_fetched_at=NOW(), last_success_at=NOW()"
    )

print()
print("=" * 55)
print("  Demo data seeded successfully!")
print(f"  Routes: {len(ROUTES)}")
print(f"  Schedules: {sched_count}")
print(f"  Stops: {stop_count}")
print(f"  Announcements: {ann_count}")
print("=" * 55)
print("  Restart the Flask app and visit /search")
print("=" * 55)
