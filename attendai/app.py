from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date
import os

app = Flask(__name__)
CORS(app)

# ── Database config ───────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'attendance.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ── Models ────────────────────────────────────────────────────────────────────

class Student(db.Model):
    __tablename__ = 'students'
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name       = db.Column(db.String(100), unique=True, nullable=False)
    records    = db.relationship('AttendanceRecord', backref='student', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'student_id': self.student_id, 'name': self.name}


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date       = db.Column(db.Date, nullable=False, default=date.today)
    marked_at  = db.Column(db.DateTime, nullable=False, default=datetime.now)
    confidence = db.Column(db.String(10))

    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='uq_student_date'),
    )

    def to_dict(self):
        return {
            'id':         self.id,
            'student_id': self.student.student_id,
            'name':       self.student.name,
            'date':       self.date.strftime('%Y-%m-%d'),
            'time':       self.marked_at.strftime('%H:%M:%S'),
            'confidence': self.confidence,
        }


def seed_students():
    defaults = [
        {'student_id': 'STU-001', 'name': 'Vismaya'},
        {'student_id': 'STU-002', 'name': 'Manya'},
    ]
    for d in defaults:
        if not Student.query.filter_by(name=d['name']).first():
            db.session.add(Student(**d))
    db.session.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/students', methods=['GET'])
def get_students():
    students = Student.query.order_by(Student.student_id).all()
    return jsonify({'students': [s.to_dict() for s in students]})


@app.route('/api/students', methods=['POST'])
def add_student():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    sid  = (data.get('student_id') or '').strip()
    if not name or not sid:
        return jsonify({'error': 'name and student_id are required'}), 400
    if Student.query.filter_by(name=name).first():
        return jsonify({'error': f'Student "{name}" already exists'}), 409
    student = Student(name=name, student_id=sid)
    db.session.add(student)
    db.session.commit()
    return jsonify({'success': True, 'student': student.to_dict()}), 201


@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    target_date = request.args.get('date')
    if target_date:
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
    else:
        target_date = date.today()

    students = Student.query.order_by(Student.student_id).all()
    records  = {
        r.student_id: r
        for r in AttendanceRecord.query.filter_by(date=target_date).all()
    }

    result = []
    for s in students:
        rec = records.get(s.id)
        result.append({
            'id':         s.student_id,
            'name':       s.name,
            'status':     'present' if rec else 'absent',
            'time':       rec.marked_at.strftime('%H:%M:%S') if rec else None,
            'confidence': rec.confidence if rec else None,
        })

    present_count = sum(1 for r in result if r['status'] == 'present')
    total = len(result)
    return jsonify({
        'date':    target_date.strftime('%Y-%m-%d'),
        'records': result,
        'stats':   {'total': total, 'present': present_count, 'absent': total - present_count},
    })


@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    data       = request.get_json()
    name       = (data.get('name') or '').strip()
    confidence = data.get('confidence', 0)

    student = Student.query.filter_by(name=name).first()
    if not student:
        return jsonify({'error': f'Unknown student: {name}'}), 404

    today    = date.today()
    existing = AttendanceRecord.query.filter_by(student_id=student.id, date=today).first()

    if existing:
        return jsonify({
            'message':        f'{name} already marked present today',
            'already_marked': True,
            'time':           existing.marked_at.strftime('%H:%M:%S'),
            'confidence':     existing.confidence,
        }), 200

    now    = datetime.now()
    record = AttendanceRecord(
        student_id = student.id,
        date       = today,
        marked_at  = now,
        confidence = f'{round(confidence * 100)}%',
    )
    db.session.add(record)
    db.session.commit()
    print(f"[{now.strftime('%H:%M:%S')}] PRESENT: {name}  ({round(confidence*100)}%)")
    return jsonify({
        'success':    True,
        'message':    f'{name} marked present',
        'time':       now.strftime('%H:%M:%S'),
        'confidence': record.confidence,
    }), 201


@app.route('/api/attendance/reset', methods=['POST'])
def reset_attendance():
    data        = request.get_json(silent=True) or {}
    target_date = data.get('date')
    if target_date:
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = date.today()

    deleted = AttendanceRecord.query.filter_by(date=target_date).delete()
    db.session.commit()
    return jsonify({'success': True, 'deleted': deleted, 'date': str(target_date)})


@app.route('/api/attendance/history', methods=['GET'])
def get_history():
    students = Student.query.all()
    total    = len(students)
    dates    = db.session.query(AttendanceRecord.date)\
                         .distinct()\
                         .order_by(AttendanceRecord.date.desc())\
                         .all()
    history = []
    for (d,) in dates:
        records       = AttendanceRecord.query.filter_by(date=d).all()
        present_names = [r.student.name for r in records]
        absent_names  = [s.name for s in students if s.name not in present_names]
        history.append({
            'date':          d.strftime('%Y-%m-%d'),
            'present':       present_names,
            'absent':        absent_names,
            'present_count': len(present_names),
            'absent_count':  len(absent_names),
            'total':         total,
        })
    return jsonify({'history': history})


@app.route('/api/attendance/history/<string:date_str>', methods=['GET'])
def get_history_for_date(date_str):
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Use YYYY-MM-DD'}), 400
    records = AttendanceRecord.query.filter_by(date=target_date)\
                                    .order_by(AttendanceRecord.marked_at).all()
    return jsonify({'date': date_str, 'records': [r.to_dict() for r in records], 'count': len(records)})


# ── Bootstrap ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_students()
        print("Database ready  →  attendance.db")
    print("=" * 50)
    print("  AttendAI  |  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
