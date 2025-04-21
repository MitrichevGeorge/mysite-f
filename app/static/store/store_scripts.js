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
}

let codeMirrorInstance = null;

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
        textarea.value = package.code || '';

        if (typeof CodeMirror !== 'undefined') {
            if (codeMirrorInstance) {
                codeMirrorInstance.toTextArea();
            }
            codeMirrorInstance = CodeMirror.fromTextArea(textarea, {
                mode: 'css',
                theme: 'material',
                lineNumbers: true,
                readOnly: true,
                gutters: ['CodeMirror-linenumbers'], /* Explicitly define line number gutter */
                lineWrapping: true /* Prevent horizontal overflow */
            });
            document.getElementById('codemirror-error').style.display = 'none';
        } else {
            console.error('CodeMirror is not loaded');
            document.getElementById('codemirror-error').style.display = 'block';
        }

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
        if (codeMirrorInstance) {
            codeMirrorInstance.toTextArea();
            codeMirrorInstance = null;
        }
    } catch (error) {
        console.error('Error in closePackageModal:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    showTab('main');
});