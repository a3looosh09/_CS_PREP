from flask import Flask, render_template, request, redirect, url_for, session

from database import (
    create_tables,
    create_student,
    get_student_by_email,
    create_teacher,
    get_teacher_by_email,
    get_admin_by_email,
    verify_password,
    get_pending_students,
    get_pending_teachers,
    update_student_approval,
    update_teacher_approval,
    get_teacher_statistics,
    get_teacher_classes,
    get_pending_requests,
    get_teacher_students,
    create_class,
    update_membership_status,
    get_all_students,
    get_student_by_id,
    get_all_teachers,
    delete_student,
    delete_teacher,
    get_student_progress,
    get_all_questions,
    add_question,
    get_question_details,
    update_question,
    delete_question,
    question_has_attempts,
    get_question,
    get_question_by_id,
    save_attempt,
    get_attempts,
    get_statistics,
    get_topic_statistics,
    get_weakest_topic,
    get_student_classes,
    get_class_by_code,
    join_class,
    remove_student_from_teacher,
    teacher_has_student,
    get_class_for_teacher,
    get_class_for_student,
    get_class_students,
    get_class_pending_requests,
    remove_student_from_class,
    get_student_classes_with_progress,
    get_class_progress,
    get_question_class_id,
    get_class_topics
)

from ai import grade_answer


app = Flask(__name__)
app.secret_key = "cs-prep-development-key"

create_tables()


@app.route("/")
def home():
    if "student_id" not in session:
        return redirect(url_for("login"))

    classes = get_student_classes_with_progress(session["student_id"])

    return render_template(
        "index.html",
        student_name=session["student_name"],
        classes=classes
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        year_group = request.form["year_group"]
        form_class = request.form["form_class"]

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="Please complete all required fields."
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters."
            )

        success, message = create_student(
            name,
            email,
            password,
            year_group,
            form_class
        )

        if not success:
            return render_template(
                "register.html",
                error=message
            )

        return render_template(
            "registration_success.html",
            account_type="student"
        )

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        student = get_student_by_email(email)

        if student is None:
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        if not verify_password(password, student[3]):
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        if student[6] == "pending":
            return render_template(
                "login.html",
                error="Your account is awaiting administrator approval."
            )

        if student[6] == "rejected":
            return render_template(
                "login.html",
                error="Your registration was not approved. Please contact your administrator."
            )

        session.clear()
        session["student_id"] = student[0]
        session["student_name"] = student[1]

        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        teacher = get_teacher_by_email(email)

        if teacher is None:
            return render_template(
                "teacher_login.html",
                error="Invalid email or password."
            )

        if not verify_password(password, teacher[3]):
            return render_template(
                "teacher_login.html",
                error="Invalid email or password."
            )

        if teacher[4] == "pending":
            return render_template(
                "teacher_login.html",
                error="Your account is awaiting administrator approval."
            )

        if teacher[4] == "rejected":
            return render_template(
                "teacher_login.html",
                error="Your registration was not approved. Please contact your administrator."
            )

        session.clear()
        session["teacher_id"] = teacher[0]
        session["teacher_name"] = teacher[1]

        return redirect(url_for("teacher_dashboard"))

    return render_template("teacher_login.html")


@app.route("/teacher/logout")
def teacher_logout():
    session.clear()
    return redirect(url_for("teacher_login"))


