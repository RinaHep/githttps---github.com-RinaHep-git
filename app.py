from flask import Flask, render_template, request
import psycopg2

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(
        dbname='student_performance',
        user='postgres',
        password='123456',
        host='localhost',
        port='5432'
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    # Получаем списки для фильтров
    cur.execute('SELECT teacher_id, full_name FROM teachers ORDER BY full_name')
    teachers = cur.fetchall()

    cur.execute('SELECT group_id, group_name FROM groups ORDER BY group_name')
    groups = cur.fetchall()

    cur.execute('SELECT DISTINCT point_number FROM control_points ORDER BY point_number')
    semesters = [(point[0], f"{point[0]} семестр") for point in cur.fetchall()]

    cur.execute('SELECT discipline_id, discipline_name FROM disciplines ORDER BY discipline_name')
    disciplines = cur.fetchall()

    results = None
    summary = None
    activity_types = None
    selected_teacher = ''
    selected_group = ''
    selected_semester = ''
    selected_discipline = ''
    show_details = False
    teacher_name = ''
    group_name = ''
    semester_name = ''
    discipline_name = ''

    if request.method == 'POST':
        selected_teacher = request.form.get('teacher_id', '')
        selected_group = request.form.get('group_id', '')
        selected_semester = request.form.get('semester', '')
        selected_discipline = request.form.get('discipline_id', '')
        show_details = 'show_details' in request.form

        # Получаем имена для отображения
        if selected_teacher:
            cur.execute('SELECT full_name FROM teachers WHERE teacher_id = %s', (selected_teacher,))
            teacher_name = cur.fetchone()[0]
        
        if selected_group:
            cur.execute('SELECT group_name FROM groups WHERE group_id = %s', (selected_group,))
            group_name = cur.fetchone()[0]

        if selected_semester:
            semester_name = f"{selected_semester} семестр"

        if selected_discipline:
            cur.execute('SELECT discipline_name FROM disciplines WHERE discipline_id = %s', (selected_discipline,))
            discipline_name = cur.fetchone()[0]

        # Получаем типы занятий с учетом всех фильтров
        activity_types_query = """
            SELECT DISTINCT at.activity_name 
            FROM activity_types at
            JOIN point_activities pa ON at.activity_id = pa.activity_type
            JOIN student_scores ss ON pa.activity_id = ss.activity_id
            JOIN students s ON ss.student_id = s.student_id
            JOIN teachers t ON ss.teacher_id = t.teacher_id
            JOIN control_points cp ON pa.point_id = cp.point_id
            JOIN disciplines d ON cp.discipline_id = d.discipline_id
            WHERE 1=1
        """
        activity_params = []

        if selected_teacher:
            activity_types_query += " AND t.teacher_id = %s"
            activity_params.append(selected_teacher)

        if selected_group:
            activity_types_query += " AND s.group_id = %s"
            activity_params.append(selected_group)

        if selected_semester:
            activity_types_query += " AND cp.point_number = %s"
            activity_params.append(selected_semester)

        if selected_discipline:
            activity_types_query += " AND d.discipline_id = %s"
            activity_params.append(selected_discipline)

        activity_types_query += " ORDER BY at.activity_name"
        cur.execute(activity_types_query, tuple(activity_params))
        activity_types = [row[0] for row in cur.fetchall()]

        # Упрощенный запрос для расчета итоговых оценок из таблицы final_grades
        final_grades_query = """
            SELECT 
                s.full_name AS student_name,
                ROUND(fg.total_score)::integer AS final_grade,
                fg.grade AS grade_category
            FROM final_grades fg
            JOIN students s ON fg.student_id = s.student_id
            JOIN teachers t ON fg.teacher_id = t.teacher_id
            JOIN disciplines d ON fg.discipline_id = d.discipline_id
            WHERE 1=1
        """
        final_params = []

        if selected_teacher:
            final_grades_query += """
                AND s.student_id IN (
                    SELECT DISTINCT ss.student_id
                    FROM student_scores ss
                    WHERE ss.teacher_id = %s
                )
            """
        final_params.append(selected_teacher)

        if selected_group:
            final_grades_query += " AND s.group_id = %s"
            final_params.append(selected_group)

        if selected_discipline:
            final_grades_query += " AND d.discipline_id = %s"
            final_params.append(selected_discipline)

        # Запрос для сводной таблицы оценок
        summary_query = f"""
                    WITH final_data AS (
            {final_grades_query}
        ),
        grades_grouped AS (
            SELECT 
                CASE
                    WHEN final_grade >= 85 THEN 'Отл'
                    WHEN final_grade >= 75 THEN 'Хор'
                    WHEN final_grade >= 60 THEN 'Удовл'
                    ELSE 'Неудовл'
                END as grade_category
            FROM final_data
        )
        SELECT 
            grade_category,
            COUNT(*) as student_count
        FROM grades_grouped
        GROUP BY grade_category
        ORDER BY 
            CASE 
                WHEN grade_category = 'Отл' THEN 1 
                WHEN grade_category = 'Хор' THEN 2 
                WHEN grade_category = 'Удовл' THEN 3 
                ELSE 4 
            END
        """
        
        cur.execute(summary_query, tuple(final_params))
        summary = cur.fetchall()

        # Запрос для детализированной таблицы
        if show_details:
            details_query = f"""
                SELECT 
                    student_name,
                    final_grade,
                    CASE
                        WHEN final_grade >= 85 THEN 'Отл'
                        WHEN final_grade >= 75 THEN 'Хор'
                        WHEN final_grade >= 60 THEN 'Удовл'
                        ELSE 'Неудовл'
                    END as grade_category
                FROM ({final_grades_query}) AS final_data
                ORDER BY 
                    CAST(SUBSTRING(student_name FROM 'Студент (\d+)') AS INTEGER)
            """
            cur.execute(details_query, tuple(final_params))
            results = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'index.html', 
        teachers=teachers, 
        groups=groups,
        semesters=semesters,
        disciplines=disciplines,
        results=results,
        summary=summary,
        activity_types=activity_types,
        selected_teacher=selected_teacher,
        selected_group=selected_group,
        selected_semester=selected_semester,
        selected_discipline=selected_discipline,
        teacher_name=teacher_name,
        group_name=group_name,
        semester_name=semester_name,
        discipline_name=discipline_name,
        show_details=show_details
    )

if __name__ == '__main__':
    app.run(debug=True)