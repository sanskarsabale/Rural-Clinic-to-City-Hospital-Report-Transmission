# RuralLink — Rural Clinic to City Hospital Report Transmission System

> **Second Year B.Tech Information Technology — Data Communication Academic Project**  
> **Project Team:** Sanskar Sabale · Vaishnavi Potdar · Jayesh Sutar

---

## Project Overview

**RuralLink** is a complete, full-stack web application that bridges rural Primary Health Centers with tertiary-care City Hospitals through reliable digital medical report transmission.

It is built as a live demonstration of **Data Communication** concepts including:
- Client-Server Architecture
- HTTP/HTTPS REST APIs over TCP/IP
- Server Acknowledgement (ACK) tokens
- Duplicate request prevention via Idempotency-Keys
- SHA-256 cryptographic data integrity verification
- Exponential backoff retry for reliable transport
- Store-and-Forward Offline Queue (browser localStorage)
- Packet analysis using Wireshark

---

## Technology Stack

| Layer | Technology |
| :--- | :--- |
| Frontend | HTML5, CSS3, Vanilla JavaScript (ES6+) |
| Backend | Python 3.11, Flask 3.0, Flask-SQLAlchemy |
| Authentication | JWT (HMAC-SHA256), Flask Sessions |
| Database | SQLite (development) / PostgreSQL (production) |
| File Handling | Multipart/form-data, PDF binary streaming, SHA-256 |
| Deployment | Render.com (Free Tier), Gunicorn WSGI |

---

## Application Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│   PORTAL A: Rural Clinic    │ HTTP/   │  PORTAL B: City Hospital     │
│   /clinic                   │ TCP/IP  │  /hospital                   │
│                             │ ──────► │                              │
│  • Dr. Suresh Verma, MBBS   │         │  • Dr. Ananya Roy, MD        │
│  • Create patient reports   │ ◄────── │  • Review incoming referrals │
│  • Upload PDF attachments   │  ACK +  │  • Download & verify PDFs    │
│  • Offline queue & retry    │ Response│  • Send clinical advice back │
└─────────────────────────────┘         └──────────────────────────────┘
                         │                          │
                         ▼                          ▼
              ┌─────────────────────────────────────────┐
              │  Flask REST API Backend (Port 5000)      │
              │  SQLite / PostgreSQL Database             │
              │  Secure PDF file storage (/uploads)       │
              │  JWT Auth · Idempotency · SHA-256 ACK    │
              └─────────────────────────────────────────┘
```

---

## Project Structure

```
dc project/
├── app.py                          # Application factory & page routes
├── config.py                       # Dev/Production configuration
├── models.py                       # SQLAlchemy database models
├── seed_data.py                    # Demo data seeder
├── requirements.txt                # Python dependencies
├── run.py                          # Simple entry point
├── render.yaml                     # Render.com deployment config
├── .env.example                    # Environment variable template
├── RuralLink.postman_collection.json  # Postman API test collection
├── WIRESHARK_GUIDE.md              # Detailed packet analysis guide
│
├── routes/
│   ├── auth.py                     # /api/auth/* endpoints
│   ├── reports.py                  # /api/reports/* endpoints
│   └── network_lab.py              # /api/network-lab/* endpoints
│
├── utils/
│   ├── auth.py                     # JWT helpers, decorators
│   ├── security.py                 # SHA-256, file validation
│   └── sample_pdf.py               # Pure-Python PDF generator
│
├── templates/
│   ├── base.html                   # Shared navbar, footer, scripts
│   ├── index.html                  # Architecture overview & API docs
│   ├── login.html                  # Doctor authentication page
│   ├── clinic.html                 # Portal A: Rural Clinic dashboard
│   ├── hospital.html               # Portal B: City Hospital dashboard
│   └── network_lab.html            # Data Comm Lab & Wireshark guide
│
└── static/
    ├── css/style.css               # Global responsive stylesheet
    └── js/
        ├── api.js                  # REST API client + retry logic
        ├── clinic.js               # Rural Clinic portal logic
        ├── hospital.js             # City Hospital portal logic
        ├── offline_queue.js        # Store & Forward offline manager
        └── network_inspector.js    # Packet dissector & trace viewer
```

---

## Demo Login Credentials

| Role | Email | Password | Organization |
| :--- | :--- | :--- | :--- |
| **Rural Doctor** | `rural.doctor@rurallink.org` | `RuralDoctor@123` | Rampur Primary Health Center |
| **Rural Doctor** | `shikha.clinic@rurallink.org` | `RuralDoctor@123` | Sundargarh Community Health Center |
| **Hospital Doctor** | `hospital.doctor@rurallink.org` | `HospitalDoctor@123` | Metro Multi-Specialty City Hospital |
| **Hospital Doctor** | `arjun.surgery@rurallink.org` | `HospitalDoctor@123` | Metro Multi-Specialty City Hospital |

---

## Local Development Setup

### Prerequisites
- Python 3.10+
- pip

### Steps

```bash
# 1. Clone or navigate to the project directory
cd "d:\dc project"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed the database with demo data
python seed_data.py

