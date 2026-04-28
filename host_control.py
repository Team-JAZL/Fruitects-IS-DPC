import os
import sys
import time
import signal
import socket
import subprocess
import base64
from contextlib import asynccontextmanager
from io import BytesIO
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from src.database import init_db, get_completed_jobs, get_queue_jobs, clear_queue_jobs, delete_completed_job, clear_completed_jobs
from src.fruits import FruitPublisher
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_HTML_PATH = os.path.join(BASE_DIR, 'admin.html')
USER_HTML_PATH = os.path.join(BASE_DIR, 'user.html')
SCRIPT_JS_PATH = os.path.join(BASE_DIR, 'script.js')
BROKER_PORT = 8000
BROKER_PROCESS = None
WORKER_PROCESS = None
HOST_POWERED = False
WORKER_POWERED = {
    'apple': False,
    'guava': False,
    'mango': False
}

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


def _is_local_client(client_host: str) -> bool:
    return client_host in ('127.0.0.1', '::1', 'localhost')


def _get_lan_ips():
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            ips.add(s.getsockname()[0])
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass

    return [ip for ip in sorted(ips) if not ip.startswith('127.')]


def _start_broker():
    global BROKER_PROCESS
    if not _is_running(BROKER_PROCESS):
        BROKER_PROCESS = _start_process([
            sys.executable,
            '-m', 'uvicorn',
            'broker:app',
            '--reload',
            '--host', '0.0.0.0',
            '--port', str(BROKER_PORT)
        ])
        time.sleep(1)


def _stop_broker():
    global BROKER_PROCESS
    _stop_process(BROKER_PROCESS)
    BROKER_PROCESS = None


def _start_worker_process():
    global WORKER_PROCESS
    if not _is_running(WORKER_PROCESS):
        WORKER_PROCESS = _start_process([sys.executable, 'subscriber_workers.py'])
        time.sleep(1)


def _stop_workers():
    global WORKER_PROCESS
    _stop_process(WORKER_PROCESS)
    WORKER_PROCESS = None


def _print_startup_urls():
    lan_ips = _get_lan_ips()
    print('=== Fruitects Host Control ===')
    if lan_ips:
        print('User site available on these LAN addresses:')
        for ip in lan_ips:
            print(f'  http://{ip}:8001/user')
    else:
        print('User site available at http://127.0.0.1:8001/user')
    print('Admin site available at http://127.0.0.1:8001/admin (local host only)')


def _is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global HOST_POWERED
    HOST_POWERED = True
    _start_broker()
    _start_worker_process()
    _print_startup_urls()
    try:
        yield
    finally:
        HOST_POWERED = False
        _stop_workers()
        _stop_broker()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.mount('/static', StaticFiles(directory=BASE_DIR), name='static')


@app.get('/')
async def home_page(request: Request):
    host = request.url.hostname or 'localhost'
    port = request.url.port or 8001
    scheme = request.url.scheme or 'http'
    user_url = f'{scheme}://{host}:{port}/user'
    admin_url = f'{scheme}://127.0.0.1:{port}/admin'
    return HTMLResponse('''
        <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>Fruitects Server</title>
                <style>
                    body {{ font-family: Inter, sans-serif; background: #f8fafc; color: #111827; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
                    .card {{ background: white; border-radius: 24px; padding: 32px; box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08); max-width: 500px; width: 100%; }}
                    a {{ color: #047857; text-decoration: none; font-weight: 700; }}
                    a.button {{ display: inline-block; margin-top: 18px; padding: 14px 20px; background: #10b981; color: white; border-radius: 16px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Fruitects Server</h1>
                    <p>Use the links below to access the hosted UI.</p>
                    <p><a class="button" href="{user_url}">Open User Site</a></p>
                    <p><a class="button" href="{admin_url}">Open Admin Console</a></p>
                    <p style="margin-top: 16px; color: #6b7280;">Admin access is restricted to the local server host.</p>
                </div>
            </body>
        </html>
    '''.format(user_url=user_url, admin_url=admin_url))


