# Fruitects: A Distributed and Smart Fruit Disease Classification System Using ResNet-50

Fruitects is a distributed fruit disease classification system that combines ResNet-50-based image classification with a publish-subscribe processing workflow. The system accepts fruit images from a browser interface, identifies the fruit type, routes the image to the correct fruit-specific worker, and returns a predicted disease label with a confidence score.

This project integrates two major computing areas:

| Area | Role in the System |
| --- | --- |
| Intelligent Systems | Uses trained TensorFlow/Keras ResNet-50 models for fruit identification and disease classification. |
| Parallel and Distributed Computing | Uses a broker-based publish-subscribe workflow to queue jobs and distribute them to parallel workers. |

## Table of Contents

- [Team Members](#team-members)
- [Project Features](#project-features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Running the Program](#running-the-program)
- [HTTPS and Mobile Camera Access](#https-and-mobile-camera-access)
- [How the System Works](#how-the-system-works)
- [Project Structure](#project-structure)
- [Repository](#repository)

## Team Members

| Name |
| --- |
| Lean Vince A. Cabales |
| Zuriel Eliazar D. Calix |
| Ma. Asherah Francine Faith S. Escrupulo |
| Jessie Loraine P. Porras |

## Project Features

- Browser-based user interface for submitting fruit images.
- Admin interface for viewing queue status, worker status, and classification history.
- ResNet-50-based fruit type identifier for apple, guava, and mango.
- Fruit-specific disease classifiers for apple, guava, and mango diseases.
- Publish-subscribe broker that routes jobs to the correct worker topic.
- Parallel subscriber workers for independent fruit disease classification.
- SQLite-backed job queue and completed-result history.
- Optional HTTPS support for mobile camera access.

## System Requirements

### Programming Language

| Requirement | Version |
| --- | --- |
| Python | 3.11.9 |

### Python Dependencies

Install all required libraries using `requirements.txt`.

| Library | Purpose |
| --- | --- |
| FastAPI | Provides the host control API and broker API. |
| Uvicorn | Runs the FastAPI ASGI servers. |
| TensorFlow | Loads and runs the Keras ResNet-50 models. |
| NumPy | Handles image tensor preparation and prediction results. |
| Pillow | Loads, converts, and resizes image files. |
| Requests | Handles HTTP communication between system components. |

### Required Model Files

The following trained model files must be present in the `models/` directory:

| Model File | Purpose |
| --- | --- |
| `fruit_type_identifier_resnet50.keras` | Identifies whether the image contains an apple, guava, or mango. |
| `apple_type_classifier_resnet50.keras` | Classifies apple disease type. |
| `guava_type_classifier_resnet50.keras` | Classifies guava disease type. |
| `mango_type_classifier_resnet50.keras` | Classifies mango disease type. |

The application also expects the following project files to be present:

```text
admin.html
user.html
script.js
data/
models/
```

The SQLite database is stored at `data/fruit_system.db`. Required database tables are initialized automatically when the application starts.

## Installation

From the project root directory, install the dependencies:

```bash
python -m pip install -r requirements.txt
```

To confirm that the installed packages are valid:

```bash
python -m pip check
```

## Running the Program

### Quick Start

Start the complete system with:

```bash
python host_control.py
```

This command starts:

| Component | Address / Behavior |
| --- | --- |
| Host control server | Runs on port `8001`. |
| Broker server | Runs on port `8000`. |
| Subscriber workers | Starts apple, guava, and mango worker threads. |

### Open the Admin Interface

Use the admin interface on the computer running the server:

```text
http://127.0.0.1:8001/admin
```

The admin interface is restricted to local host access. It is used to monitor the queue, view worker states, manage worker power, and review completed classification history.

### Open the User Interface

Use the user interface locally:

```text
http://127.0.0.1:8001/user
```

For another device on the same network, use the LAN address printed in the terminal:

```text
http://<server-ip>:8001/user
```

### Run on a Custom Host or Port

```bash
python host_control.py --host 0.0.0.0 --port 8001
```

## HTTPS and Mobile Camera Access

Most mobile browsers require HTTPS before allowing camera access. If camera capture is needed from a mobile device, run the system through a trusted HTTPS endpoint.

### Option 1: Local HTTPS Certificate

```bash
python host_control.py --ssl-cert cert.pem --ssl-key key.pem
```

Then open:

```text
https://<server-ip>:8001/user
```

### Option 2: Trusted Tunnel with ngrok

Start the Fruitects server:

```bash
python host_control.py
```

In another terminal, start the tunnel:

```bash
ngrok http 8001
```

Open the HTTPS URL generated by ngrok on the mobile device.

## How the System Works

### Intelligent Systems Components

The Intelligent Systems layer is responsible for image classification. It uses TensorFlow/Keras models trained with a ResNet-50 architecture.

| Model | Classes |
| --- | --- |
| Fruit type identifier | `apple`, `guava`, `mango` |
| Apple disease classifier | `Blotch`, `Healthy`, `Rot`, `Scab` |
| Guava disease classifier | `Anthracnose`, `Fruitfly`, `Healthy` |
| Mango disease classifier | `Alternaria`, `Anthracnose`, `Aspergillus`, `Healthy`, `Lasiodiplodia` |

Classification flow:

1. The user submits or captures a fruit image through the browser interface.
2. `FruitPublisher` prepares the image as a `224x224` RGB tensor.
3. The fruit type identifier predicts whether the image is apple, guava, or mango.
4. The image is routed to the matching fruit-specific worker.
5. The worker runs the corresponding disease classifier.
6. The predicted disease and confidence score are returned as the final result.

### Parallel and Distributed System Components

The distributed layer is responsible for job routing, queueing, worker assignment, and result storage.

| Component | Responsibility |
| --- | --- |
| `host_control.py` | Starts and manages the host API, broker process, and worker process. |
| `broker.py` | Receives jobs, stores them in the queue, leases jobs to workers, and receives acknowledgements. |
| `publisher.py` | Sends sample image jobs to the broker. |
| `src/fruits.py` | Contains publisher and subscriber logic for classification jobs. |
| `subscriber_workers.py` | Starts parallel worker threads for apple, guava, and mango topics. |
| `src/database.py` | Manages the SQLite queue, job status, history, and result payloads. |

Publish-subscribe workflow:

1. The publisher sends an image job to the broker.
2. The broker assigns the job to a topic such as `fruit/apple`, `fruit/guava`, or `fruit/mango`.
3. The job is saved in SQLite with a `PENDING` status.
4. Fruit-specific subscriber workers continuously poll their assigned topic.
5. When a worker receives a job, the broker marks it as `IN_PROGRESS`.
6. The worker processes the image using its disease classifier.
7. The worker sends an acknowledgement with the prediction result.
8. The broker saves the completed result for the admin interface and history view.

This design separates AI model inference from distributed job management. As a result, workers can process fruit-specific jobs independently while the broker maintains a centralized queue and result history.

## Project Structure

```text
Fruitects-IS-DPC/
|-- admin.html
|-- user.html
|-- script.js
|-- host_control.py
|-- broker.py
|-- publisher.py
|-- subscriber_workers.py
|-- requirements.txt
|-- README.md
|-- data/
|   |-- fruit_system.db
|   `-- sample_image/
|-- models/
|   |-- fruit_type_identifier_resnet50.keras
|   |-- apple_type_classifier_resnet50.keras
|   |-- guava_type_classifier_resnet50.keras
|   `-- mango_type_classifier_resnet50.keras
`-- src/
    |-- database.py
    `-- fruits.py
```

## Repository

Repository link: `https://github.com/Team-JAZL/Fruitects-IS-DPC`
