let API_BASE = 'https://molecular-janeen-davidson0071-394ced15.koyeb.app';
if (window.location.hostname !== '' && window.location.protocol !== 'file:') {
    API_BASE = window.location.origin;
}

// Global State
let state = {
    audioFile: null,
    audioDuration: 0,
    images: [], 
    scale: 30, // px per second
    currentTime: 0,
    selectedIndex: -1,
    orientation: 'landscape'
};

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    const audioInput = document.getElementById('audio-file-input');
    document.getElementById('audio-upload-zone').onclick = () => audioInput.click();
    audioInput.onchange = handleAudioUpload;

    const imagesInput = document.getElementById('images-file-input');
    document.getElementById('add-images-btn').onclick = () => imagesInput.click();
    imagesInput.onchange = handleImageUpload;

    document.getElementById('orientation-select').onchange = (e) => {
        state.orientation = e.target.value;
        document.getElementById('preview-area').className = state.orientation;
        updatePreview();
    };

    document.getElementById('image-scale').oninput = (e) => {
        if (state.selectedIndex !== -1) {
            state.images[state.selectedIndex].scale = parseFloat(e.target.value);
            updatePreview();
        }
    };

    document.getElementById('bulk-duration-input').onchange = handleBulkDurationChange;
    document.getElementById('reverse-timeline-btn').onclick = handleReverseTimeline;

    document.getElementById('generate-btn').onclick = handleGenerate;
    document.getElementById('reset-btn').onclick = () => document.getElementById('status-overlay').classList.add('hidden');

    const canvas = document.getElementById('video-placeholder');
    canvas.onmousedown = handleCanvasMouseDown;
    canvas.onwheel = handleCanvasWheel;
}

function handleAudioUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    state.audioFile = file;
    document.getElementById('audio-name-display').innerText = file.name;
    const audio = new Audio(URL.createObjectURL(file));
    audio.onloadedmetadata = () => {
        state.audioDuration = audio.duration;
        syncDurationsToAudio();
        renderTimeline();
    };
}

function handleImageUpload(e) {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        state.images.push({
            file, previewUrl: URL.createObjectURL(file),
            id: Math.random().toString(36).substr(2, 9),
            duration: 3.0, x: 0, y: 0, scale: 1
        });
    });
    syncDurationsToAudio();
    renderTimeline();
    if (state.selectedIndex === -1) selectImage(0);
}

function syncDurationsToAudio() {
    if (!state.audioDuration || state.images.length === 0) return;
    const currentTotal = state.images.reduce((sum, img) => sum + img.duration, 0);
    const factor = state.audioDuration / currentTotal;
    state.images.forEach(img => img.duration *= factor);
}

function handleBulkDurationChange(e) {
    const val = parseFloat(e.target.value);
    if (isNaN(val) || val <= 0) return;
    state.images.forEach(img => img.duration = val);
    
    // We update audio duration too if audio exists, 
    // or just let it mismatch if user wants specific durations?
    // In this app, it seems syncDurationsToAudio is used to fit audio.
    // If user sets bulk duration, we might want to respect it but they might lose sync.
    // Let's just update and re-render.
    renderTimeline();
    updateAudioDurationDisplay();
}

function handleReverseTimeline() {
    state.images.reverse();
    renderTimeline();
    if (state.selectedIndex !== -1) {
        // Update selection if needed, or just clear it
        state.selectedIndex = -1;
    }
}

function updateAudioDurationDisplay() {
    const total = state.images.reduce((sum, img) => sum + img.duration, 0);
    document.getElementById('total-duration').innerText = formatTime(total);
}

function renderTimeline() {
    const track = document.getElementById('video-track-content');
    track.innerHTML = '';
    state.images.forEach((img, i) => {
        const item = document.createElement('div');
        item.className = `timeline-item ${state.selectedIndex === i ? 'active' : ''}`;
        item.style.width = `${img.duration * state.scale}px`;
        item.onclick = () => selectImage(i);

        const thumb = document.createElement('img'); thumb.src = img.previewUrl;
        item.appendChild(thumb);
        const badge = document.createElement('div'); badge.className = 'duration-badge';
        badge.innerText = `${img.duration.toFixed(1)}s`;
        item.appendChild(badge);
        const handle = document.createElement('div'); handle.className = 'resize-handle';
        setupResize(handle, i);
        item.appendChild(handle);
        track.appendChild(item);
    });

    const audioCont = document.getElementById('audio-clip-container');
    audioCont.innerHTML = '';
    if (state.audioFile) {
        const clip = document.createElement('div');
        clip.className = 'audio-clip';
        clip.style.width = `${state.audioDuration * state.scale}px`;
        clip.innerText = state.audioFile.name;
        audioCont.appendChild(clip);
    }
    document.getElementById('total-duration').innerText = formatTime(state.audioDuration);
}

