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
    cur.execute('SELECT teacher_id, full_name FROM teachers')
    teachers = cur.fetchall()

    cur.execute('SELECT group_id, group_name FROM groups')
    groups = cur.fetchall()

    results = None
    query_conditions = []
    query_params = []

    # Строим SQL запрос в зависимости от выбранных фильтров
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        group_id = request.form.get('group_id')

        if teacher_id:  # Если выбран преподаватель
            query_conditions.append('fg.teacher_id = %s')
            query_params.append(teacher_id)

        if group_id:  # Если выбрана группа
            query_conditions.append('g.group_id = %s')
            query_params.append(group_id)

        # Собираем основной запрос с условиями
        query = """
            SELECT
                t.full_name,
                g.group_name,
                fg.grade,
                COUNT(*) AS grade_count
            FROM final_grades fg
            JOIN students s ON fg.student_id = s.student_id
            JOIN groups g ON s.group_id = g.group_id
            JOIN teachers t ON fg.teacher_id = t.teacher_id
        """

        # Добавляем условия фильтрации, если они есть
        if query_conditions:
            query += ' WHERE ' + ' AND '.join(query_conditions)

        query += ' GROUP BY t.full_name, g.group_name, fg.grade ORDER BY fg.grade'

        # Выполняем запрос с динамическими параметрами
        cur.execute(query, tuple(query_params))
        results = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('index.html', teachers=teachers, groups=groups, results=results)

if __name__ == '__main__':
    app.run(debug=True)
