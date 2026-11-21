# RuralLink – Data Communication & Wireshark Packet Analysis Guide

**Academic Project:** Rural Clinic to City Hospital Report Transmission System  
**Course:** Data Communication (Second Year B.Tech Information Technology)  
**Project Team:** Sanskar Sabale, Vaishnavi Potdar, Jayesh Sutar  
**Technology Stack:** Python, Flask, REST APIs, TCP/IP, HTTP/1.1, JSON, PDF Binary Streaming  

---

## 1. Overview & Data Communication Theoretical Foundation

RuralLink operates as a distributed **Client-Server Architecture** connecting remote healthcare edge nodes (Rural Primary Health Centers) to centralized core tertiary care systems (City Hospitals).

Every clinical referral transmitted across this system traverses the **5-Layer Internet Protocol Suite (TCP/IP Stack)**:

```
+-----------------------------------------------------------------------------------------+
| [Layer 5] Application Layer  : HTTP/1.1 REST APIs, JSON Payloads, Base64/PDF Streaming |
+-----------------------------------------------------------------------------------------+
| [Layer 4] Transport Layer    : TCP (Transmission Control Protocol) — Port 5000         |
|                                Guaranteed Delivery, Flow Control, 3-Way Handshake       |
+-----------------------------------------------------------------------------------------+
| [Layer 3] Network Layer      : IPv4 / IPv6 (Logical Routing, Packets, TTL, IP Headers) |
+-----------------------------------------------------------------------------------------+
| [Layer 2] Data Link Layer    : Ethernet II / 802.11 Wi-Fi (MAC Framing, Error Checking) |
+-----------------------------------------------------------------------------------------+
| [Layer 1] Physical Layer     : Twisted Pair Copper (Cat6), Fiber Optics, Radio Waves    |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Setting Up Wireshark for Packet Capture

### Step 2.1: Local Machine Capture (Single Computer)
1. Install **Wireshark** (ensure the **Npcap** packet capture driver is installed with "Support loopback traffic" checked).
2. Open Wireshark.
3. In the interface list, double-click on **"Adapter for loopback traffic capture"** (or `Npcap Loopback Adapter`).
4. RuralLink Flask server runs by default on port `5000` (`127.0.0.1:5000`).

### Step 2.2: Two-Machine Demonstration (Real LAN Simulation)
1. Connect both laptops (Rural Clinic laptop and City Hospital laptop) to the same Wi-Fi network or local Ethernet switch.
2. Find the IP address of the server machine using `ipconfig` (e.g., `192.168.1.15`).
3. Run `python app.py` on the server machine.
4. On the client laptop, open the browser to `http://192.168.1.15:5000`.
5. In Wireshark on either machine, select your **Wi-Fi** or **Ethernet** network adapter.

---

## 3. Wireshark Display Filters Cheat Sheet

Paste these filters into the green display filter bar at the top of Wireshark:

| Demonstration Goal | Wireshark Display Filter | What to Observe in Viva |
| :--- | :--- | :--- |
| **All RuralLink Traffic** | `http && tcp.port == 5000` | Shows all REST API request-response pairs between Clinic and Server. |
| **TCP 3-Way Handshake** | `tcp.flags.syn == 1 && tcp.port == 5000` | Shows initial `[SYN]` from client and `[SYN, ACK]` from server establishing reliable socket. |
| **Report Submission (POST)** | `http.request.method == "POST" && http.request.uri contains "/api/reports"` | Captures the multipart packet containing patient clinical JSON + PDF binary payload. |
| **Server ACK (201 Created)** | `http.response.code == 201` | Shows the server acknowledgement packet containing the `ack_token` and `sha256_checksum`. |
| **Duplicate Prevention (409)**| `http.response.code == 409` | Captures server rejection packet when duplicate `Idempotency-Key` is re-sent. |
| **Hospital Response Dispatch**| `http.request.uri contains "/response"` | Captures consulting doctor's advice transmitted back to the rural clinic. |
| **PDF File Download Stream** | `http.request.uri contains "/download"` | Shows HTTP GET returning `Content-Type: application/pdf` with private cache headers. |

