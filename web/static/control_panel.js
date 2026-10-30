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
const gotoResult = document.querySelector('#goto-result');
const cameraPreview = document.querySelector('#camera-preview');
const cameraStatus = document.querySelector('#camera-status');
const visualTrackerEnabled = document.querySelector('#visual-tracker-enabled');
const visualReferenceObject = document.querySelector('#visual-reference-object');
const saveVisualReference = document.querySelector('#save-visual-reference');
const resetVisualReferences = document.querySelector('#reset-visual-references');
const visualReferenceStatus = document.querySelector('#visual-reference-status');
const visualTargetObject = document.querySelector('#visual-target-object');
const prepareVisualTarget = document.querySelector('#prepare-visual-target');
const visualTargetResult = document.querySelector('#visual-target-result');
const calibrationEnabled = document.querySelector('#calibration-enabled');
const resetCalibration = document.querySelector('#reset-calibration');
const calibrationStatus = document.querySelector('#calibration-status');
const trackerEmergencyStop = document.querySelector('#tracker-emergency-stop');
let targetTimeEdited = false;
let catalogObjects = [];
let visualTrackerState = {references: [], target: null};
let calibrationState = {enabled: false, points: []};
const visualNudgeSpeed = 0.03;
const focusNudgeSpeed = 0.05;
const nudgeStartedAt = {};
const focusStepMs = 100;