@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not name or not email or not password:
            return render_template(
                "teacher_register.html",
                error="Please complete all required fields."
            )

        if password != confirm_password:
            return render_template(
                "teacher_register.html",
                error="Passwords do not match."
            )

        if len(password) < 8:
            return render_template(
                "teacher_register.html",
                error="Password must be at least 8 characters."
            )

        success, message = create_teacher(
            name,
            email,
            password
        )

        if not success:
            return render_template(
                "teacher_register.html",
                error=message
            )

        return render_template(
            "registration_success.html",
            account_type="teacher"
        )

    return render_template("teacher_register.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        admin = get_admin_by_email(email)

        if admin is None:
            return render_template(
                "admin_login.html",
                error="Invalid email or password."
            )

        if not verify_password(password, admin[3]):
            return render_template(
                "admin_login.html",
                error="Invalid email or password."
            )

        session.clear()
        session["admin_id"] = admin[0]
        session["admin_name"] = admin[1]

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    pending_students = get_pending_students()
    pending_teachers = get_pending_teachers()
    all_students = get_all_students()
    all_teachers = get_all_teachers()

    return render_template(
        "admin_dashboard.html",
        admin_name=session["admin_name"],
        pending_students=pending_students,
        pending_teachers=pending_teachers,
        all_students=all_students,
        all_teachers=all_teachers
    )


@app.route("/admin/students/<int:student_id>/approve", methods=["POST"])
def approve_student(student_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    update_student_approval(student_id, "approved")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/students/<int:student_id>/reject", methods=["POST"])
def reject_student(student_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    update_student_approval(student_id, "rejected")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/teachers/<int:teacher_id>/approve", methods=["POST"])
def approve_teacher(teacher_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    update_teacher_approval(teacher_id, "approved")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/teachers/<int:teacher_id>/reject", methods=["POST"])
def reject_teacher(teacher_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    update_teacher_approval(teacher_id, "rejected")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/students/approve-selected", methods=["POST"])
def approve_selected_students():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    student_ids = request.form.getlist("student_ids")

    for student_id in student_ids:
        update_student_approval(int(student_id), "approved")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/teachers/approve-selected", methods=["POST"])
def approve_selected_teachers():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    teacher_ids = request.form.getlist("teacher_ids")

    for teacher_id in teacher_ids:
        update_teacher_approval(int(teacher_id), "approved")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/students/<int:student_id>/delete", methods=["POST"])
def admin_delete_student(student_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    delete_student(student_id)

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/teachers/<int:teacher_id>/delete", methods=["POST"])
def admin_delete_teacher(teacher_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    delete_teacher(teacher_id)

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/teacher")
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    question_count, student_count = get_teacher_statistics(session["teacher_id"])
    classes = get_teacher_classes(session["teacher_id"])
    pending_requests = get_pending_requests(session["teacher_id"])

    return render_template(
        "teacher_dashboard.html",
        teacher_name=session["teacher_name"],
        question_count=question_count,
        student_count=student_count,
        classes=classes,
        pending_requests=pending_requests
    )

@app.route("/teacher/questions")
def teacher_questions():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    questions = get_all_questions(teacher_id=session["teacher_id"])

    return render_template(
        "teacher_questions.html",
        questions=questions
    )

@app.route("/teacher/questions/add", methods=["GET", "POST"])
def add_teacher_question():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    classes = get_teacher_classes(session["teacher_id"])
    selected_class_id = request.args.get("class_id", type=int)
    topics = get_class_topics(selected_class_id) if selected_class_id else []

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        topic = request.form["topic"].strip()
        subtopic = request.form["subtopic"].strip()
        difficulty = request.form["difficulty"]
        question_text = request.form["question_text"].strip()
        max_marks = request.form["max_marks"]
        expected_concepts = request.form["expected_concepts"].strip()

        if class_id is None or get_class_for_teacher(class_id, session["teacher_id"]) is None:
            return render_template(
                "teacher_add_question.html",
                classes=classes,
                selected_class_id=class_id,
                error="Please select one of your classes."
            )

        if not topic or not subtopic or not question_text or not expected_concepts:
            return render_template(
                "teacher_add_question.html",
                classes=classes,
                selected_class_id=class_id,
                error="Please complete all fields."
            )

        try:
            max_marks = int(max_marks)
        except ValueError:
            return render_template(
                "teacher_add_question.html",
                classes=classes,
                selected_class_id=class_id,
                error="Maximum marks must be a number."
            )

        if max_marks <= 0:
            return render_template(
                "teacher_add_question.html",
                classes=classes,
                selected_class_id=class_id,
                error="Maximum marks must be greater than zero."
            )

        add_question(
            class_id,
            topic,
            subtopic,
            difficulty,
            question_text,
            max_marks,
            expected_concepts
        )

        return redirect(url_for("teacher_class", class_id=class_id))

    return render_template(
        "teacher_add_question.html",
        classes=classes,
        selected_class_id=selected_class_id
    )

@app.route("/teacher/questions/edit/<int:question_id>", methods=["GET", "POST"])
def edit_teacher_question(question_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    question = get_question_details(question_id)

    if question is None:
        return "Question not found", 404

    current_class = get_class_for_teacher(question[1], session["teacher_id"])

    if current_class is None:
        return "Question not found", 404

    classes = get_teacher_classes(session["teacher_id"])

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        topic = request.form["topic"].strip()
        subtopic = request.form["subtopic"].strip()
        difficulty = request.form["difficulty"]
        question_text = request.form["question_text"].strip()
        max_marks = request.form["max_marks"]
        expected_concepts = request.form["expected_concepts"].strip()

        if class_id is None or get_class_for_teacher(class_id, session["teacher_id"]) is None:
            return render_template(
                "teacher_edit_question.html",
                question=question,
                classes=classes,
                error="Please select one of your classes."
            )

        try:
            max_marks = int(max_marks)
        except ValueError:
            return render_template(
                "teacher_edit_question.html",
                question=question,
                classes=classes,
                error="Maximum marks must be a number."
            )

        if max_marks <= 0:
            return render_template(
                "teacher_edit_question.html",
                question=question,
                classes=classes,
                error="Maximum marks must be greater than zero."
            )

        update_question(
            question_id,
            class_id,
            topic,
            subtopic,
            difficulty,
            question_text,
            max_marks,
            expected_concepts
        )

        return redirect(url_for("teacher_class", class_id=class_id))

    return render_template(
        "teacher_edit_question.html",
        question=question,
        classes=classes
    )

@app.route("/teacher/questions/delete/<int:question_id>", methods=["POST"])
def delete_teacher_question(question_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    question = get_question_details(question_id)

    if question is None or get_class_for_teacher(question[1], session["teacher_id"]) is None:
        return "Question not found", 404

    if question_has_attempts(question_id):
        return render_template(
            "teacher_delete_error.html"
        )

    class_id = question[1]
    delete_question(question_id)

    return redirect(url_for("teacher_class", class_id=class_id))

@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "student_id" not in session:
        return redirect(url_for("login"))

    student_id = session["student_id"]
    classes = get_student_classes_with_progress(student_id)
    selected_class_id = request.args.get("class_id", type=int)
    topics = get_class_topics(selected_class_id) if selected_class_id else []

    if request.method == "POST":
        selected_class_id = request.form.get("class_id", type=int)
        topics = get_class_topics(selected_class_id) if selected_class_id else []
        topic = request.form["topic"]
        difficulty = request.form["difficulty"]

        if selected_class_id is None or get_class_for_student(selected_class_id, student_id) is None:
            return render_template(
                "practice.html",
                classes=classes,
                selected_class_id=selected_class_id,
                topics=topics,
                error="Please select one of your classes."
            )

        question_data = get_question(selected_class_id, topic, difficulty)

        if question_data is None:
            return render_template(
                "practice.html",
                classes=classes,
                selected_class_id=selected_class_id,
                topics=topics,
                error="No questions were found for that class, topic, and difficulty."
            )

        question_id = question_data[0]
        question = question_data[2]

        return render_template(
            "question.html",
            topic=topic,
            difficulty=difficulty,
            question=question,
            question_id=question_id,
            class_id=selected_class_id
        )

    return render_template(
        "practice.html",
        classes=classes,
        selected_class_id=selected_class_id,
        topics=topics
    )

@app.route("/practice/question/<int:question_id>")
def student_question(question_id):
    if "student_id" not in session:
        return redirect(url_for("login"))

    question = get_question_details(question_id)

    if question is None:
        return "Question not found", 404

    class_id = question[1]

    if get_class_for_student(class_id, session["student_id"]) is None:
        return "Question not found", 404

    return render_template(
        "question.html",
        topic=question[2],
        difficulty=question[4],
        question=question[5],
        question_id=question[0],
        class_id=class_id
    )


@app.route("/submit", methods=["POST"])
def submit():
    if "student_id" not in session:
        return redirect(url_for("login"))

    answer = request.form["answer"]
    topic = request.form["topic"]
    question = request.form["question"]
    question_id = request.form["question_id"]
    class_id = request.form.get("class_id", type=int)

    question_data = get_question_by_id(question_id)

    if question_data is None:
        return "Question not found", 404

    question_text, max_marks, expected_concepts = question_data

    actual_class_id = get_question_class_id(question_id)

    if class_id is None or actual_class_id != class_id or get_class_for_student(class_id, session["student_id"]) is None:
        return "Question not available for this class", 403

    result = grade_answer(
        question_text,
        max_marks,
        expected_concepts,
        answer
    )

    score = result["score"]
    feedback = result["feedback"]

    save_attempt(
        session["student_id"],
        question_id,
        answer,
        score,
        feedback
    )

    return render_template(
        "results.html",
        topic=topic,
        question=question,
        score=score,
        max_marks=max_marks,
        feedback=feedback,
        mark_scheme=expected_concepts,
        class_id=class_id
    )


@app.route("/teacher/student/<int:student_id>")
def teacher_student_progress(student_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    if not teacher_has_student(student_id, session["teacher_id"]):
        return "Student not found", 404

    student = get_student_by_id(student_id)

    if student is None:
        return "Student not found", 404

    overall, topics, recent_attempts = get_student_progress(student_id)

    total_attempts = overall[0] or 0
    total_score = overall[1] or 0
    total_possible = overall[2] or 0

    if total_possible > 0:
        overall_percentage = round(
            (total_score / total_possible) * 100
        )
    else:
        overall_percentage = 0

    topic_performance = []

    weakest_topic = None
    weakest_percentage = None

    for topic in topics:
        percentage = round(
            (topic[1] / topic[2]) * 100
        )

        topic_performance.append({
            "topic": topic[0],
            "percentage": percentage
        })

        if weakest_percentage is None or percentage < weakest_percentage:
            weakest_topic = topic[0]
            weakest_percentage = percentage

    return render_template(
        "teacher_student_progress.html",
        student=student,
        total_attempts=total_attempts,
        overall_percentage=overall_percentage,
        topic_performance=topic_performance,
        weakest_topic=weakest_topic,
        weakest_percentage=weakest_percentage,
        recent_attempts=recent_attempts
    )


@app.route("/profile")
def student_profile():
    if "student_id" not in session:
        return redirect(url_for("login"))

    student = get_student_by_id(session["student_id"])

    if student is None:
        session.clear()
        return redirect(url_for("login"))

    classes = get_student_classes(session["student_id"])

    return render_template(
        "profile.html",
        student=student,
        classes=classes
    )


@app.route("/progress")
def progress():
    if "student_id" not in session:
        return redirect(url_for("login"))

    student_id = session["student_id"]

    attempts = get_attempts(student_id)
    statistics = get_statistics(student_id)
    topic_statistics = get_topic_statistics(student_id)
    weakest_topic, weakest_percentage = get_weakest_topic(student_id)

    total_attempts = statistics[0]
    total_score = statistics[1] or 0
    total_possible = statistics[2] or 0

    if total_possible > 0:
        average_percentage = round(
            (total_score / total_possible) * 100
        )
    else:
        average_percentage = 0

    topic_performance = []

    for topic in topic_statistics:
        percentage = round(
            (topic[1] / topic[2]) * 100
        )

        topic_performance.append({
            "topic": topic[0],
            "percentage": percentage
        })

    return render_template(
        "progress.html",
        attempts=attempts,
        total_attempts=total_attempts,
        average_percentage=average_percentage,
        topic_performance=topic_performance,
        weakest_topic=weakest_topic,
        weakest_percentage=weakest_percentage
    )


@app.route("/teacher/classes/create", methods=["POST"])
def create_teacher_class():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    class_name = request.form["class_name"].strip()

    if not class_name:
        return redirect(url_for("teacher_dashboard"))

    create_class(
        session["teacher_id"],
        class_name
    )

    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/requests/<int:membership_id>/accept", methods=["POST"])
def accept_student_request(membership_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    update_membership_status(
        membership_id,
        session["teacher_id"],
        "accepted"
    )

    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/requests/<int:membership_id>/reject", methods=["POST"])
def reject_student_request(membership_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    update_membership_status(
        membership_id,
        session["teacher_id"],
        "rejected"
    )

    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/classes/<int:class_id>")
def teacher_class(class_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    class_data = get_class_for_teacher(class_id, session["teacher_id"])

    if class_data is None:
        return "Class not found", 404

    students = get_class_students(class_id, session["teacher_id"])
    pending_requests = get_class_pending_requests(class_id, session["teacher_id"])
    questions = get_all_questions(class_id=class_id)

    return render_template(
        "teacher_class.html",
        class_data=class_data,
        students=students,
        pending_requests=pending_requests,
        questions=questions
    )


@app.route("/teacher/classes/<int:class_id>/students/<int:student_id>/remove", methods=["POST"])
def teacher_remove_student_from_class(class_id, student_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    remove_student_from_class(
        student_id,
        class_id,
        session["teacher_id"]
    )

    return redirect(url_for("teacher_class", class_id=class_id))


@app.route("/classes")
def student_classes():
    if "student_id" not in session:
        return redirect(url_for("login"))

    classes = get_student_classes_with_progress(
        session["student_id"]
    )

    return render_template(
        "classes.html",
        classes=classes
    )


@app.route("/classes/<int:class_id>")
def student_class(class_id):
    if "student_id" not in session:
        return redirect(url_for("login"))

    class_data = get_class_for_student(class_id, session["student_id"])

    if class_data is None:
        return "Class not found", 404

    questions = get_all_questions(class_id=class_id)
    attempts, score, possible = get_class_progress(session["student_id"], class_id)
    percentage = round((score / possible) * 100) if possible else 0

    return render_template(
        "student_class.html",
        class_data=class_data,
        questions=questions,
        attempts=attempts,
        percentage=percentage
    )


@app.route("/classes/join", methods=["POST"])
def student_join_class():
    if "student_id" not in session:
        return redirect(url_for("login"))

    class_code = request.form["class_code"].strip().upper()

    class_data = get_class_by_code(class_code)

    if class_data is None:
        return render_template(
            "classes.html",
            classes=get_student_classes_with_progress(
                session["student_id"]
            ),
            error="Class not found."
        )

    success, status = join_class(
        class_data[0],
        session["student_id"]
    )

    if not success:
        if status == "accepted":
            message = "You are already in this class."
        elif status == "pending":
            message = "Your request is already pending."
        else:
            message = "You have already interacted with this class."

        return render_template(
            "classes.html",
            classes=get_student_classes_with_progress(
                session["student_id"]
            ),
            error=message
        )

    return redirect(url_for("student_classes"))

@app.route("/teacher/students/<int:student_id>/remove", methods=["POST"])
def teacher_remove_student(student_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    remove_student_from_teacher(student_id, session["teacher_id"])

    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/requests/accept-selected", methods=["POST"])
def accept_selected_student_requests():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    membership_ids = request.form.getlist("membership_ids")

    for membership_id in membership_ids:
        update_membership_status(
            int(membership_id),
            session["teacher_id"],
            "accepted"
        )

    return redirect(url_for("teacher_dashboard"))

if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5001, debug=False)
   # app.run(debug=True)

#http://192.168.1.25:5001
#ipconfig getifaddr en0