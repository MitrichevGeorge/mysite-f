/* static/store/store_scripts.js */
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    document.getElementById(`${tabId}-tab`).style.display = 'block';
    document.querySelector(`[onclick="showTab('${tabId}')"]`).classList.add('active');

    // Update URL hash based on tab
    const tabMap = {
        'main': 'tab-1',
        'favorites': 'tab-2',
        'my-packages': 'tab-3'
    };
    window.location.hash = tabMap[tabId];
}

let codeMirrorInstance = null;

function toggleFavorite(event, filename) {
    event.stopPropagation();
    fetch(`/api/toggle-favorite/${encodeURIComponent(filename)}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const star = document.querySelector(`.favorite-star[data-filename="${filename}"]`);
            if (star) {
                star.classList.toggle('filled', data.is_favorite);
            }
            // Optionally refresh favorites tab
            if (document.getElementById('favorites-tab').style.display === 'block') {
                location.reload();
            }
        } else {
            alert('Ошибка при изменении статуса избранного.');
        }
    })
    .catch(error => {
        console.error('Error toggling favorite:', error);
        alert('Ошибка при изменении статуса избранного.');
    });
}

function openPackageModal(filename, package) {
    try {
        console.log('Opening modal with package:', package);
        if (!package || !package.name || !package.description || !package.filename || !package.code) {
            console.error('Invalid package data:', package);
            alert('Ошибка: Неверные данные пакета.');
            return;
        }

        const modal = document.getElementById('package-modal');
        document.getElementById('modal-title').textContent = package.name || 'Unnamed Package';
        document.getElementById('modal-description').textContent = package.description || 'No description available';
        document.getElementById('modal-filename').textContent = package.filename || 'Unknown file';

        const textarea = document.getElementById('code-editor');
        textarea.classList.add('loading'); // Add loading class

        // Simulate async code loading (since fetch is already async)
        setTimeout(() => {
            textarea.value = package.code || '';
            textarea.classList.remove('loading'); // Remove loading class

            if (typeof CodeMirror !== 'undefined') {
                if (codeMirrorInstance) {
                    codeMirrorInstance.toTextArea();
                }
                codeMirrorInstance = CodeMirror.fromTextArea(textarea, {
                    mode: 'css',
                    theme: 'material',
                    lineNumbers: true,
                    readOnly: true,
                    gutters: ['CodeMirror-linenumbers'],
                    lineWrapping: true
                });
                document.getElementById('codemirror-error').style.display = 'none';
            } else {
                console.error('CodeMirror is not loaded');
                document.getElementById('codemirror-error').style.display = 'block';
            }
        }, 100); // Small delay to ensure loading animation is visible

        const applyBtn = document.getElementById('apply-btn');
        applyBtn.onclick = () => {
            console.log('Applying package:', filename);
            fetch('/api/update-custom-package', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ enable: true, package: filename }),
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
            .catch(error => {
                console.error('Error applying package:', error);
                alert('Ошибка при применении пакета дизайна.');
            });
        };

        const favoriteBtn = document.getElementById('favorite-btn');
        favoriteBtn.textContent = package.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное';
        favoriteBtn.onclick = () => {
            fetch(`/api/toggle-favorite/${encodeURIComponent(filename)}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    favoriteBtn.textContent = data.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное';
                    const star = document.querySelector(`.favorite-star[data-filename="${filename}"]`);
                    if (star) {
                        star.classList.toggle('filled', data.is_favorite);
                    }
                    if (data.is_favorite) {
                        alert('Пакет добавлен в избранное!');
                    } else {
                        alert('Пакет убран из избранного!');
                    }
                    if (document.getElementById('favorites-tab').style.display === 'block') {
                        location.reload();
                    }
                } else {
                    alert('Ошибка при изменении статуса избранного.');
                }
            })
            .catch(error => {
                console.error('Error toggling favorite:', error);
                alert('Ошибка при изменении статуса избранного.');
            });
        };

        modal.style.display = 'flex';
    } catch (error) {
        console.error('Error in openPackageModal:', error);
        alert('Ошибка при открытии пакета дизайна.');
    }
}

function closePackageModal() {
    try {
        const modal = document.getElementById('package-modal');
        modal.style.display = 'none';
        const textarea = document.getElementById('code-editor');
        textarea.classList.remove('loading');
        textarea.value = 'Загрузка...';
        if (codeMirrorInstance) {
            codeMirrorInstance.toTextArea();
            codeMirrorInstance = null;
        }
        const favoriteBtn = document.getElementById('favorite-btn');
        favoriteBtn.onclick = null;
    } catch (error) {
        console.error('Error in closePackageModal:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Check URL hash to select initial tab
    const hash = window.location.hash.replace('#', '');
    const tabMap = {
        'tab-1': 'main',
        'tab-2': 'favorites',
        'tab-3': 'my-packages'
    };
    const initialTab = tabMap[hash] || 'main';
    showTab(initialTab);
});