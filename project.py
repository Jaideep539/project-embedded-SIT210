#!/usr/bin/env python3
"""
Single-file Flask app that embeds HTML/CSS/JS and reads MQ-3 digital pin + relay.
Save as alcohol_web_single.py and run with:
  sudo python3 alcohol_web_single.py
Then open http://<pi-ip>:5000 in your browser.
"""

from flask import Flask, jsonify, request, redirect, url_for, render_template_string
import time, sys

SIMULATION = False
try:
    from gpiozero import InputDevice, OutputDevice
except Exception as e:
    print("gpiozero import failed — running in SIMULATION mode.", e)
    SIMULATION = True

# ---------- Configuration ----------
MQ3_PIN = 17      # Digital output pin of MQ-3 (D0) -> GPIO17
RELAY_PIN = 27    # Relay control pin -> GPIO27
POLL_INTERVAL = 1  # seconds

app = Flask(__name__)

if not SIMULATION:
    try:
        mq3 = InputDevice(MQ3_PIN)
        relay = OutputDevice(RELAY_PIN, initial_value=True)  # True = unlocked by default
    except Exception as e:
        print("GPIO init failed — switching to SIMULATION mode.", e)
        SIMULATION = True

# simulation vars
mq3_state = False
relay_state = True

def read_mq3():
    if SIMULATION:
        return mq3_state
    try:
        return bool(mq3.is_active)
    except Exception:
        return False

def set_relay(on: bool):
    global relay_state
    if SIMULATION:
        relay_state = bool(on)
        return relay_state
    try:
        if on:
            relay.on()
        else:
            relay.off()
        # gpiozero's OutputDevice.is_active reflects whether output is active
        return bool(relay.is_active)
    except Exception:
        return None

