import psycopg2

# Настройки подключения к БД
DB_NAME = "student_performance"
DB_USER = "postgres"
DB_PASSWORD = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"

def update_missing_grades():
    """Дополнение недостающих данных для студентов с неудовлетворительными оценками"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Принудительно задаем низкие оценки первому студенту (гарантированно будет 'Неуд')
        cursor.execute("SELECT student_id FROM students ORDER BY student_id LIMIT 1")
        result = cursor.fetchone()
        if result:
            bad_student_id = result[0]

            # Удалим старые оценки для этого студента (если есть)
            cursor.execute("""
                DELETE FROM student_scores
                WHERE student_id = %s
            """, (bad_student_id,))

            # Получим все активности
            cursor.execute("SELECT activity_id, teacher_id FROM point_activities")
            all_activities = cursor.fetchall()

            for activity_id, teacher_id in all_activities:
                cursor.execute("""
                    INSERT INTO student_scores (student_id, activity_id, teacher_id, score)
                    VALUES (%s, %s, %s, %s)
                """, (bad_student_id, activity_id, teacher_id, 30))  # низкий балл

            # Удалим старую итоговую оценку (если была)
            cursor.execute("""
                DELETE FROM final_grades
                WHERE student_id = %s
            """, (bad_student_id,))

            # Пересчитываем итоговую оценку
            cursor.execute("""
            SELECT cp.discipline_id, s.teacher_id, SUM(s.score * pa.weight) / SUM(pa.weight)
            FROM student_scores s
            JOIN point_activities pa ON s.activity_id = pa.activity_id
            JOIN control_points cp ON pa.point_id = cp.point_id
            WHERE s.student_id = %s
            GROUP BY cp.discipline_id, s.teacher_id
        """, (bad_student_id,))
            for discipline_id, teacher_id, total_score in cursor.fetchall():
                grade = (
                    'Отл' if total_score >= 85 else
                    'Хор' if total_score >= 70 else
                    'Удовл' if total_score >= 50 else
                    'Неуд'
                )
                cursor.execute("""
                    INSERT INTO final_grades (student_id, discipline_id, teacher_id, total_score, grade)
                    VALUES (%s, %s, %s, %s, %s)
                """, (bad_student_id, discipline_id, teacher_id, total_score, grade))

        # Обновим некорректные или пустые оценки
        cursor.execute("""
            SELECT fg.student_id, fg.discipline_id, fg.teacher_id, fg.total_score
            FROM final_grades fg
            WHERE fg.grade IS NULL OR fg.grade NOT IN ('Отл', 'Хор', 'Удовл', 'Неуд')
        """)
        rows = cursor.fetchall()

        for row in rows:
            student_id, discipline_id, teacher_id, total_score = row
            if total_score is not None:
                if total_score >= 85:
                    grade = 'Отл'
                elif total_score >= 70:
                    grade = 'Хор'
                elif total_score >= 50:
                    grade = 'Удовл'
                else:
                    grade = 'Неуд'

                cursor.execute("""
                    UPDATE final_grades
                    SET grade = %s
                    WHERE student_id = %s AND discipline_id = %s
                """, (grade, student_id, discipline_id))
            else:
                print(f"Студент {student_id} по дисциплине {discipline_id} не имеет total_score.")

        conn.commit()
        print("Недостающие данные успешно обновлены и 'Неуд' гарантирован!")

    except Exception as e:
        print(f"Ошибка: {e}")
        conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    update_missing_grades()
