const motors = document.querySelector('#motors');
const message = document.querySelector('#message');

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function render(data) {
  document.querySelector('#mount-type').textContent = data.mount_type;
  document.querySelector('#connection').textContent = 'Connected · MockDevice';
  motors.innerHTML = Object.entries(data.motors).map(([id, motor]) => `
    <article class="motor"><h3>${id}</h3><p>${motor.enabled ? 'Enabled' : 'Disabled'} · ${motor.state}</p>
    <p>Position: ${motor.current_position.toFixed(2)} · Speed: ${motor.speed.toFixed(2)}</p>
    <button data-action="move" data-motor="${id}" data-direction="POS">＋</button>
    <button data-action="move" data-motor="${id}" data-direction="NEG">−</button>
    <button data-action="stop" data-motor="${id}">STOP</button></article>`).join('');
}

async function refresh() { try { render(await api('/api/status')); } catch (error) { message.textContent = error.message; } }
document.querySelector('#transport').addEventListener('change', (event) => {
  document.querySelector('#endpoint').placeholder = event.target.value === 'wifi' ? '192.168.4.1' : 'COM5 or /dev/rfcomm0';
});
document.querySelector('#connect').addEventListener('click', async () => {
  const mode = document.querySelector('#transport').value;
  const endpoint = document.querySelector('#endpoint').value;
  const payload = mode === 'wifi' ? {mode, host: endpoint, port: 9999} : mode === 'bluetooth' ? {mode, port: endpoint, baudrate: 115200} : {mode};
  try { await api('/api/connect', {method: 'POST', body: JSON.stringify(payload)}); message.textContent = `Connected using ${mode}`; await refresh(); }
  catch (error) { message.textContent = error.message; }
});
motors.addEventListener('click', async (event) => {
  const button = event.target.closest('button'); if (!button) return;
  try {
    const path = button.dataset.action === 'stop' ? `/api/motor/${button.dataset.motor}/stop` : `/api/motor/${button.dataset.motor}/move`;
    const options = button.dataset.action === 'stop' ? {method: 'POST'} : {method: 'POST', body: JSON.stringify({direction: button.dataset.direction, speed: 1})};
    await api(path, options); await refresh();
  } catch (error) { message.textContent = error.message; }
});
document.querySelector('#emergency').addEventListener('click', async () => { try { await api('/api/stop', {method: 'POST'}); await refresh(); } catch (error) { message.textContent = error.message; } });
document.querySelector('#refresh').addEventListener('click', refresh); refresh();
