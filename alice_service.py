import win32serviceutil
import win32service
import win32event
import requests
import json
import threading

JORDAN = "http://jordan-ip:8000"

class AliceService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AliceService"
    _svc_display_name_ = "Alice SSE Client Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def listen(self):
        with requests.get(f"{JORDAN}/sse/alice", stream=True) as r:
            for line in r.iter_lines():
                if line:
                    msg = json.loads(line.decode()[6:])
                    msg["token"] += "A"
                    msg["from"] = "alice"
                    msg["to"] = "bob"
                    requests.post(f"{JORDAN}/send", json=msg)

    def SvcStop(self):
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        threading.Thread(target=self.listen, daemon=True).start()
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(AliceService)