---

## 4. Step-by-Step Live Demonstration Scenarios

### Scenario 1: Capturing the TCP 3-Way Handshake
1. In Wireshark, apply filter:
   ```
   tcp.port == 5000
   ```
2. Open a browser and visit `http://127.0.0.1:5000/login`.
3. Observe the sequence in Wireshark:
   - **Packet 1 (SYN):** Rural Clinic sends `[SYN] Seq=0` requesting connection.
   - **Packet 2 (SYN-ACK):** Server replies `[SYN, ACK] Seq=0 Ack=1` agreeing to connect.
   - **Packet 3 (ACK):** Rural Clinic acknowledges `[ACK] Seq=1 Ack=1`. Connection is now **ESTABLISHED**.

### Scenario 2: Capturing Report Transmission & PDF Upload
1. In Wireshark, apply filter:
   ```
   http.request.method == "POST" && http.request.uri == "/api/reports"
   ```
2. In the **Rural Clinic Portal**, fill out the patient form (e.g., patient "Ramesh Yadav", diagnosis "Acute Appendicitis"), check "Automatically Generate Clinical Lab Report PDF", and click **"Send Report to City Hospital"**.
3. In Wireshark, select the captured `POST /api/reports` frame:
   - Expand **Hypertext Transfer Protocol**.
   - Note the headers:
     - `Authorization: Bearer <JWT>`
     - `Idempotency-Key: IDEMP-<UUID>`
     - `Content-Type: multipart/form-data; boundary=...`
   - Expand the **MIME Multipart Media Encapsulation**:
     - View the clinical fields (`patient_id`, `symptoms`, `diagnosis`).
     - View the binary PDF attachment stream (`%PDF-1.4 ...`).

### Scenario 3: Inspecting Server Acknowledgement (ACK)
1. Clear filter and apply:
   ```
   http.response.code == 201
   ```
2. Inspect the HTTP payload returned by the server:
   ```json
   {
     "success": true,
     "server_acknowledgement": {
       "status": "ACK_ACCEPTED",
       "report_id": "RPT-20261102-APPEN1",
       "ack_token": "ACK-7fa19c28e40192a837192bc",
       "sha256_checksum": "4b9a89c2018274aef...",
       "delivery_guarantee": "AT_LEAST_ONCE_IDEMPOTENT",
       "rtt_ms": 138.4
     }
   }
   ```
3. **Data Communication Concept:** This proves that the client does **not** assume a packet is delivered just because it was sent. The transmission is only certified once the server generates and returns the cryptographic ACK token!

### Scenario 4: Demonstrating Duplicate Request Prevention (Idempotency)
1. In Wireshark, apply filter:
   ```
   http.response.code == 409
   ```
2. Open **Postman** (or use the built-in Network Lab tool).
3. Send the same report creation request twice with the exact same `Idempotency-Key: IDEMP-RAMESH-20261102-001`.
4. Observe the response: **HTTP 409 Conflict**. The database refuses to create a duplicate record, protecting patient safety and channel integrity!

---

## 5. Packet Dissection Reference (Viva Model Diagram)

