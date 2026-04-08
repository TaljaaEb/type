import win32serviceutil
import win32service
import win32event
import threading
import queue
import time
import json
from flask import Flask, request, Response, render_template_string

app = Flask(__name__)

alice_q = queue.Queue()
bob_q = queue.Queue()
log = []

HTML = """
<!doctype html>
<title>Jordan Monitor</title>
<h2>Jordan Message Monitor</h2>
<pre id="log"></pre>
<script>
const es = new EventSource("/ui/stream");
es.onmessage = e => {
  document.getElementById("log").textContent += e.data + "\\n";
};
</script>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/ui/stream")
def ui_stream():
    def gen():
        last = 0
        while True:
            while len(log) > last:
                yield f"data: {json.dumps(log[last])}\n\n"
                last += 1
            time.sleep(0.5)
    return Response(gen(), mimetype="text/event-stream")

@app.route("/send", methods=["POST"])
def send():
    msg = request.json
    log.append(msg)

    if msg["to"] == "alice":
        alice_q.put(msg)
    elif msg["to"] == "bob":
        bob_q.put(msg)

    return {"status": "ok"}

@app.route("/sse/alice")
def sse_alice():
    def gen():
        while True:
            msg = alice_q.get()
            yield f"data: {json.dumps(msg)}\n\n"
    return Response(gen(), mimetype="text/event-stream")

@app.route("/sse/bob")
def sse_bob():
    def gen():
        while True:
            msg = bob_q.get()
            yield f"data: {json.dumps(msg)}\n\n"
    return Response(gen(), mimetype="text/event-stream")

class JordanService(win32serviceutil.ServiceFramework):
    _svc_name_ = "JordanRelayService"
    _svc_display_name_ = "Jordan Relay + Monitor Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        threading.Thread(
            target=app.run,
            kwargs={"host": "0.0.0.0", "port": 8000, "threaded": True},
            daemon=True
        ).start()

        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(JordanService)
