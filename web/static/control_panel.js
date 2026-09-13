const motors = document.querySelector('#motors');
const message = document.querySelector('#message');
const targetResult = document.querySelector('#target-result');
const catalogSelect = document.querySelector('#catalog-object');
const visibleOnly = document.querySelector('#visible-only');
const moonResult = document.querySelector('#moon-result');
const targetTime = document.querySelector('#target-time');
const liveClock = document.querySelector('#live-clock');
const alignmentStatus = document.querySelector('#alignment-status');
const alignSelectedButton = document.querySelector('#align-selected');
let targetTimeEdited = false;
let catalogObjects = [];

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
    const [status, connection, alignment] = await Promise.all([api('/api/status'), api('/api/connection'), api('/api/mount/position')]);
    render(status, connection);
    renderAlignment(alignment);
  } catch (error) { message.textContent = error.message; }
}

function renderAlignment(alignment) {
  alignmentStatus.textContent = alignment.aligned
    ? `Aligned · RA ${alignment.ra_deg.toFixed(4)}° · DEC ${alignment.dec_deg.toFixed(4)}° · ${alignment.source}`
    : 'Mount position is not aligned.';
  alignmentStatus.classList.toggle('aligned', alignment.aligned);
}

function applyCatalogObject(object) {
  document.querySelector('#target-name').value = `${object.id} — ${object.name}`;
  document.querySelector('#target-ra').value = object.ra_deg;
  document.querySelector('#target-dec').value = object.dec_deg;
  message.textContent = `${object.name} selected. Calculate it to check visibility.`;
}

function renderCatalog(objects) {
  catalogObjects = objects;
  catalogSelect.replaceChildren();
  catalogSelect.disabled = objects.length === 0;
  for (const object of objects) {
    const option = document.createElement('option');
    option.value = object.id;
    option.textContent = `${object.id} — ${object.name} (${object.object_type}${object.altitude_deg === undefined ? '' : `, ${object.altitude_deg.toFixed(1)}° alt`})`;
    catalogSelect.appendChild(option);
  }
  if (objects.length > 0) {
    catalogSelect.value = objects[0].id;
    applyCatalogObject(objects[0]);
  } else {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = visibleOnly.checked ? 'No objects currently visible' : 'Catalog is empty';
    catalogSelect.appendChild(option);
    message.textContent = visibleOnly.checked
      ? 'No local catalog objects are above the horizon for this time.'
      : 'No catalog objects are available.';
  }
}

async function loadCatalog() {
  try {
    const params = new URLSearchParams();
    if (visibleOnly.checked) params.set('visible', 'true');
    params.set('latitude_deg', document.querySelector('#observer-lat').value);
    params.set('longitude_deg', document.querySelector('#observer-lon').value);
    params.set('elevation_m', document.querySelector('#observer-elevation').value);
    params.set('observation_time', new Date(document.querySelector('#target-time').value).toISOString());
    const response = await api(`/api/catalog/objects?${params.toString()}`);
    renderCatalog(response.objects || []);
  } catch (error) {
    catalogObjects = [];
    catalogSelect.replaceChildren();
    catalogSelect.disabled = true;
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'Catalog unavailable';
    catalogSelect.appendChild(option);
    message.textContent = error.message;
  }
}

catalogSelect.addEventListener('change', () => {
  const selected = catalogObjects.find((object) => object.id === catalogSelect.value);
  if (selected) applyCatalogObject(selected);
});

alignSelectedButton.addEventListener('click', async () => {
  const name = document.querySelector('#target-name').value.trim();
  const ra = Number(document.querySelector('#target-ra').value);
  const dec = Number(document.querySelector('#target-dec').value);
  if (!name || !Number.isFinite(ra) || !Number.isFinite(dec)) {
    message.textContent = 'Select an object before setting mount alignment.';
    return;
  }
  try {
    const response = await api('/api/mount/align', {
      method: 'POST',
      body: JSON.stringify({name, ra_deg: ra, dec_deg: dec, source: name}),
    });
    renderAlignment(response.alignment);
    message.textContent = `Mount aligned to ${name}.`;
  } catch (error) { message.textContent = error.message; }
});

