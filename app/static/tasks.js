let visibleTests = [];

// Функция для генерации заготовки кода
function generateCodeTemplate() {
    return `def solve():
    # Ваша реализация здесь
    pass
    if __name__ == "__main__":
        result = solve()
        print(result)`;
}

// Функция для загрузки списка тестов через API
function loadTaskTests() {
    fetch(`/api/task/{{ task_name }}/tests`)
    .then(response => response.json())
    .then(data => {
        visibleTests = data.visible_tests || [];
        loadSubmissions();
    })
    .catch(error => {
        console.error('Ошибка при загрузке списка тестов:', error);
        alert('Произошла ошибка при загрузке списка тестов.');
    });
}

// Функция для загрузки данных о посылках через API
function loadSubmissions() {
    fetch('/api/submissions')
    .then(response => response.json())
    .then(data => {
        const submissionsList = document.getElementById('submissions-list');
        submissionsList.innerHTML = '';
        const filteredSubmissions = data.filter(submission => submission.task_name === '{{ task_name }}');
        filteredSubmissions.forEach((submission, submissionIndex) => {
            const submissionDiv = document.createElement('div');
            submissionDiv.className = 'submission';
            const submissionHeader = document.createElement('div');
            submissionHeader.className = 'submission-header';
            submissionHeader.innerHTML = `
                <span>Посылка ${submissionIndex + 1} | Дата и времени: ${submission.timestamp}</span>
                <span>Баллы: ${submission.score}</span>
                <button>Подробнее</button>
            `;
            submissionHeader.onclick = () => toggleDetails(`details-${submissionIndex}`);
            const submissionDetails = document.createElement('div');
            submissionDetails.id = `details-${submissionIndex}`;
            submissionDetails.className = 'submission-details';
            submissionDetails.style.display = 'none';
            const codeHeader = document.createElement('h3');
            codeHeader.textContent = 'Код';
            const codePre = document.createElement('pre');
            codePre.textContent = submission.code || 'Код отсутствует';
            submissionDetails.appendChild(codeHeader);
            submissionDetails.appendChild(codePre);
            submissionDiv.appendChild(submissionHeader);
            submissionDiv.appendChild(submissionDetails);
            submissionsList.appendChild(submissionDiv);
        });
    })
    .catch(error => {
        console.error('Ошибка при загрузке данных:', error);
        alert('Произошла ошибка при загрузке данных.');
    });
}

// Функции для раскрытия/скрытия деталей
function toggleDetails(id) {
    const details = document.getElementById(id);
    details.style.display = details.style.display === 'none' ? 'block' : 'none';
}

// Инициализация CodeMirror с заготовкой кода
document.addEventListener('DOMContentLoaded', async () => {
    const template = generateCodeTemplate();
    const editor = CodeMirror.fromTextArea(document.getElementById('code-input'), {
        value: template,
        mode: 'python',
        lineNumbers: true,
        theme: 'material',
        indentUnit: 4
    });
    loadTaskTests();
});