@app.get('/admin')
async def admin_page(request: Request):
    client_host = request.client.host if request.client else None
    if not client_host or not _is_local_client(client_host):
        raise HTTPException(status_code=403, detail='Admin access is restricted to the server host only.')
    return FileResponse(ADMIN_HTML_PATH)


@app.get('/user')
async def user_page():
    return FileResponse(USER_HTML_PATH)


@app.get('/script.js')
async def script_file():
    return FileResponse(SCRIPT_JS_PATH)


publisher = FruitPublisher()


@app.post('/api/publish')
async def publish_images(request: Request):
    data = await request.json()
    raw_images = data.get('images', [])
    if isinstance(raw_images, str):
        raw_images = [raw_images]

    results = []
    for raw_image in raw_images:
        if isinstance(raw_image, str) and raw_image.startswith('data:'):
            raw_image = raw_image.split(',', 1)[1]
        try:
            result = publisher.publish_base64(raw_image)
        except Exception as exc:
            result = {'status': 'error', 'message': str(exc)}
        results.append(result)

    return {'results': results}

@app.get('/api/history')
async def history():
    return {'history': get_completed_jobs()}

@app.delete('/api/history/{message_id}')
async def delete_history_item(message_id: str):
    delete_completed_job(message_id)
    return {'status': 'deleted', 'message_id': message_id}

@app.post('/api/history/clear')
async def clear_history():
    clear_completed_jobs()
    return {'status': 'cleared'}

@app.get('/api/status')
async def status():
    return {
        'host_powered': HOST_POWERED,
        'broker_powered': HOST_POWERED,
        'worker_powered': WORKER_POWERED,
        'broker_running': _is_running(BROKER_PROCESS),
        'worker_running': _is_running(WORKER_PROCESS)
    }


@app.post('/api/power')
async def power(request: Request):
    global BROKER_PROCESS, HOST_POWERED, WORKER_PROCESS
    data = await request.json()
    HOST_POWERED = bool(data.get('on'))
    if HOST_POWERED:
        if not _is_running(BROKER_PROCESS):
            _start_broker()
        _start_worker_process()
    else:
        _stop_workers()
        _stop_broker()
        BROKER_PROCESS = None
        WORKER_PROCESS = None

    return {
        'host_powered': HOST_POWERED,
        'broker_powered': HOST_POWERED,
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
        _stop_workers()

    return {
        'worker_powered': WORKER_POWERED,
        'host_powered': HOST_POWERED,
        'broker_powered': HOST_POWERED,
        'broker_running': _is_running(BROKER_PROCESS),
        'worker_running': _is_running(WORKER_PROCESS)
    }


@app.get('/api/queue')
async def queue():
    jobs = get_queue_jobs()
    worker_state = {}
    if _is_running(BROKER_PROCESS):
        try:
            response = requests.get(f'http://127.0.0.1:{BROKER_PORT}/worker-status', timeout=2)
            data = response.json()
            for worker in data.get('workers', []):
                message_id = worker.get('message_id')
                if message_id:
                    worker_state[message_id] = {
                        'status': worker.get('status', ''),
                        'progress': worker.get('progress', 0),
                        'fruit_type': worker.get('fruit_type', '')
                    }
        except Exception:
            pass

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

        fruit_type = job['topic'].split('/')[-1].capitalize() if job.get('topic') else 'Unknown'
        worker = worker_state.get(job['message_id'], {})
        progress = worker.get('progress', 0) if job['status'] != 'PENDING' else 0
        display_status = 'Pending' if job['status'] == 'PENDING' else 'In Progress'
        action_text = 'Waiting for worker assignment...' if job['status'] == 'PENDING' else f"Processing with {fruit_type} worker"

        normalized.append({
            'message_id': job['message_id'],
            'topic': job['topic'],
            'status': job['status'],
            'status_label': display_status,
            'fruit_type': fruit_type,
            'image_data': image_data,
            'progress': progress,
            'action_text': action_text,
            'position': job.get('position')
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
    server_port = 8001
    if not _is_port_available(server_port):
        print(f'Port {server_port} is already in use. Please stop the existing server or choose a different port.')
        sys.exit(1)
    uvicorn.run('host_control:app', host='0.0.0.0', port=server_port, reload=False)
