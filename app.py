# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for, redirect, request, jsonify, flash, session, Response
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import numpy as np
import base64, cv2 , rekognition
import boto3, tempfile, pytz, os, logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

# Flask 앱 정의
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:123456789@database-1.cbqomscqoth0.ap-northeast-2.rds.amazonaws.com:3306/test'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a_very_secret_key_12345'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
logging.basicConfig(level=logging.DEBUG)
app.config['SESSION_TYPE'] = 'filesystem'

# ProxyFix 설정
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# AWS S3 클라이언트 설정
s3 = boto3.client('s3',
                  aws_access_key_id='AKIAU6GDUY4XWGINNXO6',
                  aws_secret_access_key='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',
                  region_name='ap-northeast-2')

#회원 DB
class Member(db.Model, UserMixin):
    __tablename__ = 'student_info'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100))
    image_filename = db.Column(db.String(255))
    attendances = db.relationship('Attendance', backref='member', lazy=True)

    def __repr__(self):
        return f'<Member {self.name}>'

# 현재 서울 시간 반환 함수
def seoul_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

#출석 DB
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('student_info.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 사용자 이름 추가
    timestamp = db.Column(db.DateTime, default=seoul_now)
    message = db.Column(db.String(255), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return Member.query.get(int(user_id))

# 출석 기록을 저장할 리스트
attendance_records = []

@app.route('/')
def index():
    if current_user.is_authenticated:
        # 로그인한 사용자의 경우 다른 버튼을 표시하지 않고 '출석하기' 버튼만 표시합니다.
        return render_template('index_logged_in.html', username=current_user.name)
    # 비로그인 사용자의 경우 기본 인덱스 페이지를 보여줍니다.
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('user_name')
        password = request.form.get('user_password')

        user = Member.query.filter_by(name=username).first()
        if user and user.password == password:
            login_user(user, remember=True)
            return redirect(url_for('profile', user_id=user.id))
        else:
            flash('로그인 실패. 사용자명 또는 비밀번호가 잘못되었습니다.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = Member.query.get(user_id)
    if not user:
        return "사용자가 존재하지 않습니다.", 404

    s3_bucket_name = 'test-ju-upload'  # S3 버킷 이름
    image_url = f"https://{s3_bucket_name}.s3.amazonaws.com/{user.image_filename}"
    return render_template('profile.html', user=user, image_url=image_url)

# 회원가입 폼 페이지 렌더링 및 데이터 처리
@app.route('/join_membership', methods=['GET', 'POST'])
def join_membership():
    if request.method == 'POST':
        name = request.form.get('user_name')
        password = request.form.get('user_password')
        subject = request.form.get('subject')
        image_file = request.files.get('imageUpload')

        # 필드 확인
        if not name or not password or not subject or not image_file or not image_file.filename:
            # 로깅으로 어떤 필드가 누락되었는지 확인
            logging.debug(f"Received data - Name: {name}, Password: {password}, Subject: {subject}, Image File: {bool(image_file and image_file.filename)}")
            flash('모든 필드를 입력해주세요.', 'error')
            return redirect(url_for('join_membership'))

        # 이미지 파일명 처리
        image_filename = secure_filename(image_file.filename)
        if image_filename == '':
            flash('유효한 이미지 파일을 업로드해주세요.', 'error')
            return redirect(url_for('join_membership'))

        temp_dir = tempfile.gettempdir()
        image_path = os.path.join(temp_dir, image_filename)
        image_file.save(image_path)

        try:
            s3.upload_file(image_path, 'test-ju-upload', image_filename)
            new_member = Member(name=name, password=password, subject=subject, image_filename=image_filename)
            db.session.add(new_member)
            db.session.commit()
            flash('회원가입이 완료되었습니다.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # 상세한 에러 로그 기록
            logging.error('회원가입 중 오류가 발생했습니다: %s', e, exc_info=True)
            flash(f'회원가입 중 오류가 발생했습니다: {e}', 'error')
            return redirect(url_for('join_membership'))
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)
    return render_template('join_membership.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/get-attendance', methods=['GET'])
@login_required
def get_attendance():
    try:
        records = Attendance.query.order_by(Attendance.timestamp.desc()).all()
        attendance_text = "\n".join(
            f"{record.user_id}, {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, {record.message}"
            for record in records if isinstance(record.timestamp, datetime)
        )
        return Response(attendance_text, mimetype='text/plain'), 200
    except Exception as e:
        app.logger.error(f"Failed to fetch attendance records: {str(e)}")
        return "Internal server error", 500

@app.route('/get_username')
@login_required
def get_username():
    return Response(current_user.name, content_type='text/plain; charset=utf-8')

# 출석 가능 IP
ALLOWED_IPS = ['172.16.1.30', '112.169.18.189', '183.97.187.5', '127.0.0.1']

# 실제 사용자 IP를 정확히 가져오는 함수
def check_ip():
    if 'X-Forwarded-For' in request.headers:
        ip_address = request.headers['X-Forwarded-For'].split(',')[0]
    else:
        ip_address = request.remote_addr
    app.logger.info(f"Retrieved IP address: {ip_address}")
    return ip_address

@app.route('/attendance', methods=['POST'])
@login_required
def attendance():
    user_ip = check_ip()
    app.logger.debug(f"Full headers: {request.headers}")
    app.logger.debug(f"Raw remote_addr: {request.remote_addr}")
    app.logger.debug(f"Access attempt from IP: {user_ip}")

    if user_ip not in ALLOWED_IPS:
        return jsonify({'status': 'fail', 'message': '접근 권한 없음', 'verified': False}), 403

    try:
        logging.debug("Request received")
        data = request.get_json()
        logging.debug(f"Request JSON: {data}")
        
        if 'image' in data:
            # 얼굴 인식 로직
            image_data = data['image'].split(",")[1]
            logging.debug("Image data extracted")
            image_bytes = base64.b64decode(image_data)
            logging.debug("Image data decoded")
            captured_image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), -1)
            logging.debug("Image decoded into OpenCV format")
            
            # 임시 파일 저장
            temp_filename = f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            cv2.imwrite(temp_filename, captured_image)
            logging.debug(f"Image saved to temporary file: {temp_filename}")
            
            # 임시 파일 읽기
            with open(temp_filename, 'rb') as image_file:
                source_bytes = image_file.read()
            logging.debug("Temporary file read into bytes")

            # 데이터베이스에서 현재 사용자 정보 가져오기
            member = Member.query.filter_by(id=current_user.id).first()
            if not member or not member.image_filename:
                logging.debug("No image file found for current user")
                return jsonify({'status': 'fail', 'message': 'No image file found for current user', 'verified': False}), 400
            
            target_image = member.image_filename
            
            # rekognition.py의 compare_faces 함수 호출
            num_matches = rekognition.compare_faces(source_bytes, target_image)
            logging.debug(f"Number of matches: {num_matches}")
            
            # 결과 처리
            if num_matches > 0:
                time = seoul_now()
                logging.debug("Face match found, verification successful")
                return jsonify({
                    'status': 'success',
                    'message': '본인 확인 성공',
                    'verified': True,
                    'username': current_user.name,
                    'time': time.strftime('%H:%M:%S')
                }), 200
            else:
                logging.debug("No face match found, returning fail")
                return jsonify({
                    'status': 'fail',
                    'message': '얼굴 인식 실패',
                    'verified': False
                }), 200
        else:
            # 출석 기록 로직
            time = seoul_now()
            message = data.get('message', 'no message')
            
            # 출석 기록 저장
            attendance = Attendance(user_id=current_user.id, name=current_user.name, message=message, timestamp=time)
            db.session.add(attendance)
            db.session.commit()
            
            logging.debug("Attendance recorded")
            return jsonify({
                'status': 'success',
                'message': '출석 완료됨',
                'username': current_user.name,
                'time': time.strftime('%H:%M:%S'),
                'recordedMessage': message
            }), 200
    except Exception as e:
        logging.error(f"Error occurred: {e}", exc_info=True)
        return jsonify({'error': str(e), 'verified': False}), 400
    finally:
        # 임시 파일 삭제
        if 'temp_filename' in locals():
            try:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                    logging.debug(f"Temporary file deleted: {temp_filename}")
            except Exception as delete_error:
                logging.error(f"Failed to delete temporary file: {delete_error}")

@app.route('/record_attendance', methods=['POST'])
@login_required
def record_attendance():
    try:
        data = request.get_json()
        time = seoul_now()
        message = data.get('message', 'no message')
        
        # 출석 기록 저장
        attendance = Attendance(user_id=current_user.id, name=current_user.name, message=message, timestamp=time)
        db.session.add(attendance)
        db.session.commit()
        
        logging.debug("Attendance recorded")
        return jsonify({
            'status': 'success',
            'message': '출석 완료됨',
            'username': current_user.name,
            'time': time.strftime('%H:%M:%S'),
            'recordedMessage': message
        }), 200
    except Exception as e:
        logging.error(f"Error recording attendance: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 400

@app.route('/attendance/records', methods=['GET'])
@login_required
def show_records():
    user_id = current_user.id
    records = Attendance.query.filter_by(user_id=user_id).all()

    print(f"Fetched records for user_id {user_id}: {records}")

    attendance_text = "\n".join(
        f"{record.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {current_user.name}: {record.message}"
        for record in records if isinstance(record.timestamp, datetime)
    )

    print(f"Generated attendance text: {attendance_text}")

    return Response(attendance_text, mimetype='text/plain'), 200

# 출석 내용 전달
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        message = request.form['message']
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        record = {
            'name': name,
            'message': message,
            'time': time
        }
        attendance_records.append(record)
        return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/base')
def base():
    return render_template('base.html')

if __name__ == '__main__':
    db.create_all()  # 데이터베이스 생성
    app.run(host='0.0.0.0', port=5000, debug=True)

