function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
    document.getElementById(`${tabId}-tab`).style.display = 'block';
    document.querySelector(`[onclick="showTab('${tabId}')"]`).classList.add('active');
    window.location.hash = { main: 'tab-1', favorites: 'tab-2', 'my-packages': 'tab-3' }[tabId];
}

let codeMirrorInstance = null;
let previewCodeMirrorInstance = null;
let isEditMode = false;

function toggleFavorite(event, filename) {
    event.stopPropagation();
    fetch(`/api/toggle-favorite/${encodeURIComponent(filename)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const star = document.querySelector(`.favorite-star[data-filename="${filename}"]`);
            if (star) star.classList.toggle('filled', data.is_favorite);
            if (document.getElementById('favorites-tab').style.display === 'block' || document.getElementById('my-packages-tab').style.display === 'block') location.reload();
        } else {
            alert('Ошибка при изменении статуса избранного.');
        }
    })
    .catch(() => alert('Ошибка при изменении статуса избранного.'));
}

function openPackageModal(filename, package) {
    if (!package || !package.name || !package.description || !package.filename || !package.code) {
        alert('Ошибка: Неверные данные пакета.');
        return;
    }

    const modal = document.getElementById('package-modal');
    document.getElementById('modal-title').textContent = package.name || 'Unnamed Package';
    document.getElementById('modal-description').textContent = package.description || 'No description available';
    document.getElementById('modal-filename').textContent = package.filename || 'Unknown file';

    const creatorButtons = document.getElementById('creator-buttons');
    creatorButtons.style.display = package.is_creator ? 'block' : 'none';

    const viewMode = document.getElementById('view-mode');
    const editMode = document.getElementById('edit-mode');
    viewMode.style.display = 'block';
    editMode.style.display = 'none';
    isEditMode = false;

    const textarea = document.getElementById('code-editor');
    textarea.classList.add('loading');

    setTimeout(() => {
        textarea.value = package.code || '';
        textarea.classList.remove('loading');

        if (typeof CodeMirror !== 'undefined') {
            if (codeMirrorInstance) codeMirrorInstance.toTextArea();
            codeMirrorInstance = CodeMirror.fromTextArea(textarea, {
                mode: 'css',
                theme: 'material',
                lineNumbers: true,
                readOnly: true,
                gutters: ['CodeMirror-linenumbers'],
                lineWrapping: true
            });
            document.getElementById('codemirror-error').style.display = 'none';

            const lineHeight = codeMirrorInstance.defaultTextHeight();
            codeMirrorInstance.on('scroll', () => {
                const { top: scrollTop } = codeMirrorInstance.getScrollInfo();
                const linesScrolled = scrollTop / lineHeight;
                const codeMirrorElement = codeMirrorInstance.getWrapperElement();
                if (linesScrolled > 4 && !codeMirrorElement.classList.contains('expanded')) {
                    codeMirrorElement.classList.add('expanded');
                }
            });
        } else {
            document.getElementById('codemirror-error').style.display = 'block';
        }
    }, 100);

    const applyBtn = document.getElementById('apply-btn');
    applyBtn.onclick = () => {
        fetch('/api/update-custom-package', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enable: true, package: filename })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Пакет дизайна успешно применён!');
                location.reload();
            } else {
                alert('Ошибка при применении пакета дизайна.');
            }
        })
        .catch(() => alert('Ошибка при применении пакета дизайна.'));
    };

    const favoriteBtn = document.getElementById('favorite-btn');
    favoriteBtn.textContent = package.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное';
    favoriteBtn.onclick = () => {
        fetch(`/api/toggle-favorite/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                favoriteBtn.textContent = data.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное';
                const star = document.querySelector(`.favorite-star[data-filename="${filename}"]`);
                if (star) star.classList.toggle('filled', data.is_favorite);
                alert(data.is_favorite ? 'Пакет добавлен в избранное!' : 'Пакет убран из избранного!');
                if (document.getElementById('favorites-tab').style.display === 'block' || document.getElementById('my-packages-tab').style.display === 'block') location.reload();
            } else {
                alert('Ошибка при изменении статуса избранного.');
            }
        })
        .catch(() => alert('Ошибка при изменении статуса избранного.'));
    };

    const editBtn = document.getElementById('edit-btn');
    editBtn.onclick = () => {
        if (codeMirrorInstance) {
            viewMode.style.display = 'none';
            editMode.style.display = 'block';
            creatorButtons.style.display = 'none';
            isEditMode = true;
            codeMirrorInstance.setOption('readOnly', false);
            codeMirrorInstance.refresh();
        }
    };

    const saveBtn = document.getElementById('save-btn');
    saveBtn.onclick = () => {
        const updatedCode = codeMirrorInstance.getValue();
        fetch(`/api/update-package/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: updatedCode })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Пакет успешно обновлён!');
                openPreviewModal(data.metadata);
                closePackageModal();
            } else {
                alert(`Ошибка: ${data.error}`);
            }
        })
        .catch(() => alert('Ошибка при обновлении пакета.'));
    };

    const uploadBtn = document.getElementById('upload-btn');
    uploadBtn.onclick = () => {
        openUploadOverlay(filename);
    };

    modal.style.display = 'flex';
}

function closePackageModal() {
    const modal = document.getElementById('package-modal');
    modal.style.display = 'none';
    const textarea = document.getElementById('code-editor');
    textarea.classList.remove('loading');
    textarea.value = '';
    if (codeMirrorInstance) {
        codeMirrorInstance.getWrapperElement().classList.remove('expanded');
        codeMirrorInstance.toTextArea();
        codeMirrorInstance = null;
    }
    document.getElementById('view-mode').style.display = 'block';
    document.getElementById('edit-mode').style.display = 'none';
    document.getElementById('creator-buttons').style.display = 'none';
    document.getElementById('favorite-btn').onclick = null;
    document.getElementById('edit-btn').onclick = null;
    document.getElementById('upload-btn').onclick = null;
    document.getElementById('save-btn').onclick = null;
    isEditMode = false;
}

function openUploadOverlay(existingFilename = null) {
    const overlay = document.getElementById('upload-overlay');
    overlay.style.display = 'flex';

    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    const clearListeners = () => {
        dropZone.removeEventListener('click', clickHandler);
        dropZone.removeEventListener('dragover', dragoverHandler);
        dropZone.removeEventListener('dragleave', dragleaveHandler);
        dropZone.removeEventListener('drop', dropHandler);
        fileInput.removeEventListener('change', changeHandler);
    };

    const clickHandler = () => fileInput.click();
    const dragoverHandler = (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    };
    const dragleaveHandler = () => {
        dropZone.classList.remove('dragover');
    };
    const dropHandler = (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        clearListeners();
        handleFile(file, existingFilename);
    };
    const changeHandler = () => {
        const file = fileInput.files[0];
        clearListeners();
        handleFile(file, existingFilename);
    };

    dropZone.addEventListener('click', clickHandler);
    dropZone.addEventListener('dragover', dragoverHandler);
    dropZone.addEventListener('dragleave', dragleaveHandler);
    dropZone.addEventListener('drop', dropHandler);
    fileInput.addEventListener('change', changeHandler);
}

function closeUploadOverlay() {
    const overlay = document.getElementById('upload-overlay');
    overlay.style.display = 'none';
}

function openPreviewModal(package) {
    if (!package || !package.name || !package.description || !package.filename || !package.code) {
        alert('Ошибка: Неверные данные пакета.');
        return;
    }

    const modal = document.getElementById('preview-modal');
    document.getElementById('preview-title').textContent = package.name || 'Unnamed Package';
    document.getElementById('preview-description').textContent = package.description || 'No description available';
    document.getElementById('preview-filename').textContent = package.filename || 'Unknown file';

    const textarea = document.getElementById('preview-code-editor');
    textarea.classList.add('loading');

    setTimeout(() => {
        textarea.value = package.code || '';
        textarea.classList.remove('loading');

        if (typeof CodeMirror !== 'undefined') {
            if (previewCodeMirrorInstance) previewCodeMirrorInstance.toTextArea();
            previewCodeMirrorInstance = CodeMirror.fromTextArea(textarea, {
                mode: 'css',
                theme: 'material',
                lineNumbers: true,
                readOnly: true,
                gutters: ['CodeMirror-linenumbers'],
                lineWrapping: true
            });
            document.getElementById('preview-codemirror-error').style.display = 'none';

            const lineHeight = previewCodeMirrorInstance.defaultTextHeight();
            previewCodeMirrorInstance.on('scroll', () => {
                const { top: scrollTop } = previewCodeMirrorInstance.getScrollInfo();
                const linesScrolled = scrollTop / lineHeight;
                const codeMirrorElement = previewCodeMirrorInstance.getWrapperElement();
                if (linesScrolled > 4 && !codeMirrorElement.classList.contains('expanded')) {
                    codeMirrorElement.classList.add('expanded');
                }
            });
        } else {
            document.getElementById('preview-codemirror-error').style.display = 'block';
        }
    }, 100);

    const publishBtn = document.getElementById('publish-btn');
    publishBtn.onclick = () => {
        alert('Пакет успешно опубликован!');
        closePreviewModal();
        closeUploadOverlay();
        closePackageModal();
        location.reload();
    };

    modal.style.display = 'flex';
}

function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    modal.style.display = 'none';
    const textarea = document.getElementById('preview-code-editor');
    textarea.classList.remove('loading');
    textarea.value = '';
    if (previewCodeMirrorInstance) {
        previewCodeMirrorInstance.getWrapperElement().classList.remove('expanded');
        previewCodeMirrorInstance.toTextArea();
        previewCodeMirrorInstance = null;
    }
}

function handleFile(file, existingFilename = null) {
    if (!file) {
        alert('Файл не выбран.');
        return;
    }

    if (!file.name.endsWith('.css')) {
        alert('Пожалуйста, выберите файл с расширением .css');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const content = e.target.result;
        const xmlRegex = /\/\*[\s\S]*?<\?xml[\s\S]*?<package[\s\S]*?<name>[\s\S]*?<\/name>[\s\S]*?<description>[\s\S]*?<\/description>[\s\S]*?<\/package>[\s\S]*?\*\//;
        if (!xmlRegex.test(content)) {
            alert('Файл должен содержать XML-комментарий с метаданными (<name> и <description>) в начале.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        if (existingFilename) {
            formData.append('existing_filename', existingFilename);
        }

        fetch('/api/upload-package', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                openPreviewModal(data.metadata);
            } else {
                alert(`Ошибка: ${data.error}`);
            }
        })
        .catch(() => alert('Ошибка при загрузке пакета.'));
    };
    reader.readAsText(file);
}

document.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.replace('#', '');
    const tabMap = { 'tab-1': 'main', 'tab-2': 'favorites', 'tab-3': 'my-packages' };
    showTab(tabMap[hash] || 'main');
});