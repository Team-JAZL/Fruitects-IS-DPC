from src.fruits import FruitPublisher
import os

# DUMB PUBLISHER

if __name__ == "__main__":

    pub = FruitPublisher()
    test_image = "data/sample_image/mango2.jpg" 
    
    if os.path.exists(test_image):
        print(f"Sending raw image: {test_image} to the broker...")
        response = pub.publish_scan(test_image)
        print(f"Broker Response: {response}")
    else:
        print("Error: Image file not found.")



# This code only sends the raw image to the Broker 
# where the first fruit classification happens.
