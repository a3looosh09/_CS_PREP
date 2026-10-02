import sqlite3
import re
import secrets
import string

from werkzeug.security import generate_password_hash, check_password_hash


def create_tables():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            subtopic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question_text TEXT NOT NULL,
            max_marks INTEGER NOT NULL,
            expected_concepts TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            question_id INTEGER,
            student_answer TEXT,
            score INTEGER,
            feedback TEXT,
            date_time TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (question_id) REFERENCES questions(question_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            class_code TEXT NOT NULL UNIQUE,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_memberships (
            membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            UNIQUE(class_id, student_id),
            FOREIGN KEY (class_id) REFERENCES classes(class_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

    upgrade_students_table()
    upgrade_teachers_table()
    upgrade_questions_table()
    create_default_admin()


def upgrade_students_table():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(students)")
    columns = [column[1] for column in cursor.fetchall()]

    if "email" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN email TEXT")

    if "password_hash" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")

    if "year_group" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN year_group TEXT")

    if "form_class" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN form_class TEXT")

    if "approval_status" not in columns:
        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'approved'
        """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS unique_student_email
        ON students(email)
        WHERE email IS NOT NULL
    """)

    connection.commit()
    connection.close()


def upgrade_teachers_table():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(teachers)")
    columns = [column[1] for column in cursor.fetchall()]

    if "approval_status" not in columns:
        cursor.execute("""
            ALTER TABLE teachers
            ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'approved'
        """)

    connection.commit()
    connection.close()



def upgrade_questions_table():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(questions)")
    columns = [column[1] for column in cursor.fetchall()]

    if "class_id" not in columns:
        cursor.execute("ALTER TABLE questions ADD COLUMN class_id INTEGER")

    cursor.execute("SELECT class_id FROM classes ORDER BY class_id LIMIT 1")
    first_class = cursor.fetchone()

    if first_class is not None:
        cursor.execute("""
            UPDATE questions
            SET class_id = ?
            WHERE class_id IS NULL
        """, (first_class[0],))

    connection.commit()
    connection.close()

def create_default_admin():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT admin_id
        FROM admins
        WHERE email = ?
    """, ("admin@eischools.ae",))

    existing_admin = cursor.fetchone()

    if existing_admin is None:
        password_hash = generate_password_hash("AdminPassword123")

        cursor.execute("""
            INSERT INTO admins
            (name, email, password_hash)
            VALUES (?, ?, ?)
        """, (
            "CSPrep Administrator",
            "admin@eischools.ae",
            password_hash
        ))

    connection.commit()
    connection.close()


def get_question(class_id, topic, difficulty):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT question_id, topic, question_text
        FROM questions
        WHERE class_id = ?
        AND topic = ?
        AND difficulty = ?
        ORDER BY RANDOM()
        LIMIT 1
    """, (class_id, topic, difficulty))

    question = cursor.fetchone()

    connection.close()

    return question


def get_question_by_id(question_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT question_text, max_marks, expected_concepts
        FROM questions
        WHERE question_id = ?
    """, (question_id,))

    question = cursor.fetchone()

    connection.close()

    return question


def save_attempt(student_id, question_id, student_answer, score, feedback):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO attempts
        (student_id, question_id, student_answer, score, feedback, date_time)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (
        student_id,
        question_id,
        student_answer,
        score,
        feedback
    ))

    connection.commit()
    connection.close()


def get_attempts(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT attempts.score,
               questions.max_marks,
               questions.topic,
               questions.difficulty,
               attempts.date_time
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND attempts.score IS NOT NULL
        ORDER BY attempts.attempt_id DESC
    """, (student_id,))

    attempts = cursor.fetchall()

    connection.close()

    return attempts


def get_statistics(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*),
               SUM(attempts.score),
               SUM(questions.max_marks)
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND attempts.score IS NOT NULL
    """, (student_id,))

    statistics = cursor.fetchone()

    connection.close()

    return statistics


def get_topic_statistics(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT questions.topic,
               SUM(attempts.score),
               SUM(questions.max_marks)
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND attempts.score IS NOT NULL
        GROUP BY questions.topic
        ORDER BY questions.topic
    """, (student_id,))

    topic_statistics = cursor.fetchall()

    connection.close()

    return topic_statistics


