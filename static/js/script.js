// Обновление списка баз данных
function refreshDatabases() {
    fetch('/api/databases')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Перезагружаем страницу
                window.location.reload();
            }
        });
}

// Скачивание базы данных
function downloadDatabase(dbName) {
    window.location.href = `/api/download/${dbName}`;
}

// Создание бэкапа
function createBackup(dbName) {
    fetch(`/api/backup/${dbName}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Бэкап создан успешно!');
            } else {
                alert('Ошибка при создании бэкапа: ' + data.error);
            }
        });
}

// Поиск по базе данных
function searchDatabase() {
    const query = document.getElementById('searchInput').value;
    const dbName = window.location.search.split('=')[1];
    
    fetch(`/api/search/${dbName}?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTable(data.results);
            }
        });
}

// Обновление таблицы
function updateTable(data) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    
    for (const [key, value] of Object.entries(data)) {
        const row = document.createElement('tr');
        row.id = `row-${key}`;
        row.innerHTML = `
            <td>
                <input type="text" class="form-control form-control-sm key-input" 
                       value="${key}" data-original="${key}">
            </td>
            <td>
                <textarea class="form-control value-input" rows="2">${JSON.stringify(value, null, 2)}</textarea>
            </td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewRecord('${key}')">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRecord('${key}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    }
}

// Просмотр записи
function viewRecord(key) {
    const dbName = window.location.search.split('=')[1];
    window.location.href = `/view/${dbName}/${key}`;
}

// Добавление записи
function addRecord() {
    const dbName = window.location.search.split('=')[1];
    window.location.href = `/add/${dbName}`;
}

// Удаление записи
function deleteRecord(key) {
    if (!confirm('Вы уверены, что хотите удалить эту запись?')) {
        return;
    }
    
    const dbName = window.location.search.split('=')[1];
    
    fetch(`/api/database/${dbName}/record/${key}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById(`row-${key}`).remove();
            } else {
                alert('Ошибка при удалении: ' + data.error);
            }
        });
}

// Сохранение изменений
function saveChanges() {
    const dbName = window.location.search.split('=')[1];
    const rows = document.querySelectorAll('#tableBody tr');
    const updates = {};
    
    rows.forEach(row => {
        const keyInput = row.querySelector('.key-input');
        const valueInput = row.querySelector('.value-input');
        const originalKey = keyInput.dataset.original;
        const newKey = keyInput.value;
        
        try {
            const newValue = JSON.parse(valueInput.value);
            
            if (originalKey === newKey) {
                // Обновление существующей записи
                updates[newKey] = newValue;
            } else {
                // Изменение ключа - удалить старый, добавить новый
                updates[originalKey] = null; // пометить для удаления
                updates[newKey] = newValue;
            }
        } catch (e) {
            alert(`Ошибка в записи ${originalKey}: неверный JSON формат`);
            return;
        }
    });
    
    // Сначала загружаем текущие данные
    fetch(`/api/database/${dbName}`)
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                throw new Error('Ошибка загрузки данных');
            }
            
            const currentData = data.data;
            
            // Применяем изменения
            Object.entries(updates).forEach(([key, value]) => {
                if (value === null) {
                    // Удаляем запись
                    delete currentData[key];
                } else {
                    // Добавляем/обновляем запись
                    currentData[key] = value;
                }
            });
            
            // Сохраняем обновленные данные
            return fetch(`/api/database/${dbName}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentData)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Изменения сохранены успешно!');
                window.location.reload();
            } else {
                alert('Ошибка при сохранении: ' + data.error);
            }
        })
        .catch(error => {
            alert('Ошибка: ' + error.message);
        });
}

// Обработка загрузки файла
document.getElementById('uploadForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('База данных загружена успешно!');
            window.location.reload();
        } else {
            alert('Ошибка при загрузке: ' + data.error);
        }
    });
});

// Отслеживание изменений
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('.key-input, .value-input');
    
    inputs.forEach(input => {
        const originalValue = input.value;
        
        input.addEventListener('input', function() {
            const indicator = this.closest('tr').querySelector('.change-indicator');
            if (this.value !== originalValue) {
                indicator.style.display = 'inline-block';
            } else {
                indicator.style.display = 'none';
            }
        });
    });
});