# ---------- HTML (embedded) ----------
PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Alcohol Detection — Car Lock</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
:root{
  --bg:#0f1724;
  --card:#0b1220;
  --accent:#0ea5ff;
  --danger:#ef4444;
  --ok:#10b981;
  --text:#e6eef8;
}
html,body{height:100%;margin:0;padding:0}
body{
  background: linear-gradient(180deg,#041021 0%, #081426 100%);
  color: var(--text);
  font-family: "Segoe UI", Roboto, Arial, sans-serif;
  padding:20px;
}
#container{
  max-width:900px;
  margin:20px auto;
  background: rgba(255,255,255,0.02);
  border-radius:10px;
  padding:18px;
  box-shadow: 0 6px 30px rgba(0,0,0,0.6);
}
header{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:12px;
}
header h1{font-size:20px;margin:0}
#status-bubble{
  padding:8px 12px;border-radius:999px;background: rgba(255,255,255,0.04);color:var(--text);
}
#status-bubble.alarm{background: var(--danger); color:white; font-weight:700}
main{display:grid;gap:16px}
#alert-area{
  padding:18px;border-radius:8px;background: linear-gradient(90deg, rgba(239,68,68,0.12), rgba(239,68,68,0.06));
  border: 1px solid rgba(239,68,68,0.18);text-align:center;
}
#alert-area h2{ color:var(--danger); margin:8px 0; font-size:26px; }
#ok-area{ padding:14px;border-radius:8px;background: linear-gradient(90deg, rgba(16,185,129,0.08), rgba(16,185,129,0.03)); border: 1px solid rgba(16,185,129,0.12); text-align:center;}
#ok-area h2{ color:var(--ok); margin:8px 0; font-size:24px; }
.hidden{ display:none; }
#info{ display:flex; justify-content:space-between; gap:12px; color: #cfe8ff; }
#controls .btn{ padding:10px 14px; border-radius:6px; border: none; cursor:pointer; font-weight:600; margin-right:8px; }
.btn.danger{ background: var(--danger); color:white; }
.btn.ok{ background: var(--ok); color:white; }
footer{ margin-top:12px; text-align:center; opacity:0.9; font-size:13px; }
small.note{ display:block; margin-top:8px; color:#bcd; font-size:12px; }
</style>
</head>
<body>
<div id="container">
  <header>
    <h1>Alcohol Detection — Car Lock System</h1>
    <div id="status-bubble">Loading...</div>
  </header>

  <main>
    <div id="alert-area" class="hidden">
      <h2>ALCOHOL DETECTED</h2>
      <p style="font-size:18px;">Please stop the car — ignition locked.</p>
    </div>

    <div id="ok-area" class="hidden">
      <h2>All Clear</h2>
      <p>No alcohol detected. Car unlocked.</p>
    </div>

    <section id="info">
      <div>Last update: <strong id="last">--</strong></div>
      <div>Relay state: <strong id="relay">--</strong></div>
    </section>

    <section id="controls">
      <form method="post" action="/action" style="display:inline;">
        <button name="cmd" value="lock" class="btn danger">Lock (demo)</button>
      </form>
      <form method="post" action="/action" style="display:inline;">
        <button name="cmd" value="unlock" class="btn ok">Unlock (demo)</button>
      </form>

      <!-- Simulation buttons (only meaningful if server runs in SIMULATION mode) -->
      <form method="post" action="/action" style="display:inline; margin-left:10px;">
        <button name="cmd" value="simulate_on" class="btn danger">Simulate Alcohol</button>
      </form>
      <form method="post" action="/action" style="display:inline;">
        <button name="cmd" value="simulate_off" class="btn ok">Simulate Clear</button>
      </form>

      <div class="note">Hosted on Raspberry Pi — polling every <span id="poll"></span>s. Access via <code>http://{{host}}:5000</code></div>
    </section>
  </main>

  <footer>
    <small>Do not connect to real ignition for tests — use LED or lamp. Run with sudo for GPIO access.</small>
  </footer>
</div>

<script>
const pollInterval = {{ poll_interval }};
document.getElementById('poll').innerText = pollInterval;

async function fetchStatus(){
  try {
    const res = await fetch('/status');
    const obj = await res.json();
    const detected = obj.alcohol_detected;
    const relay = obj.relay_active;
    document.getElementById('last').innerText = new Date(obj.timestamp*1000).toLocaleTimeString();
    document.getElementById('relay').innerText = (relay ? 'ON / Unlocked' : 'OFF / Locked');

    const alertArea = document.getElementById('alert-area');
    const okArea = document.getElementById('ok-area');
    const statusBubble = document.getElementById('status-bubble');

    if (detected){
      alertArea.classList.remove('hidden');
      okArea.classList.add('hidden');
      statusBubble.innerText = 'ALARM';
      statusBubble.classList.add('alarm');
    } else {
      alertArea.classList.add('hidden');
      okArea.classList.remove('hidden');
      statusBubble.innerText = 'SAFE';
      statusBubble.classList.remove('alarm');
    }
  } catch (e) {
    console.error('status error', e);
  }
}

fetchStatus();
setInterval(fetchStatus, pollInterval*1000);
</script>
</body>
</html>
"""

# ---------- Routes ----------
@app.route('/')
def index():
    host = request.host.split(':')[0]
    return render_template_string(PAGE, poll_interval=POLL_INTERVAL, host=host)

@app.route('/status')
def status():
    detected = read_mq3()
    if SIMULATION:
        relay_active = relay_state
    else:
        try:
            relay_active = relay.is_active
        except Exception:
            relay_active = None
    return jsonify({
        'alcohol_detected': bool(detected),
        'relay_active': bool(relay_active),
        'timestamp': int(time.time())
    })

@app.route('/action', methods=['POST'])
def action():
    global mq3_state, relay_state
    cmd = request.form.get('cmd', '')
    if cmd == 'lock':
        set_relay(False)
    elif cmd == 'unlock':
        set_relay(True)
    elif SIMULATION and cmd == 'simulate_on':
        mq3_state = True
    elif SIMULATION and cmd == 'simulate_off':
        mq3_state = False
    return redirect(url_for('index'))

# ---------- Main ----------
if __name__ == '__main__':
    print("Starting Alcohol Detection web UI (single-file).")
    if SIMULATION:
        print("Running in SIMULATION mode (no gpiozero). Use simulate buttons on page.")
    print("Open your browser at http://<pi-ip>:5000")
    app.run(host='0.0.0.0', port=5000)
