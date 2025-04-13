// static/profile/profile_scripts.js
function getShortDateFromWeekAndDay(year, weekNumber, dayOfWeek) {
    const firstDayOfYear = new Date(year, 0, 1);
    const firstMonday = new Date(firstDayOfYear);
    firstMonday.setDate(firstDayOfYear.getDate() + (1 - firstDayOfYear.getDay() + 8) % 7);
    const targetDate = new Date(firstMonday);
    targetDate.setDate(firstMonday.getDate() + (weekNumber - 1) * 7 + (dayOfWeek - 1));
    const day = targetDate.getDate();
    const month = targetDate.toLocaleString('default', { month: 'short' });
    const weekday = targetDate.toLocaleString('default', { weekday: 'short' }).slice(0, 2);
    return `${day} ${month}, ${weekday}`;
}

document.addEventListener('DOMContentLoaded', function () {
    // Календарь
    const heatmap = document.getElementById('heatmap');
    const daysInYear = dailyRequests.length;
    const weeksInYear = 53;
    const minValue = Math.min(...dailyRequests);
    const maxValue = Math.max(...dailyRequests);
    let dayOffset = yearStartOffset || 0;

    for (let day = 0; day < 7; day++) {
        for (let week = 0; week < weeksInYear; week++) {
            const index = week * 7 + day - dayOffset;
            const cell = document.createElement('div');
            if (index < 0 || index >= daysInYear) {
                cell.classList.add('trpcl');
                heatmap.appendChild(cell);
            } else {
                cell.classList.add('cell');
                const value = dailyRequests[index];
                cell.setAttribute('data-count', `${getShortDateFromWeekAndDay(2025, week, day)}: ${value}`);
                cell.setAttribute('num', value);
                const level = normalizeValue(value, minValue, maxValue);
                cell.style.backgroundColor = getColorForLevel(level, isDarkTheme);
                heatmap.appendChild(cell);
            }
        }
    }

    // Обработчик переключателя темы
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', function () {
            const selectedTheme = themeToggle.value;
            fetch('/update-theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ theme: selectedTheme }),
            }).then(response => {
                if (response.ok) {
                    window.location.reload(); // Перезагружаем для применения темы
                } else {
                    alert('Ошибка при изменении темы');
                }
            }).catch(error => {
                console.error('Ошибка:', error);
                alert('Произошла ошибка при изменении темы');
            });
        });
    }

    // Обработчики кнопок настроек
    const changeUsernameBtn = document.getElementById('change-username-btn');
    if (changeUsernameBtn) {
        changeUsernameBtn.addEventListener('click', function () {
            window.location.href = '/change-username';
        });
    }

    const changePasswordBtn = document.getElementById('change-password-btn');
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', function () {
            window.location.href = '/change-password';
        });
    }

    loadSubmissions();
});

function normalizeValue(value, min, max) {
    return (value - min) / (max - min);
}

function getColorForLevel(level, isDarkMode) {
    const lightColors = [
        '#9be9a8', '#40c463', '#30a14e', '#216e39'
    ];
    const darkColors = [
        '#0e4429', '#006d32', '#26a641', '#39d353'
    ];
    if (level > 0) {
        const colors = isDarkMode ? darkColors : lightColors;
        const index = Math.floor(level * (colors.length - 1));
        return colors[index] || colors[0];
    }
    return isDarkMode ? '#2d2d2d' : '#ebedf0';
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    document.getElementById(tabName + '-tab').style.display = 'block';
    document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
}

function toggleDetails(id) {
    const details = document.getElementById(id);
    if (details) {
        details.style.display = details.style.display === 'none' ? 'block' : 'none';
    }
}

function toggleTestDetails(id) {
    const details = document.getElementById(id);
    if (details) {
        details.style.display = details.style.display === 'none' ? 'table-row' : 'none';
    }
}

function loadSubmissions() {
    fetch('/api/submissions')
        .then(response => response.json())
        .then(data => {
            const submissionsList = document.getElementById('submissions-list');
            submissionsList.innerHTML = '';
            data.forEach((submission, submissionIndex) => {
                const submissionDiv = document.createElement('div');
                submissionDiv.className = 'submission-card';
                const submissionHeader = document.createElement('div');
                submissionHeader.className = 'submission-header';
                submissionHeader.innerHTML = `
                    <span>Посылка ${submissionIndex + 1} | Дата и время: ${submission.timestamp}</span>
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
                const resultsHeader = document.createElement('h3');
                resultsHeader.textContent = 'Результаты тестов';
                const resultsTable = document.createElement('table');
                resultsTable.className = 'results-table';
                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr>
                        <th>Номер теста</th>
                        <th>Длительность выполнения</th>
                        <th>Использованная память</th>
                        <th>Вердикт</th>
                        <th>Информация об ошибке</th>
                    </tr>
                `;
                const tbody = document.createElement('tbody');
                submission.results.forEach((test, testIndex) => {
                    const testRow = document.createElement('tr');
                    testRow.className = 'test-row';
                    testRow.innerHTML = `
                        <td>${test.test_num}</td>
                        <td>${test.duration} мс</td>
                        <td>${test.memory} КБ</td>
                        <td>${test.verdict}</td>
                        <td>${test.error_info || '-'}</td>
                    `;
                    testRow.onclick = () => toggleTestDetails(`test-details-${submissionIndex}-${testIndex}`);
                    const testDetailsRow = document.createElement('tr');
                    testDetailsRow.id = `test-details-${submissionIndex}-${testIndex}`;
                    testDetailsRow.className = 'test-details';
                    testDetailsRow.style.display = 'none';
                    testDetailsRow.innerHTML = `
                        <td colspan="5">
                            <p><strong>Вердикт:</strong> ${test.full_verdict}</p>
                            <p><strong>Входные данные:</strong></p>
                            <pre>${test.stdin}</pre>
                            <p><strong>Вывод программы:</strong></p>
                            <pre>${test.stdout}</pre>
                            <p><strong>Ожидаемый вывод:</strong></p>
                            <pre>${test.expected_stdout}</pre>
                            <p><strong>Подробности ошибки:</strong></p>
                            <pre class="warpped">${test.full_error_info || '-'}</pre>
                        </td>
                    `;
                    tbody.appendChild(testRow);
                    tbody.appendChild(testDetailsRow);
                });
                resultsTable.appendChild(thead);
                resultsTable.appendChild(tbody);
                submissionDetails.appendChild(codeHeader);
                submissionDetails.appendChild(codePre);
                submissionDetails.appendChild(resultsHeader);
                submissionDetails.appendChild(resultsTable);
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