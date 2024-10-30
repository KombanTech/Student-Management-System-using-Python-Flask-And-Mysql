from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a more secure key in production
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'ppt'}
# MySQL Database Configuration
db_config = {
    'user': 'root',
    'password': 'komban',
    'host': 'localhost',
    'database': 'sms'
}

def get_db_connection():
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return redirect(url_for('login_view'))

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        except Exception as e:
            flash('Database error: ' + str(e), 'danger')
            return redirect(url_for('login_view'))  # Redirect on error
        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user[4], password):  # Assuming password is in the 4th column
            session['user_id'] = user[0]  # Store user ID in the session
            session['user_name'] = user[1]  # Store user name if needed
            return redirect(url_for('dashboard'))  # Redirect to student_list instead of dashboard
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')




@app.route('/student_view', methods=['GET', 'POST'])
def student_view():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = None
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM stu_users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    flash('Login successful! Welcome.', 'success')
                    return redirect(url_for('stu_dashboard'))
                else:
                    flash('Invalid email or password.', 'danger')

            except mysql.connector.Error as e:
                flash(f'Error: {e}', 'danger')
            finally:
                if cursor:
                    cursor.close()
                conn.close()
        else:
            flash('Failed to connect to the database.', 'danger')

    return render_template('student_login.html')

#################################################################################################################################################
# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/stu_assignment', methods=['GET', 'POST'])
def stu_assignment():
    if request.method == 'POST':
        title = request.form['title']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                # Fetch student name and department
                cursor.execute("SELECT name, department FROM stu_users WHERE id = %s", (session['user_id'],))
                student = cursor.fetchone()

                if student:
                    student_name = student[0]  # Use tuple index for fetching values
                    department = student[1]

                    # Insert the assignment into the database
                    cursor.execute("INSERT INTO assignments (title, filename, user_id, student_name, department) VALUES (%s, %s, %s, %s, %s)",
                                   (title, filename, session['user_id'], student_name, department))
                    conn.commit()
                    flash('Assignment submitted successfully!', 'success')
                    return redirect(url_for('stu_dashboard'))
                else:
                    flash('Student not found.', 'danger')

            except mysql.connector.Error as e:
                flash(f'Error: {e}', 'danger')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('Invalid file format. Please upload a ppt, pdf, or docx file.', 'danger')

    return render_template('stu_assignment.html')  # Render the assignment submission page



@app.route('/view_assignments', methods=['GET'])
def view_assignments():
    if 'user_id' not in session:
        flash('You must be logged in to view assignments.', 'warning')
        return redirect(url_for('login_view'))  # Redirect to login_view

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch all assignments from the database
        cursor.execute("SELECT title, filename, student_name, department FROM assignments")
        assignments = cursor.fetchall()
        return render_template('view_assignment.html', assignments=assignments)
    except mysql.connector.Error as e:
        flash(f'Error: {e}', 'danger')
        return redirect(url_for('dashboard'))  # Redirect to your dashboard
    finally:
        cursor.close()
        conn.close()




