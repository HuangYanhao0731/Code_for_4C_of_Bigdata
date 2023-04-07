import io
import pandas as pd
import threading
import time
import  analysis
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file, \
    render_template_string, send_from_directory
from flask_bootstrap import Bootstrap
from flask_mysqldb import MySQL
from jinja2 import FileSystemLoader
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
from werkzeug.security import check_password_hash
# 算法模块
from analyze_abnormal_products import analyze_abnormal_products, update_progress
from analyze_abnormal_products import get_progress
# 表单模块
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime
# 进度条
from flask import jsonify
from flask_wtf.csrf import CSRFProtect
import uuid
from django.views.decorators.csrf import csrf_exempt
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import csv

app = Flask(__name__)

# Configure MySQL database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'hyh666'
app.config['MYSQL_DB'] = 'flask'
app.config['MYSQL_PORT'] = 3306

mysql = MySQL(app)
app.config['SECRET_KEY'] = 'your_secret_key'
# csrf = CSRFProtect(app)  # CSRF保护
bootstrap = Bootstrap(app)
app.static_folder = 'static'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = 'templates/output'
# Add the allowed extensions for the files
ALLOWED_EXTENSIONS = {'tsv'}

# 设置初值，异常商品量，正常商品量
anomaly_count = 0
total_products = 0
result_url = ""
result_html_url = ""
has_detected = False

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/index', methods=['GET', 'POST'])
def index():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()
    return render_template('index.html', current_username=current_username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if email and password match the ones in the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, password FROM users WHERE email = %s;", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user[1], password):
            # Save user_id to the session
            session['user_id'] = user[0]
            flash("登录成功！", "success")
            return redirect(url_for('index', current_username=current_username))
        else:
            flash("电子邮箱或密码错误，请重新输入", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the email already exists in the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
        user_id = cursor.fetchone()
        if user_id:
            flash('Email already exists. Please login or use a different email.', 'danger')
            return redirect(url_for('register'))

        # If email doesn't exist, create a new user
        hashed_password = generate_password_hash(password, method='sha256')
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s);", (username, email, hashed_password, 'user'))
        mysql.connection.commit()
        cursor.close()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


from math import ceil

def row_to_dict(row, cursor):
    """Convert a result row to a dictionary using column names."""
    return {column[0]: value for column, value in zip(cursor.description, row)}

@app.route('/admin', methods=['GET'])
def admin():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()

    # Check if the current user is an admin
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE id = %s;", (user_id,))
    user_role = cursor.fetchone()[0]
    if user_role != 'admin':
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM users;")
    users = cursor.fetchall()
    users = [row_to_dict(user, cursor) for user in users]

    cursor.execute("SELECT * FROM feedback;")
    feedbacks = cursor.fetchall()
    feedbacks = [row_to_dict(feedback, cursor) for feedback in feedbacks]

    item_id = request.args.get('item_id')
    if item_id:
        cursor.execute("SELECT * FROM anomaly_records WHERE item_id = %s;", (item_id,))
        records = cursor.fetchall()
        records = [row_to_dict(record, cursor) for record in records]
        if not records:
            message = "未找到与该商品ID相关的异常记录"
            records = []
        else:
            message = request.args.get('message')
    else:
        message = None
        records = []


    return render_template('admin.html', item_id=item_id, message=message, anomaly_records=records, users=users,
                           feedbacks=feedbacks, current_username=current_username)

@app.route('/search_anomalies', methods=['POST'])
def search_anomalies():
    item_id = request.form['item_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM anomaly_records WHERE item_id = %s;", (item_id,))
    records = cursor.fetchall()
    records = [row_to_dict(record, cursor) for record in records]
    if not records:
        message = "未找到与该商品ID相关的异常记录"
        records = []
    else:
        message = None
    return jsonify({'message': message, 'anomaly_records': records})

@app.route('/delete_history', methods=['POST'])
def delete_history():
    year = request.form['year']
    month = request.form['month']

    # Check if the user is an admin
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE id = %s;", (user_id,))
    user_role = cursor.fetchone()[0]
    if user_role != 'admin':
        return redirect(url_for('index'))

    # Delete the history data based on the year and month
    cursor.execute("DELETE FROM anomaly_records WHERE year = %s AND month = %s;", (year, month))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message2': '数据已成功删除。', 'status': 'success'})

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']
        new_password = request.form['password']

        if new_password:
            # Hash the new password if provided
            hashed_password = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET username = %s, email = %s, password = %s, role = %s WHERE id = %s;",
                (username, email, hashed_password, role, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s;",
                (username, email, role, user_id)
            )

        mysql.connection.commit()
        return redirect(url_for('admin'))

    else:
        cursor.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
        user = cursor.fetchone()

        return render_template('edit_user.html', user=user)

# 删除用户
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s;", (user_id,))
    mysql.connection.commit()

    return redirect(url_for('admin'))

# 反馈已读路由
@app.route('/mark_feedback_as_read/<int:feedback_id>', methods=['POST'])
def mark_feedback_as_read(feedback_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM feedback WHERE id = %s;", (feedback_id,))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            input_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_file_path)
            session['input_file_path'] = input_file_path
            print(f"File uploaded: {session['input_file_path']}")  # 添加日志
            return jsonify(status='success', input_file_path=input_file_path)  # 添加 input_file_path
        else:
            return jsonify(status='error', message='Invalid file format.')

    return render_template('upload.html',current_username=current_username)


@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    global anomaly_count, result_url, result_html_url, total_products  # 使用全局变量
    print("Starting analysis...")  # 添加日志
    if 'input_file_path' not in session:
        return jsonify(status='error', message='No input file found.')
    else:
        input_file_path = session['input_file_path']
        session.pop('input_file_path', None)

    input_file_path = request.json.get('input_file_path')  # 从请求中获取 input_file_path
    output_file_path = os.path.join(app.config['OUTPUT_FOLDER'], 'result.xlsx')
    anomaly_count, total_products = analyze_abnormal_products(input_file_path, output_file_path,
                                                              update_callback=update_progress)

    # 清除与上一次检测相关的会话变量
    session.pop('download_url', None)
    session.pop('output_file_path', None)
    session.pop('result_html_url', None)

    session['download_url'] = url_for('download_result')
    session['output_file_path'] = output_file_path  # 不要在这里删除 output_file_path
    session['result_html_url'] = url_for('static', filename='output/result.html')  # 添加这一行
    result_url = session['download_url']  # 保存到全局变量
    global has_detected
    has_detected = True
    return jsonify(status='success', download_url=session['download_url'], anomaly_count=anomaly_count,
                   result_url=session['download_url'], result_html_url=session['result_html_url'])


@app.route('/progress')
def progress():
    progress_value = get_progress()
    return jsonify(progress=progress_value, anomaly_count=anomaly_count, result_url=result_url ,result_html_url=result_html_url)  # 添加 anomaly_count 和 result_url

@app.route('/download_result', methods=['GET'])
def download_result():
    if 'output_file_path' not in session:
        return redirect(url_for('upload'))
    else:
        output_file_path = session['output_file_path']

        return send_file(output_file_path, as_attachment=True)

@app.route('/result_html', methods=['GET'])
def result_html():
    if 'output_file_path' not in session:
        return redirect(url_for('upload'))
    else:
        # session.pop('output_file_path', None)  # 将 output_file_path 从 session 中删除
        return render_template('output/result.html', encoding='gbk')

def read_anomalies_from_file(file_path):
    anomalies = []

    # 读取 Excel 文件
    df = pd.read_excel(file_path, engine='openpyxl')

    # 遍历 DataFrame，将每一行添加到 anomalies 列表
    for index, row in df.iterrows():
        anomaly = {
            'item_id': row['异常商品'],
            'type': row['异常类型']
        }
        anomalies.append(anomaly)

    return anomalies

@app.route('/upload_to_db', methods=['POST'])
def upload_to_db():
    if 'output_file_path' not in session:
        return jsonify(status='error', message='No output file found.')

    year = request.form.get('year')
    month = request.form.get('month')

    if not year or not month:
        return jsonify(status='error', message='Please provide both year and month.')

    # 读取已经生成的结果文件
    output_file_path = session['output_file_path']
    anomalies = read_anomalies_from_file(output_file_path)

    # 将异常商品数据插入数据库
    cursor = mysql.connection.cursor()
    for anomaly in anomalies:
        cursor.execute("INSERT INTO anomaly_records (item_id, year, month, type) VALUES (%s, %s, %s, %s);", (anomaly['item_id'], year, month, anomaly['type']))
    mysql.connection.commit()
    cursor.close()
    # session.pop('output_file_path', None)  # 将 output_file_path 从 session 中删除
    return jsonify(status='success', message='Anomalies uploaded to the database.')

@app.route('/history', methods=['GET','POST'])
def history():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()

    if request.method == 'POST':
        year = request.form.get('year')
        month = request.form.get('month')

        if year and month:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM anomaly_records WHERE year=%s AND month=%s;", (year, month))
            mysql.connection.commit()
            cursor.close()

            return jsonify(status='success', message='数据已成功删除。')
        else:
            return jsonify(status='error', message='年份和月份是必填项。')


    if request.method == 'GET':
        year = request.args.get('year')
        month = request.args.get('month')

        if year and month:
            # 查询数据库中对应月份的异常商品信息
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT item_id, type FROM anomaly_records WHERE year=%s AND month=%s;",
                           (year, month))
            items = cursor.fetchall()
            cursor.close()

            # 将异常商品信息传入history.html渲染页面并返回
            return render_template('history.html', year=year, month=month, items=items,
                                   current_username=current_username)

        else:
            return render_template('history.html', current_username=current_username)

    return render_template('history.html', current_username=current_username)

@app.route('/download-history')
def download_history():
    year = request.args.get('year')
    month = request.args.get('month')
    # 查询数据库中对应月份的异常商品信息
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT item_id, type FROM anomaly_records WHERE year=%s AND month=%s;", (year, month))
    items = cursor.fetchall()
    cursor.close()

    # 将异常商品信息转化为csv格式
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Item ID', 'Type'])

    items_dict = [dict(zip(('item_id', 'type'), item)) for item in items]
    for item in items_dict:
        writer.writerow([item['item_id'], item['type']])

    # 将csv数据作为附件下载
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f"attachment; filename=anomaly_records_{year}_{month}.csv"
    response.headers['Content-type'] = 'text/csv'
    return response

# 设置中文字体
def get_font():
    font_path = "static/msyh.ttc"
    return FontProperties(fname=font_path)


def generate_pie_chart(anomaly_count, total_products):
    non_anomaly_count = total_products - anomaly_count
    labels = ['异常商品', '正常商品']
    sizes = [anomaly_count, non_anomaly_count]
    colors = ['#ff9999', '#66b3ff']
    font = get_font()
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontproperties': font})
    plt.axis('equal')
    plt.savefig("static/visualizations/pie_chart.svg", format='svg', bbox_inches='tight')


@app.route('/visualization')
def visualization():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()
    if not has_detected:
        return render_template('not_detected.html',current_username=current_username)
    else:
        # Generate the pie chart
        generate_pie_chart(anomaly_count, total_products)
        return render_template('visualization.html', current_username=current_username,
                               pie_chart="visualizations/pie_chart.svg")


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        if password:
            cursor.execute("UPDATE users SET username = %s, email = %s, password = %s WHERE id = %s;", (username, email, password, user_id))
        else:
            cursor.execute("UPDATE users SET username = %s, email = %s WHERE id = %s;", (username, email, user_id))
        mysql.connection.commit()
        cursor.close()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    else:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username, email FROM users WHERE id = %s;", (user_id,))
        user = cursor.fetchone()
        cursor.close()
    return render_template('settings.html', user=user, current_username=current_username)


# 提交反馈
class FeedbackForm(FlaskForm):
    feedback = TextAreaField('Your feedback', validators=[DataRequired()], render_kw={'placeholder': 'Write your feedback here', 'rows': 5})
    submit = SubmitField('Submit')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    thanks = request.args.get('thanks', False)
    user_id = session.get('user_id')
    current_username = None
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        current_username = cursor.fetchone()[0]
        cursor.close()

    if request.method == 'POST':
        feedback = request.form['feedback']

        # 获取用户id
        user_id = session.get('user_id')

        # 存储到数据库
        cursor = mysql.connection.cursor()
        current_time = datetime.now()
        cursor.execute("INSERT INTO feedback (user_id, content, submit_date) VALUES (%s, %s, %s);", (user_id, feedback, current_time))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('feedback', thanks=True))  # 添加 thanks 参数
    else:
        return render_template('feedback.html', current_username=current_username)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# 问候
@app.context_processor
def utility_functions():
    def greeting():
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "早上好"
        elif 12 <= hour < 18:
            return "下午好"
        elif 18 <= hour < 22:
            return "晚上好"
        else:
            return "夜深了"

    return dict(greeting=greeting)

if __name__ == '__main__':
    app.run(debug=True)