visibleOnly.addEventListener('change', loadCatalog);
['observer-lat', 'observer-lon', 'observer-elevation', 'target-time'].forEach((id) => {
  document.querySelector(`#${id}`).addEventListener('change', loadCatalog);
});
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
document.querySelector('#refresh').addEventListener('click', refresh);

function setDefaultTargetTime() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  targetTime.value = now.toISOString().slice(0, 16);
}

function formatLocalTime(date) {
  return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
}

function formatUtcTime(date) {
  return date.toISOString().slice(11, 19) + ' UTC';
}

function refreshClock() {
  const now = new Date();
  liveClock.textContent = `Local time: ${formatLocalTime(now)} · ${formatUtcTime(now)}`;
  if (!targetTimeEdited && document.activeElement !== targetTime) setDefaultTargetTime();
}

document.querySelector('#calculate-target').addEventListener('click', async () => {
  const timeInput = document.querySelector('#target-time').value;
  if (!timeInput) { message.textContent = 'Choose an observation time.'; return; }
  const payload = {
    name: document.querySelector('#target-name').value,
    ra_deg: Number(document.querySelector('#target-ra').value),
    dec_deg: Number(document.querySelector('#target-dec').value),
    latitude_deg: Number(document.querySelector('#observer-lat').value),
    longitude_deg: Number(document.querySelector('#observer-lon').value),
    elevation_m: Number(document.querySelector('#observer-elevation').value),
    observation_time: new Date(timeInput).toISOString(),
  };
  try {
    const response = await api('/api/astronomy/target', {method: 'POST', body: JSON.stringify(payload)});
    const target = response.target;
    targetResult.textContent = `${target.name} · ${target.above_horizon ? 'Above horizon' : 'Below horizon'}\n` +
      `Apparent RA: ${target.apparent_ra_deg.toFixed(4)}° · DEC: ${target.apparent_dec_deg.toFixed(4)}°\n` +
      `Altitude: ${target.altitude_deg.toFixed(2)}° · Azimuth: ${target.azimuth_deg.toFixed(2)}°`;
    message.textContent = 'Target calculated successfully.';
  } catch (error) { targetResult.textContent = 'Calculation failed.'; message.textContent = error.message; }
});

document.querySelector('#calculate-moon').addEventListener('click', async () => {
  const timeInput = document.querySelector('#target-time').value;
  if (!timeInput) { message.textContent = 'Choose an observation time.'; return; }
  const payload = {
    latitude_deg: Number(document.querySelector('#observer-lat').value),
    longitude_deg: Number(document.querySelector('#observer-lon').value),
    elevation_m: Number(document.querySelector('#observer-elevation').value),
    observation_time: new Date(timeInput).toISOString(),
  };
  try {
    const response = await api('/api/astronomy/moon', {method: 'POST', body: JSON.stringify(payload)});
    const moon = response.moon;
    moonResult.textContent = `Moon · ${moon.above_horizon ? 'Above horizon' : 'Below horizon'}\n` +
      `Apparent RA: ${moon.apparent_ra_deg.toFixed(4)}° · DEC: ${moon.apparent_dec_deg.toFixed(4)}°\n` +
      `Altitude: ${moon.altitude_deg.toFixed(2)}° · Azimuth: ${moon.azimuth_deg.toFixed(2)}° · Distance: ${Math.round(moon.distance_km).toLocaleString()} km`;
    message.textContent = 'Moon position calculated successfully.';
  } catch (error) { moonResult.textContent = 'Moon calculation failed.'; message.textContent = error.message; }
});

setDefaultTargetTime();
targetTime.addEventListener('input', () => { targetTimeEdited = true; });
refreshClock();
setInterval(refreshClock, 1000);
refresh();
loadCatalog();
