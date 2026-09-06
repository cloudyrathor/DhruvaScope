const motors = document.querySelector('#motors');
const message = document.querySelector('#message');

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function render(data, connection) {
  document.querySelector('#mount-type').textContent = data.mount_type || 'Equatorial mount';
  const deviceName = connection.mode === 'mock' ? 'MockDevice' : `${connection.mode} · ${connection.device}`;
  const connectionLabel = document.querySelector('#connection');
  connectionLabel.textContent = `Connected · ${deviceName}`;
  connectionLabel.style.color = connection.mode === 'mock' ? '#fbbf24' : '#86efac';
  motors.innerHTML = Object.entries(data.motors).map(([id, motor]) => {
    const available = motor.available !== false;
    const disabled = available ? '' : ' disabled';
    return `
    <article class="motor${available ? '' : ' unavailable'}"><h3>${id}</h3><p>${available ? (motor.enabled ? 'Enabled' : 'Disabled') : 'Not wired'} · ${motor.state}</p>
    <p>Position: ${Number(motor.current_position ?? 0).toFixed(2)} · Speed: ${Number(motor.speed ?? 0).toFixed(2)}</p>
    <label>Speed <output data-speed-output="${id}">${Number(motor.speed || 0.03).toFixed(3)}</output> deg/s
      <input type="range" min="0.005" max="0.1" step="0.005" value="${Number(motor.speed) || 0.03}" data-speed="${id}"${disabled}>
    </label>
    <button data-action="move" data-motor="${id}" data-direction="POS"${disabled}>＋</button>
    <button data-action="move" data-motor="${id}" data-direction="NEG"${disabled}>−</button>
    <button data-action="stop" data-motor="${id}"${disabled}>STOP</button></article>`;
  }).join('');
}

async function refresh() {
  try {
    const [status, connection] = await Promise.all([api('/api/status'), api('/api/connection')]);
    render(status, connection);
  } catch (error) { message.textContent = error.message; }
}
document.querySelector('#transport').addEventListener('change', (event) => {
  const endpoint = document.querySelector('#endpoint');
  const connectionLabel = document.querySelector('#connection');
  endpoint.placeholder = event.target.value === 'wifi' ? '192.168.4.1' : 'COM5 or /dev/rfcomm0';
  if (event.target.value === 'wifi' && !endpoint.value) endpoint.value = '192.168.4.1';
  if (event.target.value === 'wifi') {
    connectionLabel.textContent = 'Wi-Fi selected · click Connect';
    connectionLabel.style.color = '#fbbf24';
    message.textContent = 'Connect this computer to DhruvaScope-ESP32-Test first.';
  }
});
document.querySelector('#connect').addEventListener('click', async () => {
  const mode = document.querySelector('#transport').value;
  const endpoint = document.querySelector('#endpoint').value.trim();
  if (mode === 'wifi' && !endpoint) { message.textContent = 'Enter the ESP32 Wi-Fi address (default AP: 192.168.4.1)'; return; }
  const payload = mode === 'wifi' ? {mode, host: endpoint, port: 9999} : mode === 'bluetooth' ? {mode, port: endpoint, baudrate: 115200} : {mode};
  const connectButton = document.querySelector('#connect');
  const connectionLabel = document.querySelector('#connection');
  connectButton.disabled = true;
  connectionLabel.textContent = `Connecting · ${mode}`;
  try { await api('/api/connect', {method: 'POST', body: JSON.stringify(payload)}); message.textContent = `Connected using ${mode}`; await refresh(); }
  catch (error) {
    connectionLabel.textContent = 'Not connected · MockDevice active';
    connectionLabel.style.color = '#f87171';
    message.textContent = mode === 'wifi' && /timed out|timeout|failed/i.test(error.message)
      ? `${error.message}. Connect the Flask computer to the ESP32 network and verify address 192.168.4.1.`
      : error.message;
  } finally { connectButton.disabled = false; }
});
motors.addEventListener('click', async (event) => {
  const button = event.target.closest('button'); if (!button) return;
  try {
    const path = button.dataset.action === 'stop' ? `/api/motor/${button.dataset.motor}/stop` : `/api/motor/${button.dataset.motor}/move`;
    const speedInput = button.closest('.motor')?.querySelector(`[data-speed="${button.dataset.motor}"]`);
    const speed = speedInput ? Number(speedInput.value) : 0.03;
    const options = button.dataset.action === 'stop' ? {method: 'POST'} : {method: 'POST', body: JSON.stringify({direction: button.dataset.direction, speed})};
    await api(path, options); await refresh();
  } catch (error) { message.textContent = error.message; }
});
motors.addEventListener('input', (event) => {
  const input = event.target.closest('input[data-speed]'); if (!input) return;
  const output = motors.querySelector(`[data-speed-output="${input.dataset.speed}"]`);
  if (output) output.value = Number(input.value).toFixed(1);
  if (output) output.textContent = Number(input.value).toFixed(1);
});
document.querySelector('#emergency').addEventListener('click', async () => { try { await api('/api/stop', {method: 'POST'}); await refresh(); } catch (error) { message.textContent = error.message; } });
document.querySelector('#refresh').addEventListener('click', refresh); refresh();
