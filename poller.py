import os
import sys
import time
import requests
import json
import logging
from io import BytesIO
from pathlib import Path

logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
PRODUCT_ID = os.environ["PRODUCT_ID"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

headers = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}

def poll_and_process():
    while True:
        try:
            # Fetch pending jobs for this product
            jobs_url = f"{SUPABASE_URL}/rest/v1/jobs?select=*&status=eq.pending&job_type=eq.process_upload&product_id=eq.{PRODUCT_ID}&order=created_at.asc&limit=1"
            resp = requests.get(jobs_url, headers=headers)
            resp.raise_for_status()
            jobs = resp.json()
            if not jobs:
                time.sleep(60)
                continue
            job = jobs[0]
            job_id = job["id"]
            logging.info(f"Processing job {job_id}")

            # Mark job as processing
            patch_url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{job_id}"
            requests.patch(patch_url, headers=headers, json={"status": "processing"})

            # Download input file from 'uploads' bucket
            file_path = job["input_file_path"]
            file_name = file_path.split("/")[-1]
            download_url = f"{SUPABASE_URL}/storage/v1/object/authenticated/uploads/{file_path}"
            file_resp = requests.get(download_url, headers=headers)
            file_resp.raise_for_status()
            file_content = file_resp.content

            # Import backend processing module (dynamically to avoid early imports)
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
            # Assuming there's a process_timesheet function in the backend scripts
            # For this skeleton, we'll just dummy process and create records.
            # Replace with actual import and call.
            # from timesheet_processor import process_timesheet
            # result_data = process_timesheet(file_content, ...)

            # Dummy processing: For demonstration, create a single record
            records = [
                {
                    "title": f"Reconciliation from {file_name}",
                    "status": "reconciled:good",
                    "details": {"notes": "Auto-generated reconciliation"}
                }
            ]
            # Write records to Supabase
            records_url = f"{SUPABASE_URL}/rest/v1/records"
            for rec in records:
                rec_payload = {
                    "product_id": PRODUCT_ID,
                    "customer_id": job.get("customer_id"),
                    "title": rec["title"],
                    "status": rec["status"],
                    "details": rec.get("details", {}),
                    "source_file_path": file_path,
                    "due_date": job.get("due_date")  # optional
                }
                rec_resp = requests.post(records_url, headers=headers, json=rec_payload)
                rec_resp.raise_for_status()

            # Upload result file to 'results' bucket
            result_content = json.dumps({"records": records}).encode()
            result_file_name = f"{file_name}.json"
            upload_url = f"{SUPABASE_URL}/storage/v1/object/authenticated/results/{result_file_name}"
            upload_headers = headers.copy()
            upload_headers["Content-Type"] = "application/json"
            upload_resp = requests.post(upload_url, headers=upload_headers, data=result_content)
            upload_resp.raise_for_status()

            # Update job as completed
            finish_url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{job_id}"
            requests.patch(finish_url, headers=headers, json={
                "status": "completed",
                "output_file_path": f"results/{result_file_name}",
                "result_summary": f"Processed {len(records)} records",
                "completed_at": "now()"
            })
            logging.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logging.exception(f"Error processing job: {e}")
            # Mark job as failed if possible
            if 'job_id' in locals():
                fail_url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{job_id}"
                requests.patch(fail_url, headers=headers, json={
                    "status": "failed",
                    "result_summary": str(e),
                    "completed_at": "now()"
                })
        time.sleep(60)

if __name__ == "__main__":
    poll_and_process()
