import psycopg2
from psycopg2 import sql

# Database connection parameters
DB_NAME = "student_performance"
DB_USER = "postgres"
DB_PASSWORD = "123456"  # Change this to your PostgreSQL password
DB_HOST = "localhost"
DB_PORT = "5432"

def create_database():
    """Create the database and tables"""
    try:
        # Connect to PostgreSQL (to default 'postgres' database to create our DB)
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create database
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        print(f"Database {DB_NAME} created successfully!")
        
        cursor.close()
        conn.close()
        
        # Now connect to our new database to create tables
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id SERIAL PRIMARY KEY,
                group_name VARCHAR(20) NOT NULL,
                faculty VARCHAR(100),
                study_year VARCHAR(20),
                semester VARCHAR(20)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id SERIAL PRIMARY KEY,
                record_book_number VARCHAR(20) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                group_id INTEGER REFERENCES groups(group_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id SERIAL PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                department VARCHAR(100))
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disciplines (
                discipline_id SERIAL PRIMARY KEY,
                discipline_name VARCHAR(100) NOT NULL,
                study_plan VARCHAR(50))
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_points (
                point_id SERIAL PRIMARY KEY,
                point_number INTEGER NOT NULL,
                date DATE NOT NULL,
                discipline_id INTEGER REFERENCES disciplines(discipline_id),
                group_id INTEGER REFERENCES groups(group_id),
                teacher_id INTEGER REFERENCES teachers(teacher_id))
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS point_components (
                component_id SERIAL PRIMARY KEY,
                point_id INTEGER REFERENCES control_points(point_id),
                component_type VARCHAR(50) NOT NULL,  -- 'lecture', 'practice', 'lab', etc.
                weight INTEGER NOT NULL,  -- percentage weight (e.g., 20 for 20%)
                max_score INTEGER NOT NULL)  -- typically 100
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_scores (
                score_id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(student_id),
                point_id INTEGER REFERENCES control_points(point_id),
                component_id INTEGER REFERENCES point_components(component_id),
                score INTEGER NOT NULL,
                weighted_score FLOAT NOT NULL)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS final_grades (
                grade_id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(student_id),
                discipline_id INTEGER REFERENCES disciplines(discipline_id),
                semester VARCHAR(20),
                final_score FLOAT NOT NULL,
                grade VARCHAR(20) NOT NULL,  -- 'Отл', 'Хор', 'Удовл', 'Неуд'
                exam_score INTEGER,
                teacher_id INTEGER REFERENCES teachers(teacher_id),
                date_modified DATE)
        """)
        
        conn.commit()
        print("Tables created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

def insert_sample_data():
    """Insert sample data based on the images"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Insert groups
        cursor.execute("""
            INSERT INTO groups (group_name, faculty, study_year, semester)
            VALUES (%s, %s, %s, %s)
            RETURNING group_id
        """, ('УБ-21', 'Кафедра информационной безопасности', '2022-2023', '5'))
        group_id = cursor.fetchone()[0]
        
        # Insert teachers
        # Маслов А.А. - лекции
        cursor.execute("""
            INSERT INTO teachers (full_name, department)
            VALUES (%s, %s)
            RETURNING teacher_id
        """, ('Маслов А.А.', 'Кафедра информационной безопасности'))
        maslov_id = cursor.fetchone()[0]
        
        # Клименко - практики
        cursor.execute("""
            INSERT INTO teachers (full_name, department)
            VALUES (%s, %s)
            RETURNING teacher_id
        """, ('Клименко', 'Кафедра информационной безопасности'))
        klimenko_id = cursor.fetchone()[0]
        
        # Insert discipline
        cursor.execute("""
            INSERT INTO disciplines (discipline_name, study_plan)
            VALUES (%s, %s)
            RETURNING discipline_id
        """, ('Защита web-сайтов', '10.05.03_2022+t.pix'))
        discipline_id = cursor.fetchone()[0]
        
        # Insert control points (5 points as per requirements)
        # Для лекций указываем Маслова, для практик - Клименко
        points = [
            (1, '2024-09-27', discipline_id, group_id, maslov_id),  # Лекция
            (1, '2024-09-28', discipline_id, group_id, klimenko_id),  # Практика
            (2, '2024-10-25', discipline_id, group_id, maslov_id),
            (2, '2024-10-26', discipline_id, group_id, klimenko_id),
            (3, '2024-11-15', discipline_id, group_id, maslov_id),
            (3, '2024-11-16', discipline_id, group_id, klimenko_id),
            (4, '2024-11-29', discipline_id, group_id, maslov_id),
            (4, '2024-11-30', discipline_id, group_id, klimenko_id),
            (5, '2024-12-06', discipline_id, group_id, maslov_id),
            (5, '2024-12-07', discipline_id, group_id, klimenko_id)
        ]
        
        point_ids = []
        component_ids = {'lecture': [], 'practice': []}
        
        # Создаем контрольные точки и компоненты
        for i, point in enumerate(points):
            point_number, date, discipline_id, group_id, teacher_id = point
            
            # Вставляем контрольную точку
            cursor.execute("""
                INSERT INTO control_points (point_number, date, discipline_id, group_id, teacher_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING point_id
            """, (point_number, date, discipline_id, group_id, teacher_id))
            point_id = cursor.fetchone()[0]
            point_ids.append(point_id)
            
            # Определяем тип компонента (лекция/практика) по четности индекса
            if i % 2 == 0:  # Лекции (четные индексы)
                component_type = 'lecture'
                weight = 40
            else:  # Практики (нечетные индексы)
                component_type = 'practice'
                weight = 60
            
            # Вставляем компонент точки
            cursor.execute("""
                INSERT INTO point_components (point_id, component_type, weight, max_score)
                VALUES (%s, %s, %s, %s)
                RETURNING component_id
            """, (point_id, component_type, weight, 100))
            component_id = cursor.fetchone()[0]
            component_ids[component_type].append(component_id)
        

        
        # Insert ALL students from the images
        students = [
            ('227325', 'Student 1', group_id),
            ('227266', 'Student 2', group_id),
            ('227326', 'Student 3', group_id),
            ('227262', 'Student 4', group_id),
            ('227268', 'Student 5', group_id),
            ('227269', 'Student 6', group_id),
            ('227270', 'Student 7', group_id),
            ('227327', 'Student 8', group_id),
            ('227271', 'Student 9', group_id),
            ('227298', 'Student 10', group_id),
            ('227272', 'Student 11', group_id),
            ('227273', 'Student 12', group_id),
            ('227274', 'Student 13', group_id),
            ('227276', 'Student 14', group_id),
            ('227282', 'Student 15', group_id),
            ('227283', 'Student 16', group_id),
            ('227284', 'Student 17', group_id),
            ('227285', 'Student 18', group_id),
            ('227286', 'Student 19', group_id),
            ('227310', 'Student 20', group_id),
            ('227346', 'Student 21', group_id),
            ('227338', 'Student 22', group_id),
            ('227288', 'Student 23', group_id),
            ('227289', 'Student 24', group_id),
            ('227291', 'Student 25', group_id),
            ('227292', 'Student 26', group_id),
            ('227293', 'Student 27', group_id),
            ('227294', 'Student 28', group_id)
        ]
        
        student_ids = []
        for student in students:
            cursor.execute("""
                INSERT INTO students (record_book_number, full_name, group_id)
                VALUES (%s, %s, %s)
                RETURNING student_id
            """, student)
            student_ids.append(cursor.fetchone()[0])
        
        # Insert scores for all students
        for student_id in student_ids:
            # Оценки за лекции (Маслов)
            for component_id in component_ids['lecture']:
                lecture_score = 60 + (student_id % 40)
                cursor.execute("""
                    INSERT INTO student_scores (student_id, point_id, component_id, score, weighted_score)
                    VALUES (%s, (SELECT point_id FROM point_components WHERE component_id = %s), %s, %s, %s)
                """, (student_id, component_id, component_id, lecture_score, lecture_score * 0.4))
            
            # Оценки за практики (Клименко)
            for component_id in component_ids['practice']:
                practice_score = 70 + (student_id % 30)
                cursor.execute("""
                    INSERT INTO student_scores (student_id, point_id, component_id, score, weighted_score)
                    VALUES (%s, (SELECT point_id FROM point_components WHERE component_id = %s), %s, %s, %s)
                """, (student_id, component_id, component_id, practice_score, practice_score * 0.6))
        
        # Insert final grades (Клименко отвечал за итоговый рейтинг)
        for i, student_id in enumerate(student_ids):
            if i < 10:
                grade = 'Отл'
                final_score = 90 + (i % 5)
            elif i < 20:
                grade = 'Хор'
                final_score = 75 + (i % 10)
            else:
                grade = 'Удовл'
                final_score = 60 + (i % 10)
            
            cursor.execute("""
                INSERT INTO final_grades (student_id, discipline_id, semester, final_score, grade, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_id, discipline_id, '5', final_score, grade, klimenko_id))
        
        conn.commit()
        print("All data inserted successfully with two teachers!")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_database()
    insert_sample_data()