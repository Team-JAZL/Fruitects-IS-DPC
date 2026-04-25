import requests, uuid, base64, os
import tensorflow as tf
import numpy as np

from io import BytesIO
from PIL import Image
# Idagdag ang import na ito
from tensorflow.keras.applications.resnet50 import preprocess_input

class FruitPublisher:
    def __init__(self, model_path, broker_url="http://127.0.0.1:8000/publish"):
        self.broker_url = broker_url
        self.type_model = tf.keras.models.load_model(model_path)
        self.fruit_types = ["apple", "guava", "mango"] 

    def _identify_fruit(self, image_path):
        img = Image.open(image_path).convert('RGB').resize((224, 224))
        img_array = np.array(img).astype('float32')
        img_array = np.expand_dims(img_array, axis=0)
        
        prediction = self.type_model.predict(img_array)
        fruit_index = np.argmax(prediction)
        
        # Just for debugging purposes, you can print the raw prediction scores optionally can be removed later
        print(f"DEBUG Model 1 Scores: {prediction}") 
        
        return self.fruit_types[fruit_index]

    def publish_scan(self, image_path):
        detected_fruit = self._identify_fruit(image_path)
        topic = f"fruit/{detected_fruit}"
        print(f"SYSTEM DETECTED: {detected_fruit.upper()}")
        
        with open(image_path, "rb") as f:
            img_str = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "message_id": f"job-{uuid.uuid4().hex[:6]}",
            "topic": topic,
            "image_data": img_str
        }
        return requests.post(self.broker_url, json=payload).json()

class FruitSubscriber:
    def __init__(self, fruit_type, model, class_names, broker_url="http://127.0.0.1:8000"):
        self.fruit_type = fruit_type.lower()
        self.model = model
        self.class_names = class_names
        self.broker_url = broker_url

    def work_once(self):
        try:
            r = requests.get(f"{self.broker_url}/subscribe/fruit/{self.fruit_type}")
            job = r.json()
            if "message_id" in job:
                print(f"Processing {self.fruit_type} AI Analysis...")
                img_data = base64.b64decode(job['image_data'])
                img = Image.open(BytesIO(img_data)).convert('RGB').resize((224, 224))
                
                img_array = np.array(img)
                img_array = np.expand_dims(img_array, axis=0)
            
                #img_array = preprocess_input(img_array)
                
                preds = self.model.predict(img_array)
                label = self.class_names[np.argmax(preds)]
                
                ack_payload = {
                    "message_id": job['message_id'],
                    "status": "ACK",
                    "result": {"disease": label, "confidence": f"{float(np.max(preds))*100:.2f}%"}
                }
                requests.post(f"{self.broker_url}/ack", json=ack_payload)
                return f"DONE: {label}"
        except: pass
        return None