def get_weakest_topic(student_id):
    topic_statistics = get_topic_statistics(student_id)

    weakest_topic = None
    weakest_percentage = None

    for topic in topic_statistics:
        if topic[2] and topic[2] > 0:
            percentage = (topic[1] / topic[2]) * 100

            if weakest_percentage is None or percentage < weakest_percentage:
                weakest_topic = topic[0]
                weakest_percentage = percentage

    return weakest_topic, weakest_percentage


def create_student(name, email, password, year_group, form_class):
    if not re.fullmatch(r"m\d{4,5}@students\.eischools\.ae", email):
        return False, "Please use a valid school student email."

    if year_group not in [
        "Year 7",
        "Year 8",
        "Year 9",
        "Year 10",
        "Year 11",
        "Year 12",
        "Year 13"
    ]:
        return False, "Please select a valid year group."

    if form_class not in ["A", "B", "C", "D", "E"]:
        return False, "Please select a valid form class."

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT student_id
        FROM students
        WHERE email = ?
    """, (email,))

    existing_student = cursor.fetchone()

    if existing_student:
        connection.close()
        return False, "An account with this email already exists."

    password_hash = generate_password_hash(password)

    cursor.execute("""
        INSERT INTO students
        (name, email, password_hash, year_group, form_class, approval_status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (
        name,
        email,
        password_hash,
        year_group,
        form_class
    ))

    connection.commit()
    connection.close()

    return True, "Registration submitted successfully."


def get_student_by_email(email):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            email,
            password_hash,
            year_group,
            form_class,
            approval_status
        FROM students
        WHERE email = ?
    """, (email,))

    student = cursor.fetchone()

    connection.close()

    return student


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


def create_teacher(name, email, password):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT teacher_id
        FROM teachers
        WHERE email = ?
    """, (email,))

    existing_teacher = cursor.fetchone()

    if existing_teacher:
        connection.close()
        return False, "A teacher account with this email already exists."

    password_hash = generate_password_hash(password)

    cursor.execute("""
        INSERT INTO teachers
        (name, email, password_hash, approval_status)
        VALUES (?, ?, ?, 'pending')
    """, (
        name,
        email,
        password_hash
    ))

    connection.commit()
    connection.close()

    return True, "Registration submitted successfully."


def get_teacher_by_email(email):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            teacher_id,
            name,
            email,
            password_hash,
            approval_status
        FROM teachers
        WHERE email = ?
    """, (email,))

    teacher = cursor.fetchone()

    connection.close()

    return teacher


def get_admin_by_email(email):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            admin_id,
            name,
            email,
            password_hash
        FROM admins
        WHERE email = ?
    """, (email,))

    admin = cursor.fetchone()

    connection.close()

    return admin


def get_pending_students():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            email,
            year_group,
            form_class
        FROM students
        WHERE approval_status = 'pending'
        ORDER BY name
    """)

    students = cursor.fetchall()

    connection.close()

    return students


def get_pending_teachers():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            teacher_id,
            name,
            email
        FROM teachers
        WHERE approval_status = 'pending'
        ORDER BY name
    """)

    teachers = cursor.fetchall()

    connection.close()

    return teachers


def update_student_approval(student_id, status):
    if status not in ["approved", "rejected"]:
        return False

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE students
        SET approval_status = ?
        WHERE student_id = ?
    """, (status, student_id))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


def update_teacher_approval(teacher_id, status):
    if status not in ["approved", "rejected"]:
        return False

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE teachers
        SET approval_status = ?
        WHERE teacher_id = ?
    """, (status, teacher_id))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


