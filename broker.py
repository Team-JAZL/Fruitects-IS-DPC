import os
from fastapi import FastAPI
import sqlite3
import time
import json
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import tensorflow as tf
import json

from src.database import(
    init_db, update_job_status, insert_job, fetch_and_lease_job, get_completed_jobs
)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

app = FastAPI()

init_db()


# Load Model 1 (Fruit Classifier) on the broker
print("Loading Model 1 (Fruit Classifier) to the Broker...")
fruit_classifier_model = tf.keras.models.load_model('models/fruit_type_identifier_resnet50.keras')
fruit_types = ["apple", "guava", "mango"]

@app.post("/publish")
async def publish(data: dict):

    img_data = base64.b64decode(data['image_data'])
    img = Image.open(BytesIO(img_data)).convert('RGB').resize((224,224))
    img_array = np.array(img).astype('float32')
    img_array = np.expand_dims(img_array, axis = 0)

    # running the model to identify the fruit
    prediction = fruit_classifier_model.predict(img_array)
    fruit_index = np.argmax(prediction)
    detected_fruit = fruit_types[fruit_index]

    # assigning the correct routing topic
    topic = f"fruit/{detected_fruit}"
    print(f"AI Broker classified the image as: {detected_fruit.upper()}")

    # save to database
    insert_job(data['message_id'], topic, data['image_data'])

    print(f"New job queued: {data['message_id']} for {topic}")
    return {"status": "queued", "detected_fruit": detected_fruit}

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


@app.get("/history")
async def get_history():
    
    return get_completed_jobs()