import tensorflow as tf
import time
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

print("Subscriber workers are now polling for jobs...")
while True:
    for worker in workers:
        res = worker.work_once()
        if res: print(res)
    time.sleep(2)