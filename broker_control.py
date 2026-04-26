import os
import sys
import time
import signal
import subprocess
import base64
from io import BytesIO
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from src.database import init_db, get_queue_jobs, clear_queue_jobs
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_HTML_PATH = os.path.join(BASE_DIR, 'admin.html')
BROKER_PORT = 8000
BROKER_PROCESS = None
WORKER_PROCESS = None
BROKER_POWERED = False
WORKER_POWERED = {
    'apple': False,
    'guava': False,
    'mango': False
}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

init_db()


def _is_running(process):
    return process is not None and process.poll() is None


def _start_process(command):
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    return subprocess.Popen(
        command,
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _stop_process(process):
    if process is None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass


@app.get('/')
async def admin_page():
    return FileResponse(ADMIN_HTML_PATH)


@app.get('/api/status')
async def status():
    return {
        'broker_powered': BROKER_POWERED,
        'worker_powered': WORKER_POWERED,
        'broker_running': _is_running(BROKER_PROCESS),
        'worker_running': _is_running(WORKER_PROCESS)
    }


@app.post('/api/power')
async def power(request: Request):
    global BROKER_PROCESS, BROKER_POWERED, WORKER_PROCESS
    data = await request.json()
    BROKER_POWERED = bool(data.get('on'))
    if BROKER_POWERED:
        if not _is_running(BROKER_PROCESS):
            BROKER_PROCESS = _start_process([sys.executable, '-m', 'uvicorn', 'broker:app', '--reload', '--port', str(BROKER_PORT)])
            time.sleep(1)
        if any(WORKER_POWERED.values()) and not _is_running(WORKER_PROCESS):
            WORKER_PROCESS = _start_process([sys.executable, 'subscriber_workers.py'])
            time.sleep(1)
    else:
        _stop_process(BROKER_PROCESS)
        BROKER_PROCESS = None
        # stop workers when broker is off too
        _stop_process(WORKER_PROCESS)
        WORKER_PROCESS = None
        
    return {
        'broker_powered': BROKER_POWERED,
        'worker_powered': WORKER_POWERED,
        'broker_running': _is_running(BROKER_PROCESS),
        'worker_running': _is_running(WORKER_PROCESS)
    }


@app.get('/api/worker-power')
async def worker_power_status():
    return {'worker_powered': WORKER_POWERED}


@app.get('/api/worker-power/{fruit_type}')
async def get_worker_power(fruit_type: str):
    fruit_type = fruit_type.lower()
    return {'fruit_type': fruit_type, 'enabled': WORKER_POWERED.get(fruit_type, False)}


@app.post('/api/worker-power/{fruit_type}')
async def set_worker_power(fruit_type: str, request: Request):
    global WORKER_PROCESS
    data = await request.json()
    fruit_type = fruit_type.lower()
    if fruit_type in WORKER_POWERED:
        WORKER_POWERED[fruit_type] = bool(data.get('on'))

    if any(WORKER_POWERED.values()) and _is_running(BROKER_PROCESS) and not _is_running(WORKER_PROCESS):
        WORKER_PROCESS = _start_process([sys.executable, 'subscriber_workers.py'])
        time.sleep(1)

    if not any(WORKER_POWERED.values()):
        _stop_process(WORKER_PROCESS)
        WORKER_PROCESS = None

    return {
        'worker_powered': WORKER_POWERED,
        'broker_powered': BROKER_POWERED,
        'broker_running': _is_running(BROKER_PROCESS),
        'worker_running': _is_running(WORKER_PROCESS)
    }


@app.get('/api/queue')
async def queue():
    jobs = get_queue_jobs()
    normalized = []
    for job in jobs:
        image_data = None
        try:
            raw_data = base64.b64decode(job['image_base64'])
            image = Image.open(BytesIO(raw_data)).convert('RGB')
            buffered = BytesIO()
            image.save(buffered, format='JPEG')
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            image_data = f'data:image/jpeg;base64,{encoded}'
        except Exception:
            image_data = None
        normalized.append({
            'message_id': job['message_id'],
            'topic': job['topic'],
            'status': job['status'],
            'image_data': image_data
        })
    return {'queue': normalized}


@app.post('/api/clear-queue')
async def clear_queue():
    clear_queue_jobs()
    return {'status': 'cleared'}


@app.get('/api/workers')
async def workers():
    if _is_running(BROKER_PROCESS):
        try:
            response = requests.get(f'http://127.0.0.1:{BROKER_PORT}/worker-status', timeout=2)
            return response.json()
        except Exception:
            pass
    return {'workers': []}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('broker_control:app', host='127.0.0.1', port=8001, reload=False)
