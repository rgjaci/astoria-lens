/* Astoria Lens - browser glue. Vanilla JS, no build step. */

const $ = (id) => document.getElementById(id);

const state = {
  prepared: null,      // {dataUrl, base64, mime}
  mode: 'explain',
  lang: 'en',
  busy: false,
  text: '',
  model: 'gemma-4-26b-a4b-it',
  demo: false,
  stream: null,
};

const SPEECH_LANG = {
  en: 'en-US', es: 'es-ES', el: 'el-GR', ar: 'ar-SA', bn: 'bn-BD', zh: 'zh-CN',
};

/* ------------------------------------------------------------------ helpers */

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function inline(value) {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function renderMarkdown(text) {
  const out = [];
  let list = null;
  const flush = () => {
    if (list) { out.push('</' + list + '>'); list = null; }
  };
  for (const raw of String(text).split('\n')) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    let m;
    if ((m = line.match(/^#{1,4}\s+(.*)$/))) {
      flush(); out.push('<h3>' + inline(m[1]) + '</h3>'); continue;
    }
    // The model often answers with plain ALL-CAPS section labels instead of markdown.
    if (line.length <= 48 && /[A-Z]/.test(line) && /^[A-Z0-9][A-Z0-9 &'\u2019\/\-.:\u00b7]*$/.test(line)) {
      flush(); out.push('<h3>' + inline(line.replace(/:$/, '')) + '</h3>'); continue;
    }
    if ((m = line.match(/^[-*\u2022]\s+(.*)$/))) {
      if (list !== 'ul') { flush(); out.push('<ul>'); list = 'ul'; }
      out.push('<li>' + inline(m[1]) + '</li>'); continue;
    }
    if ((m = line.match(/^\d+[.)]\s+(.*)$/))) {
      if (list !== 'ol') { flush(); out.push('<ol>'); list = 'ol'; }
      out.push('<li>' + inline(m[1]) + '</li>'); continue;
    }
    flush();
    out.push('<p>' + inline(line) + '</p>');
  }
  flush();
  return out.join('\n');
}

function cameraNote(text) {
  const note = $('cameraNote');
  note.textContent = text;
  note.hidden = !text;
  // style.css sets `display: grid` on .camera-note, which beats the [hidden]
  // attribute in the cascade - set it inline so the note really hides.
  note.style.display = text ? 'grid' : 'none';
}

function showError(message) {
  const box = $('error');
  box.textContent = message;
  box.hidden = false;
}

function clearError() {
  const box = $('error');
  box.hidden = true;
  box.textContent = '';
}

function setMeta(text) {
  $('meta').textContent = text || '';
}

/* ------------------------------------------------------------------- camera */

async function startCamera() {
  const video = $('video');
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    cameraNote('This browser will not give a page a camera here — use "Choose photo" or a sample.');
    $('shutter').disabled = true;
    return;
  }
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = state.stream;
    await video.play();
    cameraNote('');
    $('shutter').disabled = false;
  } catch (err) {
    cameraNote('Camera unavailable (' + (err.name || 'blocked') + '). Use "Choose photo" or a sample below.');
    $('shutter').disabled = true;
  }
}

function drawScaled(source, width, height) {
  const MAX = 1280;
  const scale = Math.min(1, MAX / Math.max(width, height));
  const w = Math.max(1, Math.round(width * scale));
  const h = Math.max(1, Math.round(height * scale));
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  canvas.getContext('2d').drawImage(source, 0, 0, w, h);
  return canvas.toDataURL('image/jpeg', 0.85);
}

function dataUrlToPrepared(dataUrl) {
  return { dataUrl, base64: dataUrl.split(',')[1], mime: 'image/jpeg' };
}

function captureFromVideo() {
  const video = $('video');
  if (!video.videoWidth) {
    showError('The camera has not started yet. Give it a second, or choose a photo.');
    return null;
  }
  return dataUrlToPrepared(drawScaled(video, video.videoWidth, video.videoHeight));
}

async function prepareBlob(blob) {
  const bitmap = await createImageBitmap(blob);
  try {
    return dataUrlToPrepared(drawScaled(bitmap, bitmap.width, bitmap.height));
  } finally {
    bitmap.close();
  }
}

function setPrepared(prepared) {
  state.prepared = prepared;
  cameraNote('');
  const preview = $('preview');
  preview.src = prepared.dataUrl;
  preview.hidden = false;
  // style.css sets `display: block` on .viewport video/img, which beats the
  // [hidden] attribute - set the display inline so the preview really shows.
  preview.style.display = 'block';
  $('video').hidden = true;
  $('video').style.display = 'none';
  $('shutter').hidden = true;
  $('retake').hidden = false;
  clearError();
  setMeta('');
  analyze();
}

function retake() {
  state.prepared = null;
  $('preview').hidden = true;
  $('preview').style.display = 'none';
  $('preview').removeAttribute('src');
  $('video').hidden = false;
  $('video').style.display = 'block';
  $('shutter').hidden = false;
  $('retake').hidden = true;
  $('scan').hidden = true;
  setMeta('');
  clearError();
  $('resultBody').innerHTML = '<p class="empty">Take a photo, pick one from your library, or load a sample.</p>';
  $('speak').hidden = true;
  $('copy').hidden = true;
}

/* ------------------------------------------------------------------ analyze */