# 4. Start the Flask development server
python app.py
```

The server will start at: **http://127.0.0.1:5000**

| Portal | URL |
| :--- | :--- |
| Architecture Overview | http://127.0.0.1:5000/ |
| Rural Clinic (Portal A) | http://127.0.0.1:5000/clinic |
| City Hospital (Portal B) | http://127.0.0.1:5000/hospital |
| Data Comm Lab & Wireshark | http://127.0.0.1:5000/network-lab |

---

## REST API Endpoints

| Method | Endpoint | Purpose | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Doctor login, returns JWT | No |
| `POST` | `/api/auth/logout` | Invalidate session | Optional |
| `GET` | `/api/auth/me` | Current user profile | Yes |
| `GET` | `/api/reports` | Fetch role-scoped reports | Yes |
| `POST` | `/api/reports` | Create & transmit report + PDF | Yes (Rural) |
| `GET` | `/api/reports/<id>` | Report details & audit logs | Yes |
| `PATCH` | `/api/reports/<id>/status` | Update report lifecycle status | Yes |
| `POST` | `/api/reports/<id>/response` | Hospital doctor sends advice | Yes (Hospital) |
| `POST` | `/api/reports/<id>/ack` | Explicit server ACK request | Yes |
| `POST` | `/api/reports/<id>/upload` | Upload/replace PDF attachment | Yes |
| `GET` | `/api/reports/<id>/download` | Secure PDF streaming download | Yes |
| `GET` | `/api/reports/<id>/network-trace` | Full packet transmission trace | Yes |
| `GET` | `/api/network-lab/stats` | Live Data Comm metrics | No |
| `POST` | `/api/network-lab/simulate-fault` | Network fault simulator | No |
| `GET` | `/api/network-lab/wireshark-filters` | Wireshark filter cheat sheet | No |
| `GET` | `/api/network-lab/export-postman` | Download Postman collection | No |

### HTTP Status Codes Used

| Code | Meaning |
| :--- | :--- |
| `200 OK` | Successful retrieval, update, or auth |
| `201 Created` | Report created, PDF uploaded, response sent |
| `302 Found` | Redirect (page navigation) |
| `400 Bad Request` | Missing/invalid fields or bad file |
| `401 Unauthorized` | No or invalid authentication token |
| `403 Forbidden` | Authenticated but wrong role/scope |
| `404 Not Found` | Report or resource does not exist |
| `409 Conflict` | Duplicate Idempotency-Key rejected |
| `413 Payload Too Large` | PDF exceeds 16 MB limit |
| `503 Service Unavailable` | Simulated packet drop |
| `504 Gateway Timeout` | Simulated link timeout |
| `500 Internal Server Error` | Unexpected server error |

---

## Data Communication Concepts Demonstrated

### 1. TCP/IP Protocol Stack
Every HTTP request from the browser to Flask traverses all 5 layers of the Internet Protocol Suite. The Network Lab page provides an interactive OSI dissection viewer.

### 2. Server Acknowledgement (ACK) Token
When a report is accepted, the server returns a cryptographic `ack_token`. The client must wait for this before marking a transmission as delivered — mirroring TCP's ACK mechanism.

### 3. Idempotency-Key (Duplicate Prevention)
Every report submission includes a unique UUID in the `Idempotency-Key` HTTP header. If the network drops after the server stores the report but before the ACK reaches the client, the client will retry. The server detects the duplicate key and returns `HTTP 409 Conflict` — preventing double-entry.

### 4. SHA-256 Data Integrity Verification
Each PDF attachment is hashed with SHA-256. The server returns this hash in the ACK packet. The City Hospital portal displays a "Data Integrity: SHA-256 Verified" badge on every received report.

### 5. Exponential Backoff Retry
When a transmission fails (503, 504, or socket error), the client waits:
- Attempt 1: `1200ms + random jitter`
- Attempt 2: `2400ms + jitter`
- Attempt 3: `4800ms + jitter`
- Attempt 4: `9600ms + jitter`

All retries use the **same Idempotency-Key** to prevent duplicates.

### 6. Store-and-Forward Offline Queue
If all retries fail (e.g., rural area has no connectivity), the report is stored in browser `localStorage`. When `window.addEventListener('online')` fires, the queue manager automatically flushes and transmits the stored reports.

---

## Wireshark Packet Analysis (Quick Reference)

1. **Start Wireshark** → select `Npcap Loopback Adapter` (for local test)
2. Apply any filter below in the green bar:

| Goal | Display Filter |
| :--- | :--- |
| All RuralLink traffic | `http && tcp.port == 5000` |
| TCP handshake | `tcp.flags.syn == 1 && tcp.port == 5000` |
| Report submissions | `http.request.method == "POST" && http.request.uri contains "/api/reports"` |
| Server ACK (201) | `http.response.code == 201` |
| Duplicate rejection (409) | `http.response.code == 409` |

> See [WIRESHARK_GUIDE.md](WIRESHARK_GUIDE.md) for the complete guide with viva Q&A.

---

## Online Deployment (Render.com)

1. Push the project to a GitHub repository.
2. Create a new **Web Service** on [render.com](https://render.com).
3. Connect your GitHub repo.
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn "app:create_app()"`
6. Add environment variables from `.env.example`.
7. Create a free **PostgreSQL** database and link it via `DATABASE_URL`.
8. Deploy — Render auto-detects the `render.yaml` configuration.

---

## Testing with Postman

1. Import `RuralLink.postman_collection.json` into Postman.
2. Set the `base_url` variable to `http://127.0.0.1:5000` (local) or your Render URL.
3. Run the **"Login as Rural Doctor"** request first — it auto-saves the JWT token.
4. Run the collection in sequence to demonstrate the full end-to-end data communication workflow.

---

*Academic Data Communication Project — Second Year B.Tech Information Technology*  
*Team: Sanskar Sabale · Vaishnavi Potdar · Jayesh Sutar*