```
===================================================================================
                RURALLINK WIRESHARK CAPTURED PACKET BREAKDOWN
===================================================================================

[1. ETHERNET II FRAME]
  Destination MAC : 00:0c:29:8f:a1:3b (Router / Hospital Core)
  Source MAC      : 00:1a:2b:3c:4d:5e (Rural Clinic Edge Gateway)
  Type            : IPv4 (0x0800)

[2. INTERNET PROTOCOL (IPv4)]
  Version         : 4
  Header Length   : 20 Bytes
  Total Length    : 1420 Bytes
  Identification  : 0x3d91 (15761)
  Flags           : 0x4000 (Don't Fragment - DF)
  Time to Live    : 64 hops
  Protocol        : TCP (6)
  Source IP       : 192.168.1.102 (Rural Clinic)
  Destination IP  : 127.0.0.1 (City Hospital Server)

[3. TRANSMISSION CONTROL PROTOCOL (TCP)]
  Source Port     : 54192 (Client Ephemeral Port)
  Destination Port: 5000 (Flask HTTP REST Service)
  Sequence Number : 1 (Relative)
  Ack Number      : 1 (Relative)
  Flags           : [PSH, ACK] (Push data immediately to application layer)
  Window Size     : 65535 Bytes

[4. APPLICATION LAYER (HTTP/1.1)]
  Request Method  : POST
  Request URI     : /api/reports
  Request Version : HTTP/1.1
  User-Agent      : Mozilla/5.0 ...
  Authorization   : Bearer eyJhbGciOiJIUzI1Ni...
  Idempotency-Key : IDEMP-7b92-411a-8291
  Content-Type    : multipart/form-data; boundary=----WebKitFormBoundary...
  Content-Length  : 4621 Bytes

[5. APPLICATION PAYLOAD (JSON + PDF)]
  --boundary
  Content-Disposition: form-data; name="patient_name"
  Ramesh Yadav
  --boundary
  Content-Disposition: form-data; name="file"; filename="Report.pdf"
  Content-Type: application/pdf
  %PDF-1.4 ... [Binary PDF Stream] ... %%EOF
===================================================================================
```

---

## 6. High-Probability Viva Questions & Model Answers

### Q1: Why does RuralLink use TCP instead of UDP for medical report transmission?
**Answer:** TCP is a connection-oriented, reliable transport protocol that guarantees ordered, error-free delivery via acknowledgements (ACKs) and sequence numbers. Since medical reports contain vital patient diagnoses and binary PDF attachments, packet loss or bit errors could lead to incorrect medical decisions. UDP does not guarantee delivery and is unsuitable for critical clinical data.

### Q2: How does RuralLink prevent duplicate report transmission if the network drops right after the client sends data?
**Answer:** RuralLink implements the **Idempotency-Key** pattern. Each report submission includes a unique UUID in the HTTP `Idempotency-Key` header. If a network drop prevents the client from receiving the ACK, the client will retry using the exponential backoff algorithm. When the server receives the retry with an existing key, it recognizes the duplicate, rejects the second write, and returns the cached ACK with HTTP 409 Conflict or cached confirmation.

### Q3: What is the purpose of the SHA-256 Checksum in your system?
**Answer:** In Data Communication, ensuring **data integrity** means verifying that data was not altered or corrupted during transit. When the PDF report is packaged, the sender computes its SHA-256 cryptographic hash. The server re-computes the hash upon receipt. If the hashes match, the server certifies that the file arrived with 100% bit-level integrity.

### Q4: How does the Exponential Backoff Retry mechanism work?
**Answer:** When a connection fails (e.g., HTTP 503 or socket timeout), retrying immediately can flood an already congested network. Exponential backoff increases the delay exponentially before each subsequent attempt:
$$\text{Delay} = \text{Base Delay} \times 2^{\text{attempt}} + \text{Random Jitter}$$
(e.g., 1s, 2s, 4s, 8s). The random jitter prevents all edge nodes from synchronizing and causing a retry storm.

### Q5: How does the Store-and-Forward Offline Queue help in a rural environment?
**Answer:** Rural Primary Health Centers often suffer from intermittent internet connectivity. If connectivity drops, the frontend catches the transmission error and stores the referral in browser `localStorage` with status `Queued`. Once the browser detects network restoration via `window.addEventListener('online')`, the queue manager automatically flushes and transmits the pending reports.

---
*Created for the Data Communication Academic Project Evaluation — Second Year B.Tech IT.*
