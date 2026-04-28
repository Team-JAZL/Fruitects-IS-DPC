import requests, uuid, base64, os, time
import numpy as np
from PIL import Image
from io import BytesIO
import tensorflow as tf

# For devices that will capture the raw image
# The publisher classifies the fruit type before sending to the broker
class FruitPublisher:
    def __init__(self, broker_url="http://127.0.0.1:8000/publish", classifier_model_path="models/fruit_type_identifier_resnet50.keras"):
        self.broker_url = broker_url
        self.class_names = ["apple", "guava", "mango"]
        self.classifier_model = tf.keras.models.load_model(classifier_model_path)

    def _prepare_image(self, image_bytes):
        image = Image.open(BytesIO(image_bytes)).convert('RGB').resize((224, 224))
        img_array = np.array(image).astype('float32')
        return np.expand_dims(img_array, axis=0)

    def classify_fruit(self, image_bytes):
        img_tensor = self._prepare_image(image_bytes)
        predictions = self.classifier_model.predict(img_tensor)
        return self.class_names[int(np.argmax(predictions))]

    def publish_scan(self, image_path):
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        fruit_type = self.classify_fruit(image_bytes)
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return self.publish_base64(image_base64, fruit_type)

    def publish_base64(self, image_base64, fruit_type=None):
        if image_base64.startswith('data:'):
            image_base64 = image_base64.split(',', 1)[1]

        if fruit_type is None:
            image_bytes = base64.b64decode(image_base64)
            fruit_type = self.classify_fruit(image_bytes)

        fruit_type = fruit_type.lower()
        if fruit_type not in self.class_names:
            raise ValueError(f"Invalid fruit type: {fruit_type}")

        payload = {
            "message_id": f"job-{uuid.uuid4().hex[:6]}",
            "fruit_type": fruit_type,
            "image_data": image_base64
        }
        response = requests.post(self.broker_url, json=payload)
        response.raise_for_status()
        return response.json()


CONTROL_BASE = "http://127.0.0.1:8001/api"

class FruitSubscriber:
    def __init__(self, fruit_type, model, class_names, broker_url="http://127.0.0.1:8000"):
        self.fruit_type = fruit_type.lower()
        self.model = model
        self.class_names = class_names
        self.broker_url = broker_url

    def is_enabled(self):
        try:
            response = requests.get(f"{CONTROL_BASE}/worker-power/{self.fruit_type}", timeout=1)
            data = response.json()
            return bool(data.get('enabled', False))
        except Exception:
            return False

    def _update_status(self, message_id, status, progress=0):
        try:
            requests.post(
                f"{self.broker_url}/worker-status",
                json={
                    "fruit_type": self.fruit_type,
                    "message_id": message_id,
                    "status": status,
                    "progress": progress
                },
                timeout=2
            )
        except Exception:
            pass

    def _should_continue(self):
        return self.is_enabled()

    def work_once(self):
        try:
            if not self._should_continue():
                return None

            r = requests.get(f"{self.broker_url}/subscribe/fruit/{self.fruit_type}")
            job = r.json()
            if "message_id" in job:
                if not self._should_continue():
                    return None
                print(f"Processing {self.fruit_type} AI Analysis...")
                self._update_status(job['message_id'], "PROCESSING", 10)
                img_data = base64.b64decode(job['image_data'])
                img = Image.open(BytesIO(img_data)).convert('RGB').resize((224, 224))

                img_array = np.array(img)
                img_array = np.expand_dims(img_array, axis=0)

                for progress in [30, 60, 85]:
                    if not self._should_continue():
                        print(f"Worker {self.fruit_type} disabled while processing {job['message_id']}. Aborting.")
                        return None
                    time.sleep(0.3)
                    self._update_status(job['message_id'], "PROCESSING", progress)

                if not self._should_continue():
                    print(f"Worker {self.fruit_type} disabled before final predict for {job['message_id']}. Aborting.")
                    return None

                preds = self.model.predict(img_array)
                if not self._should_continue():
                    print(f"Worker {self.fruit_type} disabled after predict for {job['message_id']}. Aborting.")
                    return None

                label = self.class_names[np.argmax(preds)]

                ack_payload = {
                    "message_id": job['message_id'],
                    "status": "ACK",
                    "result": {"disease": label, "confidence": f"{float(np.max(preds))*100:.2f}%"}
                }
                requests.post(f"{self.broker_url}/ack", json=ack_payload)
                self._update_status(job['message_id'], "COMPLETED", 100)
                return f"DONE: {label}"
        except Exception as e:
            print(f"Worker Error: {e}")
        finally:
            self._update_status(None, "IDLE", 0)
        return None