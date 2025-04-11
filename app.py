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
    selected_teacher = ''
    selected_group = ''

    if request.method == 'POST':
        selected_teacher = request.form.get('teacher_id', '')
        selected_group = request.form.get('group_id', '')

        query = """
            SELECT
                t.full_name AS teacher_name,
                g.group_name,
                ss.score AS grade,
                COUNT(*) AS grade_count
            FROM student_scores ss
            JOIN students s ON ss.student_id = s.student_id
            JOIN groups g ON s.group_id = g.group_id
            JOIN teachers t ON ss.teacher_id = t.teacher_id
            JOIN point_activities pa ON ss.activity_id = pa.activity_id
            JOIN activity_types at ON pa.activity_type = at.activity_id
            WHERE 1=1
        """

        params = []

        if selected_teacher:
            query += " AND t.teacher_id = %s"
            params.append(selected_teacher)

        if selected_group:
            query += " AND g.group_id = %s"
            params.append(selected_group)

        query += """
            GROUP BY t.full_name, g.group_name, ss.score, at.activity_name
            ORDER BY t.full_name, g.group_name, at.activity_name, ss.score
        """

        cur.execute(query, tuple(params))
        results = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'index.html', 
        teachers=teachers, 
        groups=groups, 
        results=results,
        selected_teacher=selected_teacher,
        selected_group=selected_group
    )

if __name__ == '__main__':
    app.run(debug=True)