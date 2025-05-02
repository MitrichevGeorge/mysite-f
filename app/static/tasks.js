// static/tasks.js

// Генерация заготовки кода
function generateCodeTemplate() {
    return `def solve():
    # Ваша реализация здесь
    pass

if __name__ == "__main__":
    result = solve()
    print(result)`;
}

// Загрузка списка тестов через API
function loadTaskTests() {
    fetch(`/api/task/${taskId}/tests`)
        .then(response => {
            if (!response.ok) throw new Error("Ошибка при загрузке тестов");
            return response.json();
        })
        .then(data => {
            console.log("Тесты загружены:", data);
        })
        .catch(error => {
            console.error("Ошибка:", error);
            alert("Не удалось загрузить тесты.");
        });
}

// Загрузка посылок через API
function loadSubmissions() {
    fetch("/api/submissions")
        .then(response => {
            if (!response.ok) throw new Error("Ошибка при загрузке посылок");
            return response.json();
        })
        .then(data => {
            const submissionsList = document.getElementById("submissions-list");
            submissionsList.innerHTML = "";
            const filteredSubmissions = data.filter(submission => submission.task_id === taskId);
            if (filteredSubmissions.length === 0) {
                submissionsList.innerHTML = '<p class="no-submissions">Нет посылок на эту задачу.</p>';
                return;
            }
            filteredSubmissions.forEach((submission, index) => {
                const submissionDiv = document.createElement("div");
                submissionDiv.className = "submission-card";
                let resultsTable = `
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Тест</th>
                                <th>Вердикт</th>
                                <th>Время (мс)</th>
                                <th>Память (МБ)</th>
                                <th>Ошибка</th>
                                <th>Ввод</th>
                                <th>Вывод</th>
                                <th>Ожидаемый вывод</th>
                            </tr>
                        </thead>
                        <tbody>`;
                submission.results.forEach(result => {
                    resultsTable += `
                        <tr>
                            <td>${result.test_num}</td>
                            <td>
                                <span class="verdict-badge ${
                                    result.verdict === 'OK' ? 'accepted' :
                                    result.verdict === 'WA' ? 'wrong' : 'error'
                                }">
                                    ${result.full_verdict}
                                </span>
                            </td>
                            <td>${result.duration}</td>
                            <td>${result.memory}</td>
                            <td>${result.error_info || ''}</td>
                            <td>${result.stdin ? result.stdin.replace(/</g, '&lt;').replace(/>/g, '&gt;') : 'Скрыто'}</td>
                            <td>${result.stdout ? result.stdout.replace(/</g, '&lt;').replace(/>/g, '&gt;') : 'Скрыто'}</td>
                            <td>${result.expected_stdout ? result.expected_stdout.replace(/</g, '&lt;').replace(/>/g, '&gt;') : 'Скрыто'}</td>
                        </tr>`;
                });
                resultsTable += `</tbody></table>`;
                submissionDiv.innerHTML = `
                    <div class="submission-header" onclick="toggleDetails('details-${index}')">
                        <span>Посылка ${index + 1} | Дата: ${submission.timestamp}</span>
                        <span>Баллы: ${submission.score}</span>
                    </div>
                    <div id="details-${index}" class="submission-details" style="display: none;">
                        <h3>Код</h3>
                        <pre>${submission.code ? submission.code.replace(/</g, '&lt;').replace(/>/g, '&gt;') : "Код отсутствует"}</pre>
                        ${resultsTable}
                    </div>
                `;
                submissionsList.appendChild(submissionDiv);
            });
        })
        .catch(error => {
            console.error("Ошибка:", error);
            alert("Не удалось загрузить посылки.");
        });
}

// Сворачивание/разворачивание деталей посылки
function toggleDetails(id) {
    const details = document.getElementById(id);
    details.style.display = details.style.display === "none" ? "block" : "none";
}

// Инициализация
document.addEventListener("DOMContentLoaded", () => {
    const editor = CodeMirror.fromTextArea(document.getElementById("code-input"), {
        value: generateCodeTemplate(),
        mode: "python",
        lineNumbers: true,
        theme: "material",
        indentUnit: 4
    });

    if (typeof taskId !== "undefined") {
        loadTaskTests();
    } else {
        console.error("taskId не определен");
    }
});