def add_question(class_id, topic, subtopic, difficulty, question_text, max_marks, expected_concepts):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO questions
        (class_id, topic, subtopic, difficulty, question_text, max_marks, expected_concepts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        class_id,
        topic,
        subtopic,
        difficulty,
        question_text,
        max_marks,
        expected_concepts
    ))

    connection.commit()
    connection.close()


def get_all_questions(teacher_id=None, class_id=None):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    query = """
        SELECT
            questions.question_id,
            questions.class_id,
            questions.topic,
            questions.subtopic,
            questions.difficulty,
            questions.question_text,
            questions.max_marks,
            questions.expected_concepts,
            classes.class_name
        FROM questions
        LEFT JOIN classes
        ON questions.class_id = classes.class_id
    """

    conditions = []
    parameters = []

    if teacher_id is not None:
        conditions.append("classes.teacher_id = ?")
        parameters.append(teacher_id)

    if class_id is not None:
        conditions.append("questions.class_id = ?")
        parameters.append(class_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY questions.question_id DESC"

    cursor.execute(query, parameters)
    questions = cursor.fetchall()

    connection.close()

    return questions


def get_question_details(question_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            question_id,
            class_id,
            topic,
            subtopic,
            difficulty,
            question_text,
            max_marks,
            expected_concepts
        FROM questions
        WHERE question_id = ?
    """, (question_id,))

    question = cursor.fetchone()

    connection.close()

    return question


def update_question(
    question_id,
    class_id,
    topic,
    subtopic,
    difficulty,
    question_text,
    max_marks,
    expected_concepts
):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE questions
        SET class_id = ?,
            topic = ?,
            subtopic = ?,
            difficulty = ?,
            question_text = ?,
            max_marks = ?,
            expected_concepts = ?
        WHERE question_id = ?
    """, (
        class_id,
        topic,
        subtopic,
        difficulty,
        question_text,
        max_marks,
        expected_concepts,
        question_id
    ))

    connection.commit()
    connection.close()


def delete_question(question_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM questions
        WHERE question_id = ?
    """, (question_id,))

    connection.commit()
    connection.close()


def get_teacher_statistics(teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM questions
        JOIN classes
        ON questions.class_id = classes.class_id
        WHERE classes.teacher_id = ?
    """, (teacher_id,))
    question_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT class_memberships.student_id)
        FROM class_memberships
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        WHERE classes.teacher_id = ?
        AND class_memberships.status = 'accepted'
    """, (teacher_id,))
    student_count = cursor.fetchone()[0]

    connection.close()

    return question_count, student_count



def get_student_by_id(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            email,
            year_group,
            form_class,
            approval_status
        FROM students
        WHERE student_id = ?
    """, (student_id,))

    student = cursor.fetchone()

    connection.close()

    return student


def get_all_teachers():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT teacher_id, name, email, approval_status
        FROM teachers
        ORDER BY name
    """)

    teachers = cursor.fetchall()

    connection.close()

    return teachers


def delete_student(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("DELETE FROM attempts WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM class_memberships WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


def delete_teacher(teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("SELECT class_id FROM classes WHERE teacher_id = ?", (teacher_id,))
    class_ids = [row[0] for row in cursor.fetchall()]

    for class_id in class_ids:
        cursor.execute("DELETE FROM class_memberships WHERE class_id = ?", (class_id,))

    cursor.execute("DELETE FROM classes WHERE teacher_id = ?", (teacher_id,))
    cursor.execute("DELETE FROM teachers WHERE teacher_id = ?", (teacher_id,))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed

def get_all_students():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT student_id, name, email, year_group, form_class, approval_status
        FROM students
        ORDER BY name
    """)

    students = cursor.fetchall()

    connection.close()

    return students


