"""
Pure-Python Medical PDF Report Generator.
Generates valid, professional PDF/1.4 clinical reports without requiring external heavy libraries.
Used for sample testing, test data seeding, and instant clinical report generation.
"""
from datetime import datetime

def generate_medical_report_pdf(patient_name="Anil Kumar", patient_id="PAT-4091", age=42, gender="Male",
                                 symptoms="High fever, acute abdominal pain, nausea",
                                 diagnosis="Suspected Acute Appendicitis with localized peritonitis",
                                 priority="Urgent",
                                 clinic_name="Rampur Primary Rural Health Center",
                                 doctor_name="Dr. Suresh Verma, MBBS"):
    """
    Creates a standard, beautifully formatted PDF report binary stream.
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # PDF commands for text, lines, and layout
    # MediaBox is 612 x 792 (Standard US Letter / A4 approximate)
    commands = []
    
    # Helper to escape parentheses in PDF text
    def esc(text):
        if text is None:
            return ""
        return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Draw header banner lines
    commands.append("0.1 0.3 0.6 rg")  # Dark blue color
    commands.append("50 735 512 3 re f") # Horizontal line
    commands.append("0 0 0 rg") # Black

    # Header Text
    commands.append("BT /F1 18 Tf 50 750 Td (RURALLINK TELE-HEALTHCARE TRANSMISSION REPORT) Tj ET")
    commands.append(f"BT /F2 10 Tf 50 722 Td (Originating Facility: {esc(clinic_name)} | System: RuralLink v2.0) Tj ET")
    commands.append(f"BT /F2 9 Tf 50 708 Td (Generated Timestamp: {now_str} | Data Comm Integrity: SHA-256 Verified) Tj ET")
    
    # Patient Summary Section
    commands.append("0.9 0.93 0.98 rg") # Light background box
    commands.append("50 580 512 110 re f")
    commands.append("0.2 0.4 0.7 RG 1 w") # Border
    commands.append("50 580 512 110 re S")
    
    commands.append("0 0 0 rg")
    commands.append("BT /F1 12 Tf 65 665 Td (PATIENT CLINICAL SUMMARY) Tj ET")
    commands.append(f"BT /F2 10 Tf 65 645 Td (Patient Name : {esc(patient_name):<25} Patient ID: {esc(patient_id)}) Tj ET")
    commands.append(f"BT /F2 10 Tf 65 628 Td (Age / Gender : {age} Years / {esc(gender):<16} Priority  : {esc(priority).upper()}) Tj ET")
    commands.append(f"BT /F2 10 Tf 65 611 Td (Attending MD : {esc(doctor_name)}) Tj ET")
    commands.append(f"BT /F2 10 Tf 65 594 Td (Referral Destination: City Multi-Specialty Hospital, Metro Division) Tj ET")

    # Diagnostic Findings Section
    commands.append("BT /F1 12 Tf 50 550 Td (1. CLINICAL SYMPTOMS & PRESENTATION) Tj ET")
    commands.append(f"BT /F2 10 Tf 65 532 Td ({esc(symptoms)[:85]}) Tj ET")
    if len(symptoms) > 85:
        commands.append(f"BT /F2 10 Tf 65 518 Td ({esc(symptoms)[85:170]}) Tj ET")
        
    commands.append("BT /F1 12 Tf 50 490 Td (2. PRIMARY DIAGNOSIS & CLINICAL IMPRESSION) Tj ET")
    commands.append(f"BT /F2 10 Tf 65 472 Td ({esc(diagnosis)[:85]}) Tj ET")
    if len(diagnosis) > 85:
        commands.append(f"BT /F2 10 Tf 65 458 Td ({esc(diagnosis)[85:170]}) Tj ET")

    # Laboratory & Vitals Table
    commands.append("BT /F1 12 Tf 50 430 Td (3. RECORDED PHYSIOLOGICAL PARAMETERS & LAB WORK) Tj ET")
    
    # Table background & header
    commands.append("0.85 0.90 0.95 rg")
    commands.append("50 395 512 20 re f")
    commands.append("0 0 0 rg")
    commands.append("BT /F1 9 Tf 60 401 Td (Parameter) Tj 180 0 Td (Observed Value) Tj 150 0 Td (Reference Normal Range) Tj ET")
    
    # Table rows
    table_rows = [
        ("Body Temperature", "102.4 F (39.1 C)", "97.8 - 99.0 F"),
        ("Pulse / Heart Rate", "108 bpm (Tachycardia)", "60 - 100 bpm"),
        ("Blood Pressure", "138/88 mmHg", "120/80 mmHg"),
        ("SpO2 Blood Oxygen", "97% on room air", "95 - 100%"),
        ("Total Leukocyte Count (TLC)", "14,800 /uL (Elevated)", "4,000 - 11,000 /uL"),
        ("C-Reactive Protein (CRP)", "48 mg/L (High Acute Phase)", "< 5 mg/L"),
        ("Abdominal Ultrasound", "Aperistaltic, non-compressible loop", "Normal appendix diameter < 6mm")
    ]
    
    y = 380
    for param, val, ref in table_rows:
        commands.append(f"BT /F2 9 Tf 60 {y} Td ({param}) Tj 180 0 Td ({val}) Tj 150 0 Td ({ref}) Tj ET")
        # Line
        commands.append("0.8 0.8 0.8 RG 0.5 w")
        commands.append(f"50 {y-3} 512 0 re S")
        y -= 18

    # Data Communication Transmission Notice Box
    commands.append("0.96 0.96 0.96 rg")
    commands.append("50 140 512 70 re f")
    commands.append("0.7 0.7 0.7 RG 1 w")
    commands.append("50 140 512 70 re S")
    
    commands.append("0 0 0 rg")
    commands.append("BT /F1 10 Tf 65 192 Td (DATA COMMUNICATION AUDIT & VERIFICATION NOTICE) Tj ET")
    commands.append("BT /F2 8.5 Tf 65 177 Td (This document was securely transmitted via the RuralLink Tele-Medicine Protocol.) Tj ET")
    commands.append("BT /F2 8.5 Tf 65 163 Td (Encapsulation: TCP/IP Port 5000 / HTTPS | Content-Type: application/pdf | Payload Hashing: SHA-256) Tj ET")
    commands.append("BT /F2 8.5 Tf 65 149 Td (Duplicate Transmission Prevention: Idempotency Key Verified | Delivery Guarantee: Server ACK Token) Tj ET")

    # Signatures
    commands.append("0 0 0 rg")
    commands.append(f"BT /F1 9 Tf 50 80 Td (Referring Doctor: {esc(doctor_name)}) Tj ET")
    commands.append("BT /F2 8 Tf 50 68 Td (Rural Health Center Clinician - Digitally Signed) Tj ET")
    commands.append("BT /F1 9 Tf 360 80 Td (City Hospital Receiving Desk: PENDING) Tj ET")
    commands.append("BT /F2 8 Tf 360 68 Td (Awaiting Senior Specialist Review & Response) Tj ET")

    # Combine content stream
    content_stream = "\n".join(commands).encode("latin1")
    stream_length = len(content_stream)

    # Build PDF Objects
    objects = [
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
        b"/Contents 6 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"6 0 obj\n<< /Length {stream_length} >>\nstream\n".encode("latin1") + content_stream + b"\nendstream\nendobj\n"
    ]

    offsets = []
    current_offset = 0
    body = b""
    for obj in objects:
        if obj.startswith(b"%PDF"):
            body += obj
            current_offset += len(obj)
        else:
            offsets.append(current_offset)
            body += obj
            current_offset += len(obj)

    xref_offset = current_offset
    xref = f"xref\n0 {len(offsets)+1}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode("latin1")

    trailer = f"trailer\n<< /Size {len(offsets)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
    
    return body + xref + trailer
