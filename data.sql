-- Chronikle: тестовые данные

-- Тестовые пользователи.
-- Пароль для тестовых аккаунтов: password123
-- Это демонстрационные bcrypt-хэши.
INSERT INTO users (username, email, password_hash)
VALUES
    ('artem', 'artem@example.com', '$2b$12$LQv3c1yqBWj5Hh2W8D4w4uJZx7mH4k8XfWQ0lM2x6xQm7wR3k5h2S'),
    ('alex', 'alex@example.com', '$2b$12$LQv3c1yqBWj5Hh2W8D4w4uJZx7mH4k8XfWQ0lM2x6xQm7wR3k5h2S');

-- Папки первого пользователя
INSERT INTO folders (user_id, name)
VALUES
    (1, 'Учёба'),
    (1, 'Фотографии'),
    (1, 'Документы');

-- Вложенные папки первого пользователя
INSERT INTO folders (user_id, parent_folder_id, name)
VALUES
    (1, 1, 'Программирование'),
    (1, 1, 'Базы данных'),
    (1, 2, '2026');

-- Папки второго пользователя
INSERT INTO folders (user_id, name)
VALUES
    (2, 'Работа'),
    (2, 'Личные документы');

-- Материалы первого пользователя
INSERT INTO archive_items
    (user_id, folder_id, title, item_type, description, content, file_path)
VALUES
    (
        1,
        4,
        'Конспект по Python',
        'document',
        'Конспект по основам языка Python',
        NULL,
        '/archive/python_notes.pdf'
    ),
    (
        1,
        5,
        'ER-диаграмма Chronikle',
        'document',
        'Диаграмма базы данных проекта Chronikle',
        NULL,
        '/archive/chronikle_er.png'
    ),
    (
        1,
        6,
        'Поездка летом 2026',
        'photo',
        'Фотография с летней поездки',
        NULL,
        '/archive/trip_2026.jpg'
    ),
    (
        1,
        NULL,
        'Идеи для проекта',
        'note',
        'Черновые идеи и планы развития Chronikle',
        'Добавить поиск, фильтрацию по тегам и возможность создавать вложенные папки.',
        NULL
    ),
    (
        1,
        3,
        'Резюме',
        'document',
        'Актуальная версия резюме',
        NULL,
        '/archive/resume.pdf'
    );

-- Материалы второго пользователя
INSERT INTO archive_items
    (user_id, folder_id, title, item_type, description, content, file_path)
VALUES
    (
        2,
        7,
        'Рабочий план',
        'document',
        'План задач на текущий месяц',
        NULL,
        '/archive/work_plan.pdf'
    ),
    (
        2,
        8,
        'Страховой полис',
        'document',
        'Скан личного документа',
        NULL,
        '/archive/insurance.pdf'
    );

-- Теги первого пользователя
INSERT INTO tags (user_id, name)
VALUES
    (1, 'учёба'),
    (1, 'проект'),
    (1, 'важное'),
    (1, 'фото'),
    (1, 'личное');

-- Теги второго пользователя
INSERT INTO tags (user_id, name)
VALUES
    (2, 'работа'),
    (2, 'документы'),
    (2, 'важное');

-- Связываем материалы первого пользователя с тегами
INSERT INTO item_tags (item_id, tag_id)
VALUES
    (1, 1),
    (1, 2),
    (2, 2),
    (2, 3),
    (3, 4),
    (3, 5),
    (4, 2),
    (4, 3),
    (5, 3),
    (5, 5);

-- Связываем материалы второго пользователя с тегами
INSERT INTO item_tags (item_id, tag_id)
VALUES
    (6, 6),
    (7, 7),
    (7, 8);