def get_student_progress(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*),
               SUM(attempts.score),
               SUM(questions.max_marks)
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND attempts.score IS NOT NULL
    """, (student_id,))

    overall = cursor.fetchone()

    cursor.execute("""
        SELECT questions.topic,
               SUM(attempts.score),
               SUM(questions.max_marks)
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND attempts.score IS NOT NULL
        GROUP BY questions.topic
        ORDER BY questions.topic
    """, (student_id,))

    topics = cursor.fetchall()

    cursor.execute("""
        SELECT questions.question_text,
               attempts.score,
               questions.max_marks,
               questions.topic,
               questions.difficulty,
               attempts.date_time
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND attempts.score IS NOT NULL
        ORDER BY attempts.attempt_id DESC
        LIMIT 10
    """, (student_id,))

    recent_attempts = cursor.fetchall()

    connection.close()

    return overall, topics, recent_attempts


def question_has_attempts(question_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM attempts
        WHERE question_id = ?
    """, (question_id,))

    count = cursor.fetchone()[0]

    connection.close()

    return count > 0


def create_class(teacher_id, class_name):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    while True:
        class_code = "".join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

        cursor.execute(
            "SELECT class_id FROM classes WHERE class_code = ?",
            (class_code,)
        )

        if cursor.fetchone() is None:
            break

    cursor.execute("""
        INSERT INTO classes
        (teacher_id, class_name, class_code)
        VALUES (?, ?, ?)
    """, (
        teacher_id,
        class_name,
        class_code
    ))

    connection.commit()
    connection.close()

    return class_code


def get_teacher_classes(teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            classes.class_id,
            classes.class_name,
            classes.class_code,
            COUNT(
                CASE
                    WHEN class_memberships.status = 'accepted' THEN class_memberships.student_id
                END
            ) AS student_count
        FROM classes
        LEFT JOIN class_memberships
        ON classes.class_id = class_memberships.class_id
        WHERE classes.teacher_id = ?
        GROUP BY classes.class_id
        ORDER BY classes.class_name
    """, (teacher_id,))

    classes = cursor.fetchall()

    connection.close()

    return classes


def get_class_for_teacher(class_id, teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT class_id, class_name, class_code
        FROM classes
        WHERE class_id = ?
        AND teacher_id = ?
    """, (class_id, teacher_id))

    class_data = cursor.fetchone()

    connection.close()

    return class_data


def get_class_for_student(class_id, student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            classes.class_id,
            classes.class_name,
            classes.class_code,
            teachers.name,
            class_memberships.status
        FROM class_memberships
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        JOIN teachers
        ON classes.teacher_id = teachers.teacher_id
        WHERE classes.class_id = ?
        AND class_memberships.student_id = ?
        AND class_memberships.status = 'accepted'
    """, (class_id, student_id))

    class_data = cursor.fetchone()

    connection.close()

    return class_data


def get_class_students(class_id, teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.student_id,
            students.name,
            students.email,
            students.year_group,
            students.form_class,
            class_memberships.membership_id
        FROM class_memberships
        JOIN students
        ON class_memberships.student_id = students.student_id
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        WHERE classes.class_id = ?
        AND classes.teacher_id = ?
        AND class_memberships.status = 'accepted'
        ORDER BY students.name
    """, (class_id, teacher_id))

    students = cursor.fetchall()

    connection.close()

    return students


def get_class_pending_requests(class_id, teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            class_memberships.membership_id,
            students.student_id,
            students.name,
            students.email,
            classes.class_name
        FROM class_memberships
        JOIN students
        ON class_memberships.student_id = students.student_id
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        WHERE classes.class_id = ?
        AND classes.teacher_id = ?
        AND class_memberships.status = 'pending'
        ORDER BY students.name
    """, (class_id, teacher_id))

    requests = cursor.fetchall()

    connection.close()

    return requests


def remove_student_from_class(student_id, class_id, teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM class_memberships
        WHERE student_id = ?
        AND class_id = ?
        AND class_id IN (
            SELECT class_id
            FROM classes
            WHERE teacher_id = ?
        )
    """, (student_id, class_id, teacher_id))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


