import psycopg2
from psycopg2 import sql

# Настройки подключения к БД
DB_NAME = "student_performance"
DB_USER = "postgres"
DB_PASSWORD = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"

def create_database():
    """Создание БД и таблиц с улучшенной структурой"""
    try:
        # Подключение для создания БД
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        print(f"БД {DB_NAME} создана успешно!")
        
        cursor.close()
        conn.close()
        
        # Подключение к новой БД
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Улучшенная структура таблиц
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id SERIAL PRIMARY KEY,
                group_name VARCHAR(20) NOT NULL UNIQUE,
                faculty VARCHAR(100) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id SERIAL PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disciplines (
                discipline_id SERIAL PRIMARY KEY,
                discipline_name VARCHAR(100) NOT NULL,
                total_hours INTEGER NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_points (
                point_id SERIAL PRIMARY KEY,
                point_number INTEGER NOT NULL CHECK (point_number BETWEEN 1 AND 5),
                discipline_id INTEGER REFERENCES disciplines(discipline_id),
                group_id INTEGER REFERENCES groups(group_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_types (
                activity_id SERIAL PRIMARY KEY,
                activity_name VARCHAR(50) NOT NULL UNIQUE,
                default_weight INTEGER NOT NULL CHECK (default_weight BETWEEN 1 AND 100)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS point_activities (
                activity_id SERIAL PRIMARY KEY,
                point_id INTEGER REFERENCES control_points(point_id),
                activity_type INTEGER REFERENCES activity_types(activity_id),
                teacher_id INTEGER REFERENCES teachers(teacher_id),
                weight INTEGER NOT NULL CHECK (weight BETWEEN 1 AND 100),
                max_score INTEGER NOT NULL DEFAULT 100
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id SERIAL PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                group_id INTEGER REFERENCES groups(group_id),
                record_book VARCHAR(20) NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_scores (
                score_id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(student_id),
                activity_id INTEGER REFERENCES point_activities(activity_id),
                teacher_id INTEGER REFERENCES teachers(teacher_id),
                score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
                date_recorded DATE NOT NULL DEFAULT CURRENT_DATE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS final_grades (
                grade_id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(student_id),
                discipline_id INTEGER REFERENCES disciplines(discipline_id),
                teacher_id INTEGER REFERENCES teachers(teacher_id),
                total_score NUMERIC(5,2) NOT NULL CHECK (total_score BETWEEN 0 AND 100),
                grade VARCHAR(10) NOT NULL,
                UNIQUE(student_id, discipline_id)
            )
        """)
        
        conn.commit()
        print("Таблицы созданы успешно!")
        
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

def insert_sample_data():
    """Вставка тестовых данных с учетом всех требований"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # 1. Добавляем группу
        cursor.execute("""
            INSERT INTO groups (group_name, faculty)
            VALUES (%s, %s)
            RETURNING group_id
        """, ('УБ-21', 'Кафедра информационной безопасности'))
        group_id = cursor.fetchone()[0]
        
        # 2. Добавляем преподавателей
        cursor.execute("""
            INSERT INTO teachers (full_name, department)
            VALUES (%s, %s)
            RETURNING teacher_id
        """, ('Маслов А.А.', 'Кафедра информационной безопасности'))
        maslov_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO teachers (full_name, department)
            VALUES (%s, %s)
            RETURNING teacher_id
        """, ('Клименко', 'Кафедра информационной безопасности'))
        klimenko_id = cursor.fetchone()[0]
        
        # 3. Добавляем дисциплину
        cursor.execute("""
            INSERT INTO disciplines (discipline_name, total_hours)
            VALUES (%s, %s)
            RETURNING discipline_id
        """, ('Защита web-сайтов', 144))
        discipline_id = cursor.fetchone()[0]
        
        # 4. Добавляем типы активностей
        activities = [
            ('Лекция', 20),  # 20% веса
            ('Практика', 80)  # 80% веса
        ]
        
        for name, weight in activities:
            cursor.execute("""
                INSERT INTO activity_types (activity_name, default_weight)
                VALUES (%s, %s)
            """, (name, weight))
        
        # 5. Создаем 5 контрольных точек
        for point_num in range(1, 6):
            cursor.execute("""
                INSERT INTO control_points (point_number, discipline_id, group_id)
                VALUES (%s, %s, %s)
                RETURNING point_id
            """, (point_num, discipline_id, group_id))
            point_id = cursor.fetchone()[0]
            
            # Для каждой точки добавляем лекцию (Маслов) и практику (Клименко)
            cursor.execute("""
                INSERT INTO point_activities 
                (point_id, activity_type, teacher_id, weight, max_score)
                VALUES (
                    %s, 
                    (SELECT activity_id FROM activity_types WHERE activity_name = 'Лекция'), 
                    %s, 
                    (SELECT default_weight FROM activity_types WHERE activity_name = 'Лекция'), 
                    100
                )
            """, (point_id, maslov_id))
            
            cursor.execute("""
                INSERT INTO point_activities 
                (point_id, activity_type, teacher_id, weight, max_score)
                VALUES (
                    %s, 
                    (SELECT activity_id FROM activity_types WHERE activity_name = 'Практика'), 
                    %s, 
                    (SELECT default_weight FROM activity_types WHERE activity_name = 'Практика'), 
                    100
                )
            """, (point_id, klimenko_id))
        
        # 6. Добавляем 28 студентов
        students = []
        for i in range(1, 29):
            students.append((f'Студент {i}', group_id, f'227{200+i}'))
        
        student_ids = []
        for student in students:
            cursor.execute("""
                INSERT INTO students (full_name, group_id, record_book)
                VALUES (%s, %s, %s)
                RETURNING student_id
            """, student)
            student_ids.append(cursor.fetchone()[0])
        
        # 7. Добавляем оценки для всех студентов с указанием преподавателя
        cursor.execute("""
            SELECT pa.activity_id, pa.teacher_id, at.activity_name 
            FROM point_activities pa
            JOIN activity_types at ON pa.activity_type = at.activity_id
        """)
        activities = cursor.fetchall()
        
        for student_id in student_ids:
            for activity_id, teacher_id, activity_name in activities:
                # Генерируем оценки в зависимости от типа активности
                if activity_name == 'Лекция':
                    # Оценки за лекции (Маслов) - более высокие
                    score = 70 + (student_id % 30)  # 70-100 баллов
                else:
                    # Оценки за практики (Клименко) - более строгие
                    score = 50 + (student_id % 45)  # 50-95 баллов
                
                # Сохраняем оценку с указанием преподавателя
                cursor.execute("""
                    INSERT INTO student_scores 
                    (student_id, activity_id, teacher_id, score)
                    VALUES (%s, %s, %s, %s)
                """, (student_id, activity_id, teacher_id, score))
        
        # 8. Рассчитываем итоговые оценки (выставляет Маслов)
        for student_id in student_ids:
            # Считаем средневзвешенную оценку по всем активностям
            cursor.execute("""
                SELECT SUM(s.score * pa.weight)/SUM(pa.weight)
                FROM student_scores s
                JOIN point_activities pa ON s.activity_id = pa.activity_id
                WHERE s.student_id = %s
            """, (student_id,))
            total_score = cursor.fetchone()[0]
            
            # Определяем оценку
            if total_score >= 85:
                grade = 'Отл'
            elif total_score >= 70:
                grade = 'Хор'
            elif total_score >= 50:
                grade = 'Удовл'
            else:
                grade = 'Неуд'
            
            # Записываем итоговую оценку (выставляет Маслов)
            cursor.execute("""
                INSERT INTO final_grades 
                (student_id, discipline_id, teacher_id, total_score, grade)
                VALUES (%s, %s, %s, %s, %s)
            """, (student_id, discipline_id, maslov_id, total_score, grade))
        
        conn.commit()
        print("Тестовые данные успешно добавлены для 28 студентов!")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_database()
    insert_sample_data()