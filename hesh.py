from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()

# Генерируем хеш пароля
hashed_password = bcrypt.generate_password_hash('123456').decode('utf-8')
print("Хеш пароля:", hashed_password)

# Вставьте этот хеш в SQL-запрос
print(f"""
INSERT INTO users (email, password, is_deanery) 
VALUES ('test@example.com', '{hashed_password}', TRUE);
""")