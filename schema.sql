-- Chronikle: структура базы данных PostgreSQL

-- Удаляем таблицы при повторном запуске скрипта
DROP TABLE IF EXISTS item_tags CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS archive_items CASCADE;
DROP TABLE IF EXISTS folders CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Пользователи
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Папки
CREATE TABLE folders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    parent_folder_id BIGINT,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_folders_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_folders_parent
        FOREIGN KEY (parent_folder_id)
        REFERENCES folders(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_folder_not_self_parent
        CHECK (parent_folder_id IS NULL OR parent_folder_id <> id)
);

-- Материалы личного архива
CREATE TABLE archive_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    folder_id BIGINT,
    title VARCHAR(200) NOT NULL,
    item_type VARCHAR(20) NOT NULL,
    description TEXT,
    content TEXT,
    file_path TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_archive_items_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_archive_items_folder
        FOREIGN KEY (folder_id)
        REFERENCES folders(id)
        ON DELETE SET NULL,

    CONSTRAINT chk_archive_item_type
        CHECK (item_type IN ('document', 'photo', 'note', 'other'))
);

-- Теги
CREATE TABLE tags (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(50) NOT NULL,

    CONSTRAINT fk_tags_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_tag_user_name
        UNIQUE (user_id, name)
);

-- Связь материалов и тегов (многие-ко-многим)
CREATE TABLE item_tags (
    item_id BIGINT NOT NULL,
    tag_id BIGINT NOT NULL,

    PRIMARY KEY (item_id, tag_id),

    CONSTRAINT fk_item_tags_item
        FOREIGN KEY (item_id)
        REFERENCES archive_items(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_item_tags_tag
        FOREIGN KEY (tag_id)
        REFERENCES tags(id)
        ON DELETE CASCADE
);

-- Индексы для часто используемых связей и поиска
CREATE INDEX idx_folders_user_id ON folders(user_id);
CREATE INDEX idx_folders_parent_folder_id ON folders(parent_folder_id);
CREATE INDEX idx_archive_items_user_id ON archive_items(user_id);
CREATE INDEX idx_archive_items_folder_id ON archive_items(folder_id);
CREATE INDEX idx_archive_items_item_type ON archive_items(item_type);
CREATE INDEX idx_item_tags_tag_id ON item_tags(tag_id);