async function analyze() {
  if (!state.prepared || state.busy) return;
  state.busy = true;
  clearError();
  $('scan').hidden = false;
  $('resultBody').innerHTML = '<div class="loading"><span class="dots"><span></span><span></span><span></span></span> Looking at your photo with Gemma 4…</div>';
  $('speak').hidden = true;
  $('copy').hidden = true;

  const started = performance.now();
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: state.prepared.base64,
        mime: state.prepared.mime,
        mode: state.mode,
        lang: state.lang,
        question: $('question').value.trim(),
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) throw new Error(data.error || ('Server said HTTP ' + response.status));

    state.text = data.text || '';
    state.demo = !!data.demo;
    state.model = data.model || state.model;
    updatePills();

    const elapsed = Math.round(performance.now() - started);
    $('resultBody').innerHTML = renderMarkdown(state.text);
    setMeta([
      state.demo ? 'demo output' : state.model,
      data.ms ? data.ms + ' ms model' : null,
      elapsed + ' ms end-to-end',
      'mode: ' + state.mode,
      'lang: ' + state.lang,
    ].filter(Boolean).join('  ·  '));
    $('speak').hidden = false;
    $('copy').hidden = false;
  } catch (err) {
    $('resultBody').innerHTML = '<p class="empty">Nothing to show yet.</p>';
    showError(err && err.message ? err.message : 'Something went wrong.');
  } finally {
    state.busy = false;
    $('scan').hidden = true;
  }
}

/* -------------------------------------------------------------------- pills */

async function probeHealth() {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    state.demo = !!data.demo;
    state.model = data.model || state.model;
    updatePills();
  } catch (err) {
    /* offline or server gone - the analyze call will explain it */
  }
}

function updatePills() {
  $('modelPill').textContent = state.model;
  $('demoPill').hidden = !state.demo;
  $('livePill').hidden = state.demo;
}

/* ------------------------------------------------------------------- speech */

function speak() {
  if (!state.text) return;
  if (!('speechSynthesis' in window)) {
    showError('This browser has no speech engine. The text is still on screen.');
    return;
  }
  const clean = state.text
    .replace(/\[DEMO MODE[^\]]*\]/g, '')
    .replace(/[#*_`>]/g, '')
    .replace(/\n+/g, '. ')
    .trim();
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.lang = SPEECH_LANG[state.lang] || 'en-US';
  utterance.rate = 0.98;
  window.speechSynthesis.speak(utterance);
}

async function copyText() {
  if (!state.text) return;
  try {
    await navigator.clipboard.writeText(state.text);
    const button = $('copy');
    const label = button.textContent;
    button.textContent = 'Copied';
    setTimeout(() => { button.textContent = label; }, 1400);
  } catch (err) {
    showError('Clipboard blocked. Select the text and copy it manually.');
  }
}

/* ------------------------------------------------------------------ samples */

async function loadSample(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Sample image not found (' + response.status + ').');
    const blob = await response.blob();
    setPrepared(await prepareBlob(blob));
  } catch (err) {
    showError('Could not load the sample: ' + (err.message || err));
  }
}

/* -------------------------------------------------------------------- wires */

function wire() {
  $('shutter').addEventListener('click', () => {
    const prepared = captureFromVideo();
    if (prepared) setPrepared(prepared);
  });

  $('retake').addEventListener('click', retake);

  $('file').addEventListener('change', async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    try {
      setPrepared(await prepareBlob(file));
    } catch (err) {
      showError('That file could not be read as an image.');
    } finally {
      event.target.value = '';
    }
  });

  $('sampleMenu').addEventListener('click', () => loadSample('/samples/menu.png'));
  $('sampleFlyer').addEventListener('click', () => loadSample('/samples/flyer.png'));

  document.querySelectorAll('.mode').forEach((button) => {
    button.addEventListener('click', () => {
      state.mode = button.dataset.mode;
      document.querySelectorAll('.mode').forEach((b) => b.classList.toggle('active', b === button));
      $('askbar').hidden = state.mode !== 'ask';
      if (state.mode === 'ask') $('question').focus();
      if (state.prepared) analyze();
    });
  });

  $('lang').addEventListener('change', () => {
    state.lang = $('lang').value;
    if (state.prepared) analyze();
  });

  $('askGo').addEventListener('click', analyze);
  $('question').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') analyze();
  });

  $('speak').addEventListener('click', speak);
  $('copy').addEventListener('click', copyText);
  $('error').addEventListener('click', clearError);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) analyze();
  });

  window.addEventListener('dragover', (event) => event.preventDefault());
  window.addEventListener('drop', async (event) => {
    event.preventDefault();
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (!file) return;
    try {
      setPrepared(await prepareBlob(file));
    } catch (err) {
      showError('Drop a photo file (JPEG, PNG, or WebP).');
    }
  });
}

/* ---------------------------------------------------------------- deep link */

// ?sample=menu or ?sample=flyer auto-loads a sample photo on page start.
// Useful for screenshots and for a demo that cannot depend on camera permission.
// This path skips the camera and canvas downscale: the sample is already small,
// so it loads straight into the preview and keeps its original PNG bytes.
async function autoLoadSampleFromQuery() {
  const name = new URLSearchParams(window.location.search).get('sample');
  if (!name) return;
  const safe = name.toLowerCase().replace(/[^a-z0-9_-]/g, '');
  if (!safe) return;
  try {
    const response = await fetch('/samples/' + safe + '.png');
    if (!response.ok) throw new Error('Sample image not found (' + response.status + ').');
    const blob = await response.blob();
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error || new Error('read failed'));
      reader.readAsDataURL(blob);
    });
    setPrepared({ dataUrl, base64: String(dataUrl).split(',')[1], mime: blob.type || 'image/png' });
  } catch (err) {
    showError('Could not load the sample: ' + (err.message || err));
  }
}

wire();
probeHealth();
startCamera();
autoLoadSampleFromQuery();
