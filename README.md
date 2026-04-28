# Fruitects-IS&DPC
[CCS 229 & CCS 231] Final Project


### How to Use:
Run the following command in the terminal to start the host control server:
```bash
python host_control.py
```

Then open the localhost URL for admin interface:
```
http://127.0.0.1:8001/admin/
```

User site available on these LAN addresses (check the broker console for the correct IP address):
```
http://<server-ip>:8001/user
```

## Secure HTTPS Hosting for Mobile Camera Access
Mobile browsers require a secure HTTPS context for camera access. To avoid warnings and get a trusted connection, run the app over HTTPS with a valid certificate or use a trusted tunnel service.

### Run with HTTPS locally
1. Create or obtain an SSL certificate and key.
2. Start the host control server with:
```bash
python host_control.py --ssl-cert cert.pem --ssl-key key.pem
```
3. Open the secure URL:
```
https://<server-ip>:8001/user
```

### Quick trusted HTTPS with ngrok
1. Install [ngrok](https://ngrok.com/).
2. Run the server normally:
```bash
python host_control.py
```
3. In another terminal, start a secure tunnel:
```bash
ngrok http 8001
```
4. Open the HTTPS URL shown by ngrok on your mobile device.

### Notes
- Allow camera access when the browser prompts you.
- The app will not work over `http://` or `file://` for mobile camera capture.
- Use a trusted HTTPS endpoint to avoid browser security warnings.
