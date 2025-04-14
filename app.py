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

    # Получаем список преподавателей и групп
    cur.execute('SELECT teacher_id, full_name FROM teachers ORDER BY full_name')
    teachers = cur.fetchall()

    cur.execute('SELECT group_id, group_name FROM groups ORDER BY group_name')
    groups = cur.fetchall()

    results = None
    summary = None
    selected_teacher = ''
    selected_group = ''
    show_details = False
    teacher_name = ''
    group_name = ''

    if request.method == 'POST':
        selected_teacher = request.form.get('teacher_id', '')
        selected_group = request.form.get('group_id', '')
        show_details = 'show_details' in request.form

        # Получаем имя преподавателя и группы для отображения
        if selected_teacher:
            cur.execute('SELECT full_name FROM teachers WHERE teacher_id = %s', (selected_teacher,))
            teacher_name = cur.fetchone()[0]
        
        if selected_group:
            cur.execute('SELECT group_name FROM groups WHERE group_id = %s', (selected_group,))
            group_name = cur.fetchone()[0]

        # Запрос для сводной таблицы оценок (без изменений)
        summary_query = """
            WITH student_avg_scores AS (
                SELECT 
                    s.student_id,
                    AVG(ss.score) as avg_score
                FROM student_scores ss
                JOIN students s ON ss.student_id = s.student_id
                JOIN teachers t ON ss.teacher_id = t.teacher_id
                WHERE 1=1
        """
        summary_params = []

        if selected_teacher:
            summary_query += " AND t.teacher_id = %s"
            summary_params.append(selected_teacher)

        if selected_group:
            summary_query += " AND s.group_id = %s"
            summary_params.append(selected_group)

        summary_query += """
                GROUP BY s.student_id
            ),
            grade_categories AS (
                SELECT 
                    CASE 
                        WHEN avg_score >= 85 THEN 'Отл'
                        WHEN avg_score >= 75 THEN 'Хор'
                        WHEN avg_score >= 60 THEN 'Удовл'
                        ELSE 'Неудовл'
                    END as grade
                FROM student_avg_scores
            )
            SELECT 
                grade,
                COUNT(*) as student_count
            FROM grade_categories
            GROUP BY grade
            ORDER BY CASE grade 
                WHEN 'Отл' THEN 1 
                WHEN 'Хор' THEN 2 
                WHEN 'Удовл' THEN 3 
                ELSE 4 
            END
        """
        
        cur.execute(summary_query, tuple(summary_params))
        summary = cur.fetchall()

        # Запрос для детализированной таблицы (убрали группу)
        if show_details:
            details_query = """
                SELECT
                    s.full_name AS student_name,
                    at.activity_name,
                    ss.score::integer AS grade
                FROM student_scores ss
                JOIN students s ON ss.student_id = s.student_id
                JOIN teachers t ON ss.teacher_id = t.teacher_id
                JOIN point_activities pa ON ss.activity_id = pa.activity_id
                JOIN activity_types at ON pa.activity_type = at.activity_id
                WHERE 1=1
            """

            details_params = []

            if selected_teacher:
                details_query += " AND t.teacher_id = %s"
                details_params.append(selected_teacher)

            if selected_group:
                details_query += " AND s.group_id = %s"
                details_params.append(selected_group)

            details_query += " ORDER BY s.full_name, at.activity_name"

            cur.execute(details_query, tuple(details_params))
            results = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'index.html', 
        teachers=teachers, 
        groups=groups, 
        results=results,
        summary=summary,
        selected_teacher=selected_teacher,
        selected_group=selected_group,
        teacher_name=teacher_name,
        group_name=group_name,
        show_details=show_details
    )

if __name__ == '__main__':
    app.run(debug=True)