function selectImage(index) {
    state.selectedIndex = index;
    renderTimeline();
    updatePreview();
}

function updatePreview() {
    const container = document.getElementById('video-placeholder');
    container.innerHTML = '';
    if (state.selectedIndex === -1) return;
    const imgData = state.images[state.selectedIndex];
    document.getElementById('image-scale').value = imgData.scale;

    const img = document.createElement('img');
    img.src = imgData.previewUrl;
    img.draggable = false;
    img.style.left = `${imgData.x}px`;
    img.style.top = `${imgData.y}px`;
    img.style.transform = `scale(${imgData.scale})`;
    if (state.orientation === 'landscape') img.style.width = '100%';
    else img.style.height = '100%';
    container.appendChild(img);
}

function setupResize(handle, index) {
    handle.onmousedown = (e) => {
        e.stopPropagation();
        let startX = e.clientX;
        let startDur = state.images[index].duration;
        document.onmousemove = (me) => {
            const dx = (me.clientX - startX) / state.scale;
            const newDur = Math.max(0.5, startDur + dx);
            const oldDur = state.images[index].duration;
            const diff = newDur - oldDur;
            const targetIdx = (index === state.images.length - 1) ? index - 1 : index + 1;
            if (state.images[targetIdx] && state.images[targetIdx].duration - diff > 0.1) {
                state.images[index].duration = newDur;
                state.images[targetIdx].duration -= diff;
                renderTimeline();
            }
        };
        document.onmouseup = () => document.onmousemove = document.onmouseup = null;
    };
}

function handleCanvasWheel(e) {
    e.preventDefault();
    if (state.selectedIndex === -1) return;
    const img = state.images[state.selectedIndex];
    img.scale = Math.max(0.1, Math.min(5, img.scale + (e.deltaY > 0 ? -0.1 : 0.1)));
    updatePreview();
}

function handleCanvasMouseDown(e) {
    if (state.selectedIndex === -1) return;
    e.preventDefault();
    const img = state.images[state.selectedIndex];
    let startX = e.clientX - img.x;
    let startY = e.clientY - img.y;
    document.onmousemove = (me) => {
        img.x = me.clientX - startX;
        img.y = me.clientY - startY;
        updatePreview();
    };
    document.onmouseup = () => document.onmousemove = document.onmouseup = null;
}

function formatTime(s) {
    const m = Math.floor(s/60);
    return `${m}:${Math.floor(s%60).toString().padStart(2,'0')}`;
}

async function handleGenerate() {
    if (!state.audioFile || state.images.length === 0) return alert("Add content first");
    const formData = new FormData();
    formData.append('audio', state.audioFile);
    const timeline = state.images.map((img, i) => {
        formData.append('images', img.file);
        return { file_index: i, duration: img.duration, x_offset: img.x, y_offset: img.y, scale: img.scale };
    });
    formData.append('timeline_data', JSON.stringify(timeline));
    formData.append('orientation', state.orientation);
    formData.append('style', document.getElementById('style-select').value);
    document.getElementById('status-overlay').classList.remove('hidden');
    try {
        const res = await fetch(`${API_BASE}/video/generate-video`, { method: 'POST', body: formData });
        const data = await res.json();
        pollStatus(data.task_id);
    } catch (e) { alert(e.message); }
}

function pollStatus(tid) {
    const interval = setInterval(async () => {
        const res = await fetch(`${API_BASE}/video/status/${tid}`);
        const data = await res.json();
        document.getElementById('status-text').innerText = data.status.toUpperCase();
        if (data.status === 'completed') {
            clearInterval(interval);
            document.getElementById('result-actions').classList.remove('hidden');
            document.getElementById('download-link').href = `${API_BASE}${data.download_url}`;
        }
    }, 3000);
}