import os
from datetime import datetime, timedelta
from app import create_app
from models import db, User, Report, HospitalResponse, TransmissionLog, IdempotencyRecord
from utils.security import compute_sha256, generate_ack_token
from utils.sample_pdf import generate_medical_report_pdf

def seed_database():
    app = create_app()
    with app.app_context():
        print("Initializing database tables...")
        db.create_all()

        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        # Check if users already exist
        if User.query.first():
            print("Database already contains data. Skipping re-seed.")
            return

        print("Seeding doctor user accounts...")
        # 1. Rural Doctors
        dr_suresh = User(
            user_id='usr_rural_suresh',
            name='Dr. Suresh Verma, MBBS',
            email='rural.doctor@rurallink.org',
            role='rural_doctor',
            organization='Rampur Primary Health Center',
            license_number='RMC-2018-9844'
        )
        dr_suresh.set_password('RuralDoctor@123')

        dr_shikha = User(
            user_id='usr_rural_shikha',
            name='Dr. Shikha Patel, MBBS',
            email='shikha.clinic@rurallink.org',
            role='rural_doctor',
            organization='Sundargarh Community Health Center',
            license_number='OR-2020-5621'
        )
        dr_shikha.set_password('RuralDoctor@123')

        # 2. City Hospital Doctors
        dr_ananya = User(
            user_id='usr_hosp_ananya',
            name='Dr. Ananya Roy, MD (Internal Medicine)',
            email='hospital.doctor@rurallink.org',
            role='hospital_doctor',
            organization='Metro Multi-Specialty City Hospital',
            license_number='NMC-2012-34891'
        )
        dr_ananya.set_password('HospitalDoctor@123')

        dr_arjun = User(
            user_id='usr_hosp_arjun',
            name='Dr. Arjun Malhotra, MS, MCh (Trauma & Surgery)',
            email='arjun.surgery@rurallink.org',
            role='hospital_doctor',
            organization='Metro Multi-Specialty City Hospital',
            license_number='NMC-2015-11042'
        )
        dr_arjun.set_password('HospitalDoctor@123')

        db.session.add_all([dr_suresh, dr_shikha, dr_ananya, dr_arjun])
        db.session.commit()
        print("Users created successfully.")

        print("Seeding clinical medical reports and PDF attachments...")
        
        # Report 1: Acute Appendicitis (Critical - Received)
        rpt1_id = 'RPT-20261102-APPEN1'
        pdf1_data = generate_medical_report_pdf(
            patient_name='Ramesh Yadav',
            patient_id='PAT-7821',
            age=34,
            gender='Male',
            symptoms='Severe right lower quadrant abdominal pain for 18h, vomiting, fever 102F, rebound tenderness at McBurney point',
            diagnosis='Acute Appendicitis with localized peritonitis - impending perforation risk',
            priority='Critical Emergency',
            clinic_name='Rampur Primary Health Center',
            doctor_name='Dr. Suresh Verma, MBBS'
        )
        pdf1_filename = f"{rpt1_id}_Appendicitis_Workup.pdf"
        pdf1_path = os.path.join(upload_dir, pdf1_filename)
        with open(pdf1_path, 'wb') as f:
            f.write(pdf1_data)
        pdf1_hash = compute_sha256(pdf1_data)
        ack1 = generate_ack_token(rpt1_id)

        rpt1 = Report(
            report_id=rpt1_id,
            patient_id='PAT-7821',
            patient_name='Ramesh Yadav',
            age=34,
            gender='Male',
            symptoms='Severe right lower quadrant abdominal pain for 18h, vomiting, fever 102F, rebound tenderness at McBurney point',
            diagnosis='Acute Appendicitis with localized peritonitis - impending perforation risk',
            priority='Critical Emergency',
            additional_notes='Patient started on IV fluids and broad-spectrum antibiotics (Ceftriaxone + Metronidazole). Awaiting surgical bed reservation at City Hospital.',
            pdf_filename=pdf1_filename,
            pdf_path=pdf1_path,
            pdf_size_bytes=len(pdf1_data),
            sha256_checksum=pdf1_hash,
            status='Received',
            idempotency_key='IDEMP-RAMESH-20261102-001',
            ack_token=ack1,
            created_by_user_id=dr_suresh.user_id,
            clinic_name='Rampur Primary Health Center',
            created_at=datetime.utcnow() - timedelta(minutes=45),
            received_at=datetime.utcnow() - timedelta(minutes=44)
        )

        # Report 2: Acute Coronary Syndrome (Under Review)
        rpt2_id = 'RPT-20261102-CARDI2'
        pdf2_data = generate_medical_report_pdf(
            patient_name='Savita Devi',
            patient_id='PAT-5510',
            age=58,
            gender='Female',
            symptoms='Retrosternal squeezing chest pain radiating to left jaw and shoulder, diaphoresis, shortness of breath on sitting, BP 165/100',
            diagnosis='Acute Coronary Syndrome (NSTEMI vs Unstable Angina) with Hypertensive Urgency',
            priority='Critical Emergency',
            clinic_name='Rampur Primary Health Center',
            doctor_name='Dr. Suresh Verma, MBBS'
        )
        pdf2_filename = f"{rpt2_id}_Cardiac_Evaluation.pdf"
        pdf2_path = os.path.join(upload_dir, pdf2_filename)
        with open(pdf2_path, 'wb') as f:
            f.write(pdf2_data)
        pdf2_hash = compute_sha256(pdf2_data)
        ack2 = generate_ack_token(rpt2_id)

        rpt2 = Report(
            report_id=rpt2_id,
            patient_id='PAT-5510',
            patient_name='Savita Devi',
            age=58,
            gender='Female',
            symptoms='Retrosternal squeezing chest pain radiating to left jaw and shoulder, diaphoresis, shortness of breath on sitting, BP 165/100',
            diagnosis='Acute Coronary Syndrome (NSTEMI vs Unstable Angina) with Hypertensive Urgency',
            priority='Critical Emergency',
            additional_notes='Administered Aspirin 325mg chewed, Clopidogrel 300mg, and sublingual Sorbitrate. Oxygen via nasal cannula @ 4 L/min.',
            pdf_filename=pdf2_filename,
            pdf_path=pdf2_path,
            pdf_size_bytes=len(pdf2_data),
            sha256_checksum=pdf2_hash,
            status='Under Review',
            idempotency_key='IDEMP-SAVITA-20261102-002',
            ack_token=ack2,
            created_by_user_id=dr_suresh.user_id,
            clinic_name='Rampur Primary Health Center',
            created_at=datetime.utcnow() - timedelta(hours=2, minutes=15),
            received_at=datetime.utcnow() - timedelta(hours=2, minutes=14)
        )

        # Report 3: Fracture Dislocation (Responded)
        rpt3_id = 'RPT-20261102-FRACT3'
        pdf3_data = generate_medical_report_pdf(
            patient_name='Pooja Sharma',
            patient_id='PAT-9204',
            age=22,
            gender='Female',
            symptoms='Skid from motorcycle, intense pain and dinner-fork deformity over right wrist, distal pulses palpable, capillary refill < 2s',
            diagnosis='Closed Displaced Colles Fracture of Right Distal Radius',
            priority='Normal',
            clinic_name='Sundargarh Community Health Center',
            doctor_name='Dr. Shikha Patel, MBBS'
        )
        pdf3_filename = f"{rpt3_id}_Orthopedic_Xray_Report.pdf"
        pdf3_path = os.path.join(upload_dir, pdf3_filename)
        with open(pdf3_path, 'wb') as f:
            f.write(pdf3_data)
        pdf3_hash = compute_sha256(pdf3_data)
        ack3 = generate_ack_token(rpt3_id)

        rpt3 = Report(
            report_id=rpt3_id,
            patient_id='PAT-9204',
            patient_name='Pooja Sharma',
            age=22,
            gender='Female',
            symptoms='Skid from motorcycle, intense pain and dinner-fork deformity over right wrist, distal pulses palpable, capillary refill < 2s',
            diagnosis='Closed Displaced Colles Fracture of Right Distal Radius',
            priority='Normal',
            additional_notes='Temporary volar slab applied. X-Ray image reviewed. Neurovascular status intact.',
            pdf_filename=pdf3_filename,
            pdf_path=pdf3_path,
            pdf_size_bytes=len(pdf3_data),
            sha256_checksum=pdf3_hash,
            status='Responded',
            idempotency_key='IDEMP-POOJA-20261102-003',
            ack_token=ack3,
            created_by_user_id=dr_shikha.user_id,
            clinic_name='Sundargarh Community Health Center',
            created_at=datetime.utcnow() - timedelta(hours=5),
            received_at=datetime.utcnow() - timedelta(hours=4, minutes=58)
        )

        # Hospital Response for Report 3
        res3 = HospitalResponse(
            report_id=rpt3_id,
            doctor_id=dr_arjun.user_id,
            doctor_name=dr_arjun.name,
            hospital_name='Metro Multi-Specialty City Hospital',
            department='Orthopedics & Trauma Surgery',
            clinical_assessment='Satisfactory alignment post initial splinting. Fracture line is extra-articular with 12 degree dorsal tilt.',
            prescription_advice='Keep below-elbow plaster slab elevated in sling. Analgesia: Paracetamol 650mg TDS + Tramadol 50mg PRN. Advise ice packs 20min Q4H. Schedule elective OPD checkup on Thursday for possible cast completion.',
            urgency_directive='Proceed with Local Care (Splint + Elevation)'
        )

        db.session.add_all([rpt1, rpt2, rpt3, res3])
        db.session.commit()

        # Seed Transmission Logs to demonstrate Data Communication concepts
        print("Seeding transmission logs for packet analysis demonstration...")
        logs = [
            TransmissionLog(
                report_id=rpt1_id,
                event_type='REPORT_SUBMITTED',
                http_method='POST',
                endpoint='/api/reports',
                status_code=201,
                round_trip_ms=138.4,
                client_ip='192.168.1.102',
                payload_checksum=pdf1_hash,
                ack_token=ack1,
                details=f"Packet size: {len(pdf1_data)} bytes. Idempotency verified: IDEMP-RAMESH-20261102-001. TCP ACK sent.",
                created_at=datetime.utcnow() - timedelta(minutes=44)
            ),
            TransmissionLog(
                report_id=rpt2_id,
                event_type='REPORT_SUBMITTED',
                http_method='POST',
                endpoint='/api/reports',
                status_code=201,
                round_trip_ms=164.2,
                client_ip='192.168.1.102',
                payload_checksum=pdf2_hash,
                ack_token=ack2,
                details=f"Packet size: {len(pdf2_data)} bytes. TCP stream established. Received at hospital gateway.",
                created_at=datetime.utcnow() - timedelta(hours=2, minutes=14)
            ),
            TransmissionLog(
                report_id=rpt2_id,
                event_type='STATUS_TRANSITION',
                http_method='PATCH',
                endpoint=f"/api/reports/{rpt2_id}/status",
                status_code=200,
                round_trip_ms=42.1,
                client_ip='10.0.4.15',
                details="Status transitioned to 'Under Review' by Dr. Ananya Roy (Cardiology)",
                created_at=datetime.utcnow() - timedelta(hours=1, minutes=30)
            ),
            TransmissionLog(
                report_id=rpt3_id,
                event_type='REPORT_SUBMITTED',
                http_method='POST',
                endpoint='/api/reports',
                status_code=201,
                round_trip_ms=121.8,
                client_ip='192.168.2.45',
                payload_checksum=pdf3_hash,
                ack_token=ack3,
                details=f"Packet size: {len(pdf3_data)} bytes. Verified and stored.",
                created_at=datetime.utcnow() - timedelta(hours=4, minutes=58)
            ),
            TransmissionLog(
                report_id=rpt3_id,
                event_type='HOSPITAL_RESPONSE_DISPATCHED',
                http_method='POST',
                endpoint=f"/api/reports/{rpt3_id}/response",
                status_code=201,
                round_trip_ms=78.5,
                client_ip='10.0.4.18',
                details="Orthopedic clinical advice packet dispatched back to Sundargarh clinic.",
                created_at=datetime.utcnow() - timedelta(hours=3, minutes=10)
            )
        ]
        db.session.add_all(logs)

        # Seed Idempotency records
        idemp1 = IdempotencyRecord(
            idempotency_key='IDEMP-RAMESH-20261102-001',
            report_id=rpt1_id,
            request_hash=compute_sha256('IDEMP-RAMESH-20261102-001'),
            response_status=201,
            response_body='{"report_id": "' + rpt1_id + '"}'
        )
        db.session.add(idemp1)
        db.session.commit()

        print("Database seeded successfully with demo doctors, reports, and transmission logs!")

if __name__ == '__main__':
    seed_database()
