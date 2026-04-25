from fruits import FruitPublisher
import os

model_1 = 'models/fruit_type_identifier_resnet50.keras'

if __name__ == "__main__":
    pub = FruitPublisher(model_1)
    test_image = "Sample_Image/Disease_Mango.png" 
    
    if os.path.exists(test_image):
        print(f"Scanning: {test_image}")
        response = pub.publish_scan(test_image)
        print(f"Broker Response: {response}")
    else:
        print("Error: Image file not found.")