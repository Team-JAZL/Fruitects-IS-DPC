from src.fruits import FruitPublisher
import os

# DUMB PUBLISHER

if __name__ == "__main__":

    pub = FruitPublisher()

    folder_path = "data/sample_image/"

    test_images = []

    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                full_path = os.path.join(folder_path, filename)
                test_images.append(full_path)


    else: 
        print(f"Error: the folder does not exist.")

    for image in test_images:
        if os.path.exists(image):
            print(f"Sending raw image: {image} to the broker...")
            response = pub.publish_scan(image)
            print(f"Broker Response: {response}")
        else:
            print("Error: Image file not found.")



# This code only sends the raw image to the Broker 
# where the first fruit classification happens.
