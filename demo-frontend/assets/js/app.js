let API_BASE = 'https://molecular-janeen-davidson0071-394ced15.koyeb.app';
if (window.location.hostname !== '' && window.location.protocol !== 'file:') {
    API_BASE = window.location.origin;
}

// Global State
let state = {
    audioFile: null,
    audioDuration: 0,
    images: [], // Each: { file, previewUrl, id, duration, x, y, scale, type: 'image'|'video', videoDuration }
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
    imagesInput.onchange = handleMediaUpload;

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

/**
 * Handles upload of both image and video files.
 */
function handleMediaUpload(e) {
    const files = Array.from(e.target.files);
    const promises = files.map(file => {
        return new Promise(resolve => {
            const type = file.type.startsWith('video/') ? 'video' : 'image';
            const previewUrl = URL.createObjectURL(file);

            if (type === 'video') {
                // Probe the video duration from its metadata
                const vid = document.createElement('video');
                vid.preload = 'metadata';
                vid.src = previewUrl;
                vid.onloadedmetadata = () => {
                    const dur = isFinite(vid.duration) && vid.duration > 0 ? vid.duration : 3.0;
                    resolve({
                        file,
                        previewUrl,
                        id: Math.random().toString(36).substr(2, 9),
                        duration: dur,
                        x: 0, y: 0, scale: 1,
                        type: 'video',
                        videoDuration: dur
                    });
                };
                vid.onerror = () => {
                    resolve({
                        file,
                        previewUrl,
                        id: Math.random().toString(36).substr(2, 9),
                        duration: 3.0,
                        x: 0, y: 0, scale: 1,
                        type: 'video',
                        videoDuration: 3.0
                    });
                };
            } else {
                resolve({
                    file,
                    previewUrl,
                    id: Math.random().toString(36).substr(2, 9),
                    duration: 3.0,
                    x: 0, y: 0, scale: 1,
                    type: 'image',
                    videoDuration: null
                });
            }
        });
    });

    Promise.all(promises).then(clips => {
        clips.forEach(clip => state.images.push(clip));
        syncDurationsToAudio();
        renderTimeline();
        if (state.selectedIndex === -1) selectImage(0);
    });

    // Reset input so the same file can be re-added if needed
    e.target.value = '';
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
    renderTimeline();
    updateAudioDurationDisplay();
}

function handleReverseTimeline() {
    state.images.reverse();
    renderTimeline();
    if (state.selectedIndex !== -1) {
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
    state.images.forEach((clip, i) => {
        const item = document.createElement('div');
        item.className = `timeline-item ${state.selectedIndex === i ? 'active' : ''}`;
        item.style.width = `${clip.duration * state.scale}px`;
        item.onclick = () => selectImage(i);

        if (clip.type === 'video') {
            // Use a video element as thumbnail (muted, no controls, paused at start)
            const thumb = document.createElement('video');
            thumb.src = clip.previewUrl;
            thumb.muted = true;
            thumb.preload = 'metadata';
            thumb.currentTime = 0.1; // Seek slightly in to get a frame
            thumb.style.width = '100%';
            thumb.style.height = '100%';
            thumb.style.objectFit = 'cover';
            thumb.style.opacity = '0.7';
            thumb.style.pointerEvents = 'none';
            item.appendChild(thumb);

            // Video type badge
            const typeBadge = document.createElement('div');
            typeBadge.className = 'media-type-badge video-badge';
            typeBadge.innerHTML = '▶ Video';
            item.appendChild(typeBadge);
        } else {
            const thumb = document.createElement('img');
            thumb.src = clip.previewUrl;
            item.appendChild(thumb);
        }

        const badge = document.createElement('div');
        badge.className = 'duration-badge';
        badge.innerText = `${clip.duration.toFixed(1)}s`;
        item.appendChild(badge);

        const handle = document.createElement('div');
        handle.className = 'resize-handle';
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
    document.getElementById('total-duration').innerText = formatTime(
        state.images.reduce((s, img) => s + img.duration, 0)
    );
}

function selectImage(index) {
    state.selectedIndex = index;
    renderTimeline();
    updatePreview();
}

function updatePreview() {
    const container = document.getElementById('video-placeholder');
    // Pause any existing preview video before clearing
    const existingVid = container.querySelector('video');
    if (existingVid) existingVid.pause();
    container.innerHTML = '';

    if (state.selectedIndex === -1) return;
    const clipData = state.images[state.selectedIndex];
    document.getElementById('image-scale').value = clipData.scale;

    if (clipData.type === 'video') {
        const vid = document.createElement('video');
        vid.src = clipData.previewUrl;
        vid.controls = true;
        vid.loop = true;
        vid.autoplay = true;
        vid.muted = false;
        vid.draggable = false;
        vid.style.left = `${clipData.x}px`;
        vid.style.top = `${clipData.y}px`;
        vid.style.transform = `scale(${clipData.scale})`;
        if (state.orientation === 'landscape') vid.style.width = '100%';
        else vid.style.height = '100%';
        vid.style.position = 'absolute';
        container.appendChild(vid);
    } else {
        const img = document.createElement('img');
        img.src = clipData.previewUrl;
        img.draggable = false;
        img.style.left = `${clipData.x}px`;
        img.style.top = `${clipData.y}px`;
        img.style.transform = `scale(${clipData.scale})`;
        if (state.orientation === 'landscape') img.style.width = '100%';
        else img.style.height = '100%';
        container.appendChild(img);
    }
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
    const clip = state.images[state.selectedIndex];
    // Don't intercept drag on video controls
    if (e.target.tagName === 'VIDEO') return;
    e.preventDefault();
    let startX = e.clientX - clip.x;
    let startY = e.clientY - clip.y;
    document.onmousemove = (me) => {
        clip.x = me.clientX - startX;
        clip.y = me.clientY - startY;
        updatePreview();
    };
    document.onmouseup = () => document.onmousemove = document.onmouseup = null;
}

function formatTime(s) {
    const m = Math.floor(s / 60);
    return `${m}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
}

async function handleGenerate() {
    if (!state.audioFile || state.images.length === 0) return alert("Add content first");
    const formData = new FormData();
    formData.append('audio', state.audioFile);

    const timeline = state.images.map((clip, i) => {
        // All clips go through the 'images' field — backend differentiates by media_types
        formData.append('images', clip.file);
        return {
            file_index: i,
            duration: clip.duration,
            x_offset: clip.x,
            y_offset: clip.y,
            scale: clip.scale,
            media_type: clip.type  // 'image' or 'video'
        };
    });

    formData.append('timeline_data', JSON.stringify(timeline));
    formData.append('orientation', state.orientation);
    formData.append('style', document.getElementById('style-select').value);

    document.getElementById('status-overlay').classList.remove('hidden');
    document.getElementById('result-actions').classList.add('hidden');
    document.getElementById('status-text').innerText = 'Processing...';

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
        } else if (data.status === 'failed') {
            clearInterval(interval);
            document.getElementById('status-text').innerText = `Failed: ${data.error_message || 'Unknown error'}`;
        }
    }, 3000);
}