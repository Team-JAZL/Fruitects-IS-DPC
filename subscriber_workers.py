import tensorflow as tf
import time
import threading
from src.fruits import FruitSubscriber

# Load Specific Models
m_apple = tf.keras.models.load_model('models/apple_type_classifier_resnet50.keras')
m_guava = tf.keras.models.load_model('models/guava_type_classifier_resnet50.keras')
m_mango = tf.keras.models.load_model('models/mango_type_classifier_resnet50.keras')

workers = [
    FruitSubscriber("apple", m_apple, ["Blotch", "Healthy", "Rot", "Scab"]),
    FruitSubscriber("guava", m_guava, ["Anthracnose", "Fruitfly", "Healthy"]),
    FruitSubscriber("mango", m_mango, ["Alternaria", "Anthracnose", "Aspergillus", "Healthy", "Lasiodiplodia"])
]

def run_worker(worker):

    print(f"{worker.fruit_type.capitalize()} worker is now pulling for jobs...")
    
    while True:
        if worker.is_enabled():
            res = worker.work_once()
            if res: 
                print(res)
        else:
            time.sleep(1)
            continue

        time.sleep(2)
print("Starting all subscriber workers in parallel...")

threads = []

for worker in workers:

    worker_thread = threading.Thread(
        target = run_worker, 
        args = (worker, )
    )

    worker_thread.start()
    threads.append(worker_thread)

for worker_thread in threads:
    worker_thread.join()