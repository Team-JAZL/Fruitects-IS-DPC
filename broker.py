import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import time
import json
import base64
import numpy as np
from io import BytesIO
from PIL import Image

from src.database import(
    init_db, update_job_status, insert_job, fetch_and_lease_job, get_completed_jobs, get_queue_jobs
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

worker_statuses = {
    "apple": {"fruit_type": "apple", "status": "idle", "progress": 0, "message_id": None, "updated": None},
    "guava": {"fruit_type": "guava", "status": "idle", "progress": 0, "message_id": None, "updated": None},
    "mango": {"fruit_type": "mango", "status": "idle", "progress": 0, "message_id": None, "updated": None}
}

VALID_FRUIT_TYPES = {"apple", "guava", "mango"}

@app.post("/publish")
async def publish(data: dict):
    message_id = data.get('message_id')
    image_data = data.get('image_data')
    fruit_type = (data.get('fruit_type') or '').lower()

    if not message_id or not image_data or fruit_type not in VALID_FRUIT_TYPES:
        raise HTTPException(status_code=400, detail="Payload must include message_id, image_data, and a valid fruit_type")

    topic = f"fruit/{fruit_type}"
    print(f"Broker received job {message_id} for topic: {topic}")

    insert_job(message_id, topic, image_data)
    print(f"New job queued: {message_id} for {topic}")
    return {"status": "queued", "detected_fruit": fruit_type}

@app.get("/subscribe/fruit/{fruit_type}")
async def subscribe(fruit_type: str):
    topic = f"fruit/{fruit_type.lower()}"
    
    # Lease & Retry logic
    timeout_limit = time.time() - 60
    
    job = fetch_and_lease_job(topic, timeout_limit)
    
    if job:
        # Update status to prevent other workers from taking it
        update_job_status(job['message_id'], 'IN_PROGRESS')
        print(f"Job {job['message_id']} leased to {fruit_type} worker")
        return job
    
    return {"status": "no_jobs"}

@app.post("/ack")
async def acknowledge(data: dict):
    print(f"Received ACK for job: {data['message_id']}")
    update_job_status(data['message_id'], 'COMPLETED', data['result'])
    return {"status": "confirmed"}


@app.post("/worker-status")
async def update_worker_status(data: dict):
    fruit_type = data.get('fruit_type', '').lower()
    if fruit_type in worker_statuses:
        worker_statuses[fruit_type].update({
            'status': data.get('status', worker_statuses[fruit_type]['status']),
            'progress': data.get('progress', worker_statuses[fruit_type]['progress']),
            'message_id': data.get('message_id'),
            'updated': time.time()
        })
    return {"status": "worker status updated"}


@app.get("/worker-status")
async def get_worker_status():
    return {"workers": list(worker_statuses.values())}


@app.get("/queue")
async def get_queue():
    queue = get_queue_jobs()
    normalized = []
    for job in queue:
        try:
            raw_data = base64.b64decode(job['image_base64'])
            image = Image.open(BytesIO(raw_data)).convert('RGB')
            buffered = BytesIO()
            image.save(buffered, format='JPEG')
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            image_data = f"data:image/jpeg;base64,{encoded}"
        except Exception:
            image_data = None

        normalized.append({
            'message_id': job['message_id'],
            'topic': job['topic'],
            'status': job['status'],
            'image_data': image_data
        })
    return {'queue': normalized}


@app.get("/history")
async def get_history():
    
    return get_completed_jobs()