const API_BASE = 'http://localhost:8000';
let selectedFiles = []; // State to hold multiple files cumulatively

document.addEventListener('DOMContentLoaded', () => {
    setupToggles();
    setupUrlList();
    setupFileUpload();

    const generateBtn = document.getElementById('generate-btn');
    generateBtn.addEventListener('click', handleGenerate);
});

function setupToggles() {
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const group = btn.dataset.group;
            const type = btn.dataset.type;

            document.querySelectorAll(`.toggle-btn[data-group="${group}"]`).forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (group === 'audio') {
                document.getElementById('audio-file').classList.toggle('hidden', type === 'url');
                document.getElementById('audio-url').classList.toggle('hidden', type === 'file');
            } else {
                document.getElementById('file-uploader-box').classList.toggle('hidden', type === 'url');
                document.getElementById('url-list').classList.toggle('hidden', type === 'file');
            }
        });
    });
}

function setupUrlList() {
    const urlList = document.getElementById('url-list');
    urlList.addEventListener('click', (e) => {
        if (e.target.classList.contains('add-url')) {
            const entry = document.createElement('div');
            entry.className = 'url-entry';
            entry.innerHTML = `
                <input type="text" class="image-url" placeholder="https://example.com/image.jpg">
                <button class="remove-url">×</button>
            `;
            urlList.appendChild(entry);
            entry.querySelector('.remove-url').onclick = () => entry.remove();
        }
    });
}

function setupFileUpload() {
    const fileInput = document.getElementById('images-files');
    const previewList = document.getElementById('file-preview-list');

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        files.forEach(file => {
            if (!selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
                addFileToPreview(file);
            }
        });
        // Reset input so change event fires again for same file if needed
        fileInput.value = '';
    });
}

function addFileToPreview(file) {
    const previewList = document.getElementById('file-preview-list');
    const div = document.createElement('div');
    div.className = 'preview-item';

    const reader = new FileReader();
    reader.onload = (e) => {
        div.innerHTML = `
            <img src="${e.target.result}" alt="preview">
            <button class="remove-file" title="Remove">×</button>
        `;
        div.querySelector('.remove-file').onclick = () => {
            selectedFiles = selectedFiles.filter(f => f !== file);
            div.remove();
        };
    };
    reader.readAsDataURL(file);
    previewList.appendChild(div);
}

async function handleGenerate() {
    const formData = new FormData();

    // 1. Get Audio
    const audioType = document.querySelector('.toggle-btn[data-group="audio"].active').dataset.type;
    if (audioType === 'file') {
        const file = document.getElementById('audio-file').files[0];
        if (!file) return alert('Please select an audio file');
        formData.append('audio', file);
    } else {
        const url = document.getElementById('audio-url').value;
        if (!url) return alert('Please enter an audio URL');
        formData.append('audio', url);
    }

    // 2. Get Images
    const imagesType = document.querySelector('.toggle-btn[data-group="images"].active').dataset.type;
    if (imagesType === 'file') {
        if (selectedFiles.length === 0) return alert('Please upload at least one image');
        selectedFiles.forEach(file => {
            formData.append('images', file);
        });
    } else {
        const urls = Array.from(document.querySelectorAll('.image-url'))
            .map(input => input.value.trim())
            .filter(v => v !== '');
        if (urls.length === 0) return alert('Please enter at least one image URL');
        urls.forEach(url => formData.append('images', url));
    }

    document.getElementById('input-section').classList.add('hidden');
    document.getElementById('status-section').classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/video/generate-video`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Generation failed to start');

        const data = await response.json();
        pollStatus(data.task_id);

    } catch (err) {
        alert(err.message);
        resetUI();
    }
}

async function pollStatus(taskId) {
    const statusText = document.getElementById('status-text');
    const taskIdDisplay = document.getElementById('task-id-display');
    taskIdDisplay.innerText = `Task ID: ${taskId}`;

    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/video/status/${taskId}`);
            const data = await response.json();

            const rawStatus = (data.status || '').toLowerCase();
            let statusDisplay = rawStatus.toUpperCase();

            if (data.error_message) {
                statusDisplay = `FAILED: ${data.error_message}`;
            }
            statusText.innerText = `Status: ${statusDisplay}`;

            if (rawStatus === 'completed') {
                clearInterval(interval);
                document.querySelector('#status-section h2').innerText = "Video Ready!";
                showResult(`${API_BASE}${data.download_url}`);
            } else if (rawStatus === 'failed') {
                clearInterval(interval);
                document.querySelector('#status-section h2').innerText = "Generation Failed";
                document.querySelector('.spinner').classList.add('hidden');
                document.getElementById('result-actions').classList.remove('hidden');
                document.getElementById('download-link').classList.add('hidden');
                document.getElementById('reset-btn').innerText = "Try Again";
                document.getElementById('reset-btn').onclick = resetUI;
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 3000);
}

function showResult(downloadUrl) {
    document.querySelector('.spinner').classList.add('hidden');
    document.getElementById('result-actions').classList.remove('hidden');
    document.getElementById('download-link').href = downloadUrl;
    document.getElementById('reset-btn').onclick = resetUI;
}

function resetUI() {
    document.getElementById('input-section').classList.remove('hidden');
    document.getElementById('status-section').classList.add('hidden');
    document.getElementById('result-actions').classList.add('hidden');
    document.getElementById('download-link').classList.remove('hidden');
    document.querySelector('.spinner').classList.remove('hidden');
    document.getElementById('reset-btn').innerText = "Create Another";
}
