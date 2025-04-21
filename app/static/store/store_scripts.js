function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
    document.getElementById(`${tabId}-tab`).style.display = 'block';
    document.querySelector(`[onclick="showTab('${tabId}')"]`).classList.add('active');
    window.location.hash = { main: 'tab-1', favorites: 'tab-2', 'my-packages': 'tab-3' }[tabId];
}

let codeMirrorInstance = null;

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
            if (document.getElementById('favorites-tab').style.display === 'block') location.reload();
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
                if (document.getElementById('favorites-tab').style.display === 'block') location.reload();
            } else {
                alert('Ошибка при изменении статуса избранного.');
            }
        })
        .catch(() => alert('Ошибка при изменении статуса избранного.'));
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
    document.getElementById('favorite-btn').onclick = null;
}

document.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.replace('#', '');
    const tabMap = { 'tab-1': 'main', 'tab-2': 'favorites', 'tab-3': 'my-packages' };
    showTab(tabMap[hash] || 'main');
});