def get_class_progress(student_id, class_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(attempts.score), 0),
            COALESCE(SUM(questions.max_marks), 0)
        FROM attempts
        JOIN questions
        ON attempts.question_id = questions.question_id
        WHERE attempts.student_id = ?
        AND questions.class_id = ?
        AND attempts.score IS NOT NULL
    """, (student_id, class_id))

    progress = cursor.fetchone()

    connection.close()

    return progress


def get_student_classes_with_progress(student_id):
    classes = get_student_classes(student_id)
    result = []

    for class_item in classes:
        attempts, score, possible = get_class_progress(student_id, class_item[0])
        percentage = round((score / possible) * 100) if possible else 0
        result.append(class_item + (attempts, percentage))

    return result


def get_class_by_code(class_code):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT class_id, teacher_id, class_name, class_code
        FROM classes
        WHERE class_code = ?
    """, (class_code,))

    class_data = cursor.fetchone()

    connection.close()

    return class_data


def join_class(class_id, student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT membership_id, status
        FROM class_memberships
        WHERE class_id = ?
        AND student_id = ?
    """, (
        class_id,
        student_id
    ))

    existing = cursor.fetchone()

    if existing:
        connection.close()
        return False, existing[1]

    cursor.execute("""
        INSERT INTO class_memberships
        (class_id, student_id, status)
        VALUES (?, ?, 'pending')
    """, (
        class_id,
        student_id
    ))

    connection.commit()
    connection.close()

    return True, "pending"


def get_student_classes(student_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            classes.class_id,
            classes.class_name,
            classes.class_code,
            teachers.name,
            class_memberships.status
        FROM class_memberships
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        JOIN teachers
        ON classes.teacher_id = teachers.teacher_id
        WHERE class_memberships.student_id = ?
        ORDER BY classes.class_name
    """, (student_id,))

    classes = cursor.fetchall()

    connection.close()

    return classes


def get_pending_requests(teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            class_memberships.membership_id,
            students.student_id,
            students.name,
            students.email,
            classes.class_name
        FROM class_memberships
        JOIN students
        ON class_memberships.student_id = students.student_id
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        WHERE classes.teacher_id = ?
        AND class_memberships.status = 'pending'
        ORDER BY students.name
    """, (teacher_id,))

    requests = cursor.fetchall()

    connection.close()

    return requests


def update_membership_status(membership_id, teacher_id, status):
    if status not in ["accepted", "rejected"]:
        return False

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE class_memberships
        SET status = ?
        WHERE membership_id = ?
        AND class_id IN (
            SELECT class_id
            FROM classes
            WHERE teacher_id = ?
        )
    """, (
        status,
        membership_id,
        teacher_id
    ))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


def get_teacher_students(teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DISTINCT
            students.student_id,
            students.name,
            students.email
        FROM class_memberships
        JOIN students
        ON class_memberships.student_id = students.student_id
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        WHERE classes.teacher_id = ?
        AND class_memberships.status = 'accepted'
        ORDER BY students.name
    """, (teacher_id,))

    students = cursor.fetchall()

    connection.close()

    return students


def remove_student_from_teacher(student_id, teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM class_memberships
        WHERE student_id = ?
        AND class_id IN (
            SELECT class_id
            FROM classes
            WHERE teacher_id = ?
        )
    """, (student_id, teacher_id))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


def teacher_has_student(student_id, teacher_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT 1
        FROM class_memberships
        JOIN classes
        ON class_memberships.class_id = classes.class_id
        WHERE class_memberships.student_id = ?
        AND classes.teacher_id = ?
        AND class_memberships.status = 'accepted'
        LIMIT 1
    """, (student_id, teacher_id))

    result = cursor.fetchone() is not None

    connection.close()

    return result


if __name__ == "__main__":
    create_tables()
    print("Database tables created.")

def get_question_class_id(question_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT class_id
        FROM questions
        WHERE question_id = ?
    """, (question_id,))

    result = cursor.fetchone()

    connection.close()

    return result[0] if result else None


def get_class_topics(class_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DISTINCT topic
        FROM questions
        WHERE class_id = ?
        ORDER BY topic
    """, (class_id,))

    topics = [row[0] for row in cursor.fetchall()]

    connection.close()

    return topics
