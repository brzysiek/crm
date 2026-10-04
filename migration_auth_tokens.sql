-- Jednorazowe sekrety logowania: kod 2FA wysyłany mailem po haśle i link do resetu hasła.
-- Oba mają ten sam cykl życia (krótki termin, jedno użycie, wysyłka na maila użytkownika),
-- więc siedzą w jednej tabeli i różnią się tylko `kind`.
--
-- W bazie leży wyłącznie SHA-256 sekretu — wyciek tej tabeli nie daje nikomu ani kodu,
-- ani działającego linku do zmiany hasła.

CREATE TABLE IF NOT EXISTS auth_tokens (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    kind        ENUM('login_code', 'password_reset') NOT NULL,
    token_hash  CHAR(64) NOT NULL,
    expires_at  DATETIME NOT NULL,
    used_at     DATETIME DEFAULT NULL,
    attempts    SMALLINT NOT NULL DEFAULT 0,
    ip          VARCHAR(45) DEFAULT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_auth_tokens_lookup (kind, token_hash),
    KEY idx_auth_tokens_user (user_id, kind, created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