#################################################################################################################################################
@app.route('/stu_dashboard')
def stu_dashboard():
    if 'user_id' not in session:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('student_view'))  # Redirect to login if not logged in

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch students from the database
    cursor.execute("SELECT * FROM stu_users")
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    # Pass the students to the template
    return render_template('stu_dashboard.html', students=students)



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:  # Check if user_id is in session
        return redirect(url_for('login_view'))  # Redirect to login_view if not logged in
    return render_template('dashboard.html', user_name=session.get('user_name'))  

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        registration_number = request.form['registration_number']
        gender = request.form['gender']
        dob = request.form['dob']
        department = request.form['department']
        blood_group = request.form['blood_group']
        address = request.form['address']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = None
        if conn:
            try:
                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    flash('Email already exists! Please choose another one.', 'danger')
                else:
                    cursor.execute("""
                        INSERT INTO users (name, email, phone, registration_number, gender, dob, department, blood_group, address, password)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, email, phone, registration_number, gender, dob, department, blood_group, address, hashed_password))
                    conn.commit()
                    flash('User registered successfully! You can now log in.', 'success')
                    return redirect(url_for('login_view'))  # Redirect to login page after registration
                
            except Error as e:
                flash(f'Error: {e}', 'danger')
                conn.rollback()  # Roll back on error
            finally:
                if cursor:
                    cursor.close()
                conn.close()  # Always close the connection

        else:
            flash('Failed to connect to the database.', 'danger')

    return render_template('register.html')

@app.route('/stu_register', methods=['GET', 'POST'])
def stu_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        registration_number = request.form['registration_number']
        gender = request.form['gender']
        dob = request.form['dob']
        department = request.form['department']
        blood_group = request.form['blood_group']
        address = request.form['address']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = None
        if conn:
            try:
                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT * FROM stu_users WHERE email = %s", (email,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    flash('Email already exists! Please choose another one.', 'danger')
                else:
                    cursor.execute("""
                        INSERT INTO stu_users (name, email, phone, registration_number, gender, dob, department, blood_group, address, password)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, email, phone, registration_number, gender, dob, department, blood_group, address, hashed_password))
                    conn.commit()
                    flash('User registered successfully! You can now log in.', 'success')
                    return redirect(url_for('student_view'))  # Redirect to login page after registration
                
            except Error as e:
                flash(f'Error: {e}', 'danger')
                conn.rollback()  # Roll back on error
            finally:
                if cursor:
                    cursor.close()
                conn.close()  # Always close the connection

        else:
            flash('Failed to connect to the database.', 'danger')

    return render_template('stu_register.html')

