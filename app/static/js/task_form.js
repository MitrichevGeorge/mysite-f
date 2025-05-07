const easyMDE = new EasyMDE({
    element: document.getElementById('condition'),
    autoDownloadFontAwesome: true,
    spellChecker: false,
    placeholder: "Введите условие задачи в формате Markdown..."
});

function adjustTextareaHeight(textarea) {
    textarea.style.height = 'auto';
    const lines = textarea.value.split('\n').length;
    const height = Math.max(50, lines * 1.5 * 16);
    textarea.style.height = `${height}px`;
}

function adjustAllTextareaHeights() {
    const textareas = document.querySelectorAll('.test-textarea');
    textareas.forEach(adjustTextareaHeight);
}

function updateCheckboxIds() {
    const checkboxes = document.querySelectorAll('input[name="test_hidden[]"]');
    checkboxes.forEach((checkbox, index) => {
        checkbox.value = index;
        checkbox.id = `chb${index}`;
        checkbox.nextElementSibling.setAttribute('for', `chb${index}`);
    });
}

document.getElementById('add-test-btn').addEventListener('click', () => {
    const tbody = document.getElementById('test-table-body');
    const rowIndex = tbody.children.length;
    const hasSolution = document.querySelector('.generate-test-btn') !== null;
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><textarea name="test_input[]" class="test-textarea" required></textarea></td>
        <td><textarea name="test_output[]" class="test-textarea" required></textarea></td>
        <td class="hidden-column">
            <div class="form-groupcheck">
                <input type="checkbox" name="test_hidden[]" id="chb${rowIndex}" style="display: none;" value="${rowIndex}">
                <label for="chb${rowIndex}"></label>
            </div>
        </td>
        ${hasSolution ? '<td><button type="button" class="generate-test-btn btn btn-primary">Ген.</button></td>' : ''}
        <td><button type="button" class="remove-test-btn">Удалить</button></td>
    `;
    tbody.appendChild(row);
    adjustAllTextareaHeights();
});

document.getElementById('test-table-body').addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-test-btn')) {
        const tbody = document.getElementById('test-table-body');
        if (tbody.children.length > 1) {
            e.target.closest('tr').remove();
            updateCheckboxIds();
            adjustAllTextareaHeights();
        } else {
            alert('Нельзя удалить последний тест.');
        }
    }
});

document.getElementById('test-table-body').addEventListener('input', (e) => {
    if (e.target.classList.contains('test-textarea')) {
        adjustTextareaHeight(e.target);
    }
});

const fileInput = document.getElementById('tests');
const fileNameDisplay = document.getElementById('fileName');
fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        fileNameDisplay.textContent = fileInput.files[0].name;
    } else {
        fileNameDisplay.textContent = 'Не выбран файл';
    }
});

const solutionInput = document.getElementById('solution');
const solutionNameDisplay = document.getElementById('solutionName');
solutionInput.addEventListener('change', () => {
    if (solutionInput.files.length > 0) {
        solutionNameDisplay.textContent = solutionInput.files[0].name;
    } else {
        solutionNameDisplay.textContent = 'Не выбран файл';
    }
});

document.getElementById('tests').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
        const zip = await JSZip.loadAsync(file);
        const tests = [];
        const promises = [];
        zip.forEach((relativePath, zipEntry) => {
            if (zipEntry.name.match(/input\d+\.txt$/)) {
                const testNum = zipEntry.name.match(/\d+/)[0];
                const inputPromise = zipEntry.async('text').then(content => ({
                    testNum,
                    input: content
                }));
                promises.push(inputPromise);
            } else if (zipEntry.name.match(/output\d+\.txt$/)) {
                const testNum = zipEntry.name.match(/\d+/)[0];
                const outputPromise = zipEntry.async('text').then(content => ({
                    testNum,
                    output: content
                }));
                promises.push(outputPromise);
            }
        });
        const results = await Promise.all(promises);
        const inputs = results.filter(r => r.input).sort((a, b) => a.testNum - b.testNum);
        const outputs = results.filter(r => r.output).sort((a, b) => a.testNum - b.testNum);
        for (let i = 0; i < Math.min(inputs.length, outputs.length); i++) {
            if (inputs[i].testNum === outputs[i].testNum) {
                tests.push({
                    input: inputs[i].input,
                    output: outputs[i].output,
                    hidden: false
                });
            }
        }
        const tbody = document.getElementById('test-table-body');
        const hasSolution = document.querySelector('.generate-test-btn') !== null;
        tbody.innerHTML = '';
        tests.forEach((test, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><textarea name="test_input[]" class="test-textarea" required>${test.input}</textarea></td>
                <td><textarea name="test_output[]" class="test-textarea" required>${test.output}</textarea></td>
                <td class="hidden-column">
                    <div class="form-groupcheck">
                        <input type="checkbox" name="test_hidden[]" id="chb${index}" style="display: none;" value="${index}" ${test.hidden ? 'checked' : ''}>
                        <label for="chb${index}"></label>
                    </div>
                </td>
                ${hasSolution ? '<td><button type="button" class="generate-test-btn btn btn-primary">Ген.</button></td>' : ''}
                <td><button type="button" class="remove-test-btn">Удалить</button></td>
            `;
            tbody.appendChild(row);
        });
        adjustAllTextareaHeights();
    } catch (err) {
        alert('Ошибка при обработке ZIP-файла: ' + err.message);
    }
});

document.getElementById('test-table-body').addEventListener('click', async (e) => {
    if (e.target.classList.contains('generate-test-btn')) {
        const button = e.target;
        const row = button.closest('tr');
        const inputTextarea = row.querySelector('textarea[name="test_input[]"]');
        const outputTextarea = row.querySelector('textarea[name="test_output[]"]');
        const taskId = document.getElementById('id').value;

        button.textContent = 'Генерируется...';
        button.disabled = true;

        try {
            const response = await fetch(`/generate_test_output/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ input: inputTextarea.value })
            });
            const result = await response.json();
            if (result.error) {
                alert(`Ошибка: ${result.error}`);
            } else {
                outputTextarea.value = result.output;
                adjustTextareaHeight(outputTextarea);
            }
        } catch (err) {
            alert('Ошибка при генерации вывода: ' + err.message);
        } finally {
            button.textContent = 'Ген.';
            button.disabled = false;
        }
    }
});

document.getElementById('generate-all-btn')?.addEventListener('click', async () => {
    const buttons = document.querySelectorAll('.generate-test-btn');
    for (const button of buttons) {
        const row = button.closest('tr');
        const inputTextarea = row.querySelector('textarea[name="test_input[]"]');
        const outputTextarea = row.querySelector('textarea[name="test_output[]"]');
        const taskId = document.getElementById('id').value;

        if (!inputTextarea.value.trim()) continue;

        button.textContent = 'Генерируется...';
        button.disabled = true;

        try {
            const response = await fetch(`/generate_test_output/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ input: inputTextarea.value })
            });
            const result = await response.json();
            if (result.error) {
                alert(`Ошибка в тесте ${row.rowIndex}: ${result.error}`);
            } else {
                outputTextarea.value = result.output;
                adjustTextareaHeight(outputTextarea);
            }
        } catch (err) {
            alert(`Ошибка в тесте ${row.rowIndex}: ${err.message}`);
        } finally {
            button.textContent = 'Ген.';
            button.disabled = false;
        }
    }
});

window.addEventListener('load', adjustAllTextareaHeights);