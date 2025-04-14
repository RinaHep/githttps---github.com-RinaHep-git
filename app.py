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
    activity_types = None
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

        # Получаем типы занятий для выбранных фильтров
        activity_types_query = """
            SELECT DISTINCT at.activity_name 
            FROM activity_types at
            JOIN point_activities pa ON at.activity_id = pa.activity_type
            JOIN student_scores ss ON pa.activity_id = ss.activity_id
            JOIN students s ON ss.student_id = s.student_id
            JOIN teachers t ON ss.teacher_id = t.teacher_id
            WHERE 1=1
        """
        activity_params = []

        if selected_teacher:
            activity_types_query += " AND t.teacher_id = %s"
            activity_params.append(selected_teacher)

        if selected_group:
            activity_types_query += " AND s.group_id = %s"
            activity_params.append(selected_group)

        activity_types_query += " ORDER BY at.activity_name"

        cur.execute(activity_types_query, tuple(activity_params))
        activity_types = [row[0] for row in cur.fetchall()]

        # Запрос для сводной таблицы оценок
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

        # Запрос для детализированной таблицы (с расчетом итоговой оценки)
        if show_details:
            details_query = """
                WITH lecture_scores AS (
                    SELECT 
                        s.student_id,
                        s.full_name AS student_name,
                        cp.point_number AS checkpoint_id,
                        AVG(CASE WHEN at.activity_name = 'Лекция' THEN ss.score ELSE 0 END) * 0.4 AS lecture_score
                    FROM student_scores ss
                    JOIN students s ON ss.student_id = s.student_id
                    JOIN teachers t ON ss.teacher_id = t.teacher_id
                    JOIN point_activities pa ON ss.activity_id = pa.activity_id
                    JOIN activity_types at ON pa.activity_type = at.activity_id
                    JOIN control_points cp ON pa.point_id = cp.point_id
                    WHERE at.activity_name = 'Лекция'
            """

            details_params = []

            if selected_teacher:
                details_query += " AND t.teacher_id = %s"
                details_params.append(selected_teacher)

            if selected_group:
                details_query += " AND s.group_id = %s"
                details_params.append(selected_group)

            details_query += """
                    GROUP BY s.student_id, s.full_name, cp.point_number
                ),
                practice_scores AS (
                    SELECT 
                        s.student_id,
                        s.full_name AS student_name,
                        cp.point_number AS checkpoint_id,
                        AVG(CASE WHEN at.activity_name = 'Практика' THEN ss.score ELSE 0 END) * 0.6 AS practice_score
                    FROM student_scores ss
                    JOIN students s ON ss.student_id = s.student_id
                    JOIN teachers t ON ss.teacher_id = t.teacher_id
                    JOIN point_activities pa ON ss.activity_id = pa.activity_id
                    JOIN activity_types at ON pa.activity_type = at.activity_id
                    JOIN control_points cp ON pa.point_id = cp.point_id
                    WHERE at.activity_name = 'Практика'
            """

            if selected_teacher:
                details_query += " AND t.teacher_id = %s"
                details_params.append(selected_teacher)

            if selected_group:
                details_query += " AND s.group_id = %s"
                details_params.append(selected_group)

            details_query += """
                    GROUP BY s.student_id, s.full_name, cp.point_number
                ),
                checkpoint_scores AS (
                    SELECT 
                        COALESCE(l.student_id, p.student_id) AS student_id,
                        COALESCE(l.student_name, p.student_name) AS student_name,
                        COALESCE(l.checkpoint_id, p.checkpoint_id) AS checkpoint_id,
                        (COALESCE(l.lecture_score, 0) + COALESCE(p.practice_score, 0)) AS checkpoint_score
                    FROM lecture_scores l
                    FULL OUTER JOIN practice_scores p ON l.student_id = p.student_id AND l.checkpoint_id = p.checkpoint_id
                ),
                final_scores AS (
                    SELECT 
                        student_id,
                        student_name,
                        ROUND(AVG(checkpoint_score))::integer AS final_grade
                    FROM checkpoint_scores
                    GROUP BY student_id, student_name
                )
                SELECT 
                    student_name,
                    final_grade
                FROM final_scores
                ORDER BY student_name
            """

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
        activity_types=activity_types,
        selected_teacher=selected_teacher,
        selected_group=selected_group,
        teacher_name=teacher_name,
        group_name=group_name,
        show_details=show_details
    )

if __name__ == '__main__':
    app.run(debug=True)