function showSection(sectionName) {
  document.querySelectorAll('.nav-item').forEach((item) => {
    const active = item.dataset.section === sectionName;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  document.querySelectorAll('.workspace-section').forEach((section) => {
    section.classList.toggle('active-section', section.id === `section-${sectionName}`);
  });
}

document.querySelectorAll('.nav-item').forEach((item) => {
  item.addEventListener('click', () => showSection(item.dataset.section));
});

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

function renderVisualReferenceObjects(objects) {
  visualReferenceObject.replaceChildren();
  visualTargetObject.replaceChildren();
  for (const object of objects) {
    for (const select of [visualReferenceObject, visualTargetObject]) {
      const option = document.createElement('option');
      option.value = object.id;
      option.textContent = `${object.id} — ${object.name}`;
      select.appendChild(option);
    }
  }
  saveVisualReference.disabled = !visualTrackerEnabled.checked || objects.length === 0;
  prepareVisualTarget.disabled = !visualTrackerEnabled.checked || objects.length === 0;
}

function renderVisualTracker(status) {
  visualTrackerState = status;
  visualTrackerEnabled.checked = status.enabled;
  const modeLabel = visualTrackerEnabled.closest('.tracker-switch')?.querySelector('strong');
  if (modeLabel) modeLabel.textContent = status.enabled ? 'ON' : 'OFF';
  saveVisualReference.disabled = !status.enabled || catalogObjects.length === 0;
  prepareVisualTarget.disabled = !status.enabled || catalogObjects.length === 0;
  renderVisualReferences(status.references);
  if (status.target && typeof status.target === 'object') {
    visualTargetResult.textContent = `${status.target.name}\nRA delta: ${Number(status.target.ra_delta_deg).toFixed(4)}° · DEC delta: ${Number(status.target.dec_delta_deg).toFixed(4)}°\nReady for the next confirmed movement.`;
  }
  renderTrackerSteps();
}

function renderVisualReferences(references) {
  visualReferenceStatus.replaceChildren();
  if (!references.length) {
    visualReferenceStatus.textContent = 'No visual references saved.';
    return;
  }
  const count = document.createElement('span');
  count.className = 'reference-count';
  count.textContent = `${references.length}/3 references saved`;
  visualReferenceStatus.appendChild(count);
  for (const reference of references) {
    const badge = document.createElement('span');
    badge.className = 'reference-badge';
    const check = document.createElement('span');
    check.className = 'reference-check';
    check.setAttribute('aria-hidden', 'true');
    check.textContent = '✓';
    const name = document.createElement('span');
    name.textContent = reference.name;
    badge.append(check, name);
    visualReferenceStatus.appendChild(badge);
  }
}

function renderCalibration(status) {
  calibrationState = status;
  calibrationEnabled.checked = status.enabled;
  resetCalibration.disabled = !status.enabled;
  const scales = status.scale_deg_per_second || {};
  const raScale = scales.RA == null ? 'pending' : Number(scales.RA).toFixed(5) + '°/s';
  const decScale = scales.DEC == null ? 'pending' : Number(scales.DEC).toFixed(5) + '°/s';
  calibrationStatus.textContent = status.enabled
    ? status.points.length + ' reference point(s). RA scale: ' + raScale + ' · DEC scale: ' + decScale
    : 'Calibration is off. One reference is enough for basic positioning.';
  renderTrackerSteps();
}

function renderTrackerSteps() {
  const references = visualTrackerState.references?.length || 0;
  const hasTarget = Boolean(visualTrackerState.target && typeof visualTrackerState.target === 'object');
  const activeStep = !references ? 'reference' : calibrationState.enabled && calibrationState.points.length < 3 ? 'calibration' : hasTarget ? 'target' : 'target';
  document.querySelectorAll('[data-tracker-step]').forEach((step) => {
    const name = step.dataset.trackerStep;
    const complete = (name === 'reference' && references > 0) || (name === 'calibration' && calibrationState.points.length >= 3) || (name === 'target' && hasTarget);
    step.classList.toggle('complete', complete);
    step.classList.toggle('active', name === activeStep && !complete);
  });
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
    renderVisualReferenceObjects(response.objects || []);
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

visualTrackerEnabled.addEventListener('change', async () => {
  try {
    const response = await api('/api/visual-tracker/mode', {
      method: 'POST', body: JSON.stringify({enabled: visualTrackerEnabled.checked}),
    });
    if (response.visual_tracker) renderVisualTracker(response.visual_tracker);
    message.textContent = visualTrackerEnabled.checked
      ? 'Visual Tracker enabled. Use the telescope view or optional camera preview with the arrow pad.'
      : 'Visual Tracker disabled; RA and DEC manual movement stopped.';
  } catch (error) {
    visualTrackerEnabled.checked = !visualTrackerEnabled.checked;
    message.textContent = error.message;
  }
});

saveVisualReference.addEventListener('click', async () => {
  const selected = catalogObjects.find((object) => object.id === visualReferenceObject.value);
  if (!selected) { message.textContent = 'Select a reference object first.'; return; }
  try {
    const response = await api(calibrationEnabled.checked ? '/api/calibration/reference' : '/api/visual-tracker/reference', {
      method: 'POST',
      body: JSON.stringify({name: `${selected.id} — ${selected.name}`, ra_deg: selected.ra_deg, dec_deg: selected.dec_deg}),
    });
    if (response.visual_tracker) renderVisualTracker(response.visual_tracker);
    if (response.calibration) renderCalibration(response.calibration);
    renderAlignment({aligned: true, ra_deg: selected.ra_deg, dec_deg: selected.dec_deg, source: selected.name});
    message.textContent = `${selected.name} saved as a visual reference.`;
  } catch (error) { message.textContent = error.message; }
});

resetVisualReferences.addEventListener('click', async () => {
  try {
    const response = await api('/api/visual-tracker/references/reset', {method: 'POST'});
    renderVisualTracker(response.visual_tracker);
    renderAlignment(response.alignment);
    visualTargetResult.textContent = 'No target prepared.';
    message.textContent = 'Visual reference points and mount alignment were reset.';
  } catch (error) { message.textContent = error.message; }
});

calibrationEnabled.addEventListener('change', async () => {
  try {
    const response = await api('/api/calibration/mode', {method: 'POST', body: JSON.stringify({enabled: calibrationEnabled.checked})});
    renderCalibration(response.calibration);
    message.textContent = calibrationEnabled.checked ? 'Calibration enabled. Record the first reference, move, then record the next.' : 'Calibration disabled.';
  } catch (error) { calibrationEnabled.checked = !calibrationEnabled.checked; message.textContent = error.message; }
});

resetCalibration.addEventListener('click', async () => {
  try {
    const response = await api('/api/calibration/reset', {method: 'POST'});
    renderCalibration(response.calibration);
    message.textContent = 'Calibration references reset.';
  } catch (error) { message.textContent = error.message; }
});

prepareVisualTarget.addEventListener('click', async () => {
  const selected = catalogObjects.find((object) => object.id === visualTargetObject.value);
  if (!selected) { message.textContent = 'Select a target object first.'; return; }
  try {
    const response = await api('/api/visual-tracker/target', {
      method: 'POST',
      body: JSON.stringify({name: `${selected.id} — ${selected.name}`, ra_deg: selected.ra_deg, dec_deg: selected.dec_deg}),
    });
    const target = response.target;
    visualTargetResult.textContent = `${target.name}\nRA delta: ${target.ra_delta_deg.toFixed(4)}° · DEC delta: ${target.dec_delta_deg.toFixed(4)}°\nReady for the next confirmed movement.`;
    message.textContent = `${selected.name} prepared. No motors were moved.`;
  } catch (error) { visualTargetResult.textContent = 'Target preparation failed.'; message.textContent = error.message; }
});

async function nudgeStart(button) {
  if (!visualTrackerEnabled.checked) { message.textContent = 'Enable Visual Tracker mode first.'; return; }
  try {
    const axis = button.dataset.axis;
    nudgeStartedAt[axis] = performance.now();
    const speed = axis === 'FOCUS' ? focusNudgeSpeed : visualNudgeSpeed;
    await api(`/api/motor/${axis}/move`, {
      method: 'POST', body: JSON.stringify({direction: button.dataset.direction, speed}),
    });
  } catch (error) { message.textContent = error.message; }
}

async function nudgeStop(axis) {
  if (!['RA', 'DEC', 'FOCUS'].includes(axis)) return;
  try {
    await api(`/api/motor/${axis}/stop`, {method: 'POST'});
    if (axis !== 'FOCUS' && calibrationEnabled.checked && nudgeStartedAt[axis] != null) {
      const button = document.querySelector('.nudge[data-axis="' + axis + '"]');
      await api('/api/calibration/motion', {method: 'POST', body: JSON.stringify({
        axis, direction: button.dataset.direction,
        duration_ms: Math.min(300000, Math.max(0, performance.now() - nudgeStartedAt[axis])),
      })});
      delete nudgeStartedAt[axis];
    }
    if (nudgeStartedAt[axis] != null) delete nudgeStartedAt[axis];
  } catch (error) { message.textContent = error.message; }
}

document.querySelectorAll('.nudge').forEach((button) => {
  if (button.dataset.action === 'stop') {
    button.addEventListener('click', () => {
      const axes = (button.dataset.axes || 'RA,DEC').split(',').map((axis) => axis.trim()).filter(Boolean);
      axes.forEach((axis) => nudgeStop(axis));
    });
    return;
  }
  button.addEventListener('pointerdown', (event) => { event.preventDefault(); button.setPointerCapture(event.pointerId); nudgeStart(button); });
  button.addEventListener('pointerup', () => nudgeStop(button.dataset.axis));
  button.addEventListener('pointercancel', () => nudgeStop(button.dataset.axis));
  button.addEventListener('pointerleave', () => nudgeStop(button.dataset.axis));
});

const focusStepSize = document.querySelector('#focus-step-size');
const focusSpeed = document.querySelector('#focus-speed');
const focusStatus = document.querySelector('#focus-status');
let focusTotal = 0;

focusSpeed.addEventListener('input', () => { document.querySelector('#focus-speed-output').textContent = focusSpeed.value; });

document.querySelectorAll('.pulse-step[data-direction]').forEach((button) => {
  button.addEventListener('click', async () => {
    if (!visualTrackerEnabled.checked) { message.textContent = 'Enable Visual Tracker mode first.'; return; }
    const steps = Number(focusStepSize.value);
    const direction = button.dataset.direction;
    try {
      await api('/api/motor/FOCUS/step', {method: 'POST', body: JSON.stringify({direction, steps, speed: Number(focusSpeed.value)})});
      focusTotal += direction === 'POS' ? steps : -steps;
      focusStatus.textContent = `Command sent: ${steps} step(s) ${direction === 'POS' ? 'out' : 'in'}. Net this session: ${focusTotal} steps.`;
    } catch (error) { focusStatus.textContent = `Focuser error: ${error.message}`; message.textContent = `Focuser: ${error.message}`; }
  });
});

document.querySelector('#focus-stop').addEventListener('click', async () => {
  try { await api('/api/motor/FOCUS/stop', {method: 'POST'}); focusStatus.textContent = 'Focuser stopped.'; }
  catch (error) { message.textContent = `Focuser: ${error.message}`; }
});

trackerEmergencyStop.addEventListener('click', async () => {
  nudgeStop('RA'); nudgeStop('DEC');
  try { await api('/api/motor/FOCUS/stop', {method: 'POST'}); } catch (error) { /* FOCUS may be unavailable */ }
});

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

document.querySelector('#plan-goto').addEventListener('click', async () => {
  try {
    const response = await api('/api/goto/plan', {
      method: 'POST',
      body: JSON.stringify({
        name: document.querySelector('#target-name').value,
        ra_deg: Number(document.querySelector('#target-ra').value),
        dec_deg: Number(document.querySelector('#target-dec').value),
      }),
    });
    const plan = response.plan;
    gotoResult.textContent = `${plan.name}\nRA delta: ${plan.ra_delta_deg.toFixed(4)}° · DEC delta: ${plan.dec_delta_deg.toFixed(4)}°\nExecution is not enabled yet.`;
    message.textContent = 'GoTo plan calculated; motors were not moved.';
  } catch (error) { gotoResult.textContent = 'GoTo planning failed.'; message.textContent = error.message; }
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

async function refreshCamera() {
  const camera = await api('/api/camera');
  cameraStatus.textContent = camera.open ? `Camera open · ${camera.type}` : 'Camera is closed.';
  cameraPreview.hidden = !camera.open;
  cameraPreview.src = camera.open ? '/api/camera/stream' : '';
}

document.querySelector('#camera-open').addEventListener('click', async () => {
  try { await api('/api/camera/open', {method: 'POST', body: JSON.stringify({type: 'mock'})}); await refreshCamera(); }
  catch (error) { message.textContent = error.message; }
});
document.querySelector('#camera-capture').addEventListener('click', async () => {
  try { await api('/api/camera/capture', {method: 'POST', body: JSON.stringify({filename: `capture-${Date.now()}.jpg`})}); message.textContent = 'Image captured with metadata.'; }
  catch (error) { message.textContent = error.message; }
});
document.querySelector('#camera-close').addEventListener('click', async () => {
  try { await api('/api/camera/close', {method: 'POST'}); await refreshCamera(); }
  catch (error) { message.textContent = error.message; }
});

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
refreshCamera();
api('/api/visual-tracker').then(renderVisualTracker).catch((error) => { message.textContent = error.message; });
api('/api/calibration').then(renderCalibration).catch((error) => { message.textContent = error.message; });