@app.route('/student_list')
def student_list():
    if 'user_id' not in session:
        return redirect(url_for('login_view'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM stu_users")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('student_list.html', students=students)

from werkzeug.security import generate_password_hash  # Make sure to import this

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user_id' not in session:
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        registration_number = request.form.get('registration_number')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        blood_group = request.form.get('blood_group')
        email = request.form.get('email')
        dob = request.form.get('dob')
        password = request.form.get('password')  # Get the password from the form

        # Basic validation
        if not all([name, department, registration_number, phone, gender, blood_group, email, dob, password]):
            flash('All fields are required!', 'danger')
            return render_template('add_student.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if student with the same registration number or email already exists
            cursor.execute("SELECT * FROM stu_users WHERE registration_number = %s OR email = %s", (registration_number, email))
            existing_student = cursor.fetchone()
            
            if existing_student:
                flash('Student with this registration number or email already exists!', 'danger')
            else:
                hashed_password = generate_password_hash(password)  # Hash the password before storing
                cursor.execute("""
                    INSERT INTO stu_users (name, department, registration_number, phone, gender, blood_group, email, dob, password)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, department, registration_number, phone, gender, blood_group, email, dob, hashed_password))
                conn.commit()
                flash('Student added successfully!', 'success')

        except mysql.connector.Error as e:
            flash(f'Error adding student: {e}', 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirect(url_for('student_list'))

    return render_template('add_student.html')



@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if 'user_id' not in session:
        return redirect(url_for('login_view'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            name = request.form['name']
            department = request.form['department']
            registration_number = request.form['registration_number']
            phone = request.form['phone']
            gender = request.form['gender']
            blood_group = request.form['blood_group']
            email = request.form['email']
            dob = request.form['dob']

            cursor.execute("""
                UPDATE stu_users SET name = %s, department = %s, registration_number = %s,
                phone = %s, gender = %s, blood_group = %s, email = %s, dob = %s
                WHERE id = %s
            """, (name, department, registration_number, phone, gender, blood_group, email, dob, student_id))
            conn.commit()
            flash('Student updated successfully!', 'success')
        except mysql.connector.Error as e:
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('student_list'))

    cursor.execute("SELECT * FROM stu_users WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check for related attendance records
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id = %s", (student_id,))
        attendance_count = cursor.fetchone()[0]

        if attendance_count > 0:
            # Optionally, delete related attendance records
            cursor.execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))

        # Delete the student record
        cursor.execute("DELETE FROM stu_users WHERE id = %s", (student_id,))
        conn.commit()

        flash('Student deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting student: {e}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('student_list'))


@app.route('/course_management', methods=['GET', 'POST'])
def course_management():
    if 'user_id' not in session:
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        description = request.form.get('description')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO courses (course_name, description) VALUES (%s, %s)",
                       (course_name, description))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Course added successfully!', 'success')
        return redirect(url_for('course_management'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('course_management.html', courses=courses)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Course deleted successfully!', 'success')
    return redirect(url_for('course_management'))




#####################################################################################################################################
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user_id' not in session:
        return redirect(url_for('login_view'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        date = request.form.get('date')
        status = request.form.get('status')

        # Check if the student_id exists in the stu_users table
        cursor.execute("SELECT * FROM stu_users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            flash('Invalid student ID. Please select a valid student.', 'danger')
            return redirect(url_for('attendance'))

        print(f"Inserting attendance for student_id: {student_id}, date: {date}, status: {status}")

        try:
            cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, %s)",
                           (student_id, date, status))
            conn.commit()
            flash('Attendance marked successfully!', 'success')
        except mysql.connector.Error as e:
            flash(f'Error marking attendance: {e}', 'danger')
        
        return redirect(url_for('attendance'))

    cursor.execute("SELECT * FROM stu_users")
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('attendance.html', students=students)


@app.route('/view_attendance')
def view_attendance():
    if 'user_id' not in session:
        return redirect(url_for('student_view'))  # Redirect to login if not logged in
    
    student_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch the student's name
    cursor.execute("SELECT name FROM stu_users WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('student_view'))

    # Fetch the attendance records
    cursor.execute("SELECT date, status FROM attendance WHERE student_id = %s", (student_id,))
    attendance_records = cursor.fetchall()

    if not attendance_records:
        flash('No attendance records found for this student.', 'info')

    cursor.close()
    conn.close()
    
    return render_template('stu_attendance.html', records=attendance_records, student_name=student['name'])




#########################################################################################################

#########################################################################################################
@app.route('/grades', methods=['GET', 'POST'])
def grades():
    if 'user_id' not in session:
        return redirect(url_for('login_view'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        grade = request.form.get('grade')

        cursor.execute("INSERT INTO grades (student_id, course_id, grade) VALUES (%s, %s, %s)",
                       (student_id, course_id, grade))
        conn.commit()
        flash('Grade added successfully!', 'success')
        return redirect(url_for('grades'))

    cursor.execute("SELECT * FROM stu_users")  # Assuming this retrieves students
    students = cursor.fetchall()
    cursor.execute("SELECT * FROM courses")  # Assuming this retrieves courses
    courses = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('grades.html', students=students, courses=courses)

@app.route('/stu_grades', methods=['GET'])
def stu_grades():
    if 'user_id' not in session:
        return redirect(url_for('student_view'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    user_id = session['user_id']
    cursor.execute(
        "SELECT g.*, c.course_name FROM grades g JOIN courses c ON g.course_id = c.id WHERE g.student_id = %s",
        (user_id,)
    )
    student_grades = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('stu_grades.html', grades=student_grades)
@app.route('/stu_profile')
def stu_profile():
    if 'user_id' not in session:
        return redirect(url_for('student_login'))
    
    user_id = session['user_id']

    # Fetch user details from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM stu_users WHERE id = %s", (user_id,))
    student = cursor.fetchone()  # Use 'student' instead of 'user'
    
    cursor.close()
    conn.close()

    return render_template('stu_profile.html', student=student)  # Pass 'student' to the template


@app.route('/update_profile/<int:student_id>', methods=['GET', 'POST'])
def update_profile(student_id):
    # Your logic for updating the profile goes here
    return render_template('update_profile.html', student_id=student_id)



##########################################################################################################
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login_view'))
    
    user_id = session['user_id']

    # Fetch user details from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()

    return render_template('profile.html', user=user)


@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login_view'))
    
    return render_template('reports.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
