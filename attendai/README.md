# AttendAI — Face Recognition Attendance System

## Project Structure

```
attendai/
├── app.py                  ← Flask backend
├── requirements.txt        ← Python dependencies
├── README.md
├── templates/
│   └── index.html          ← Frontend UI
└── static/
    └── my_model/           ← ⚠ PUT YOUR MODEL FILES HERE
        ├── model.json
        ├── metadata.json
        └── weights.bin
```

## Setup

### 1. Place your Teachable Machine model files
Copy your downloaded model files into `static/my_model/`:
- `model.json`
- `metadata.json`
- `weights.bin`

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server
```bash
python app.py
```

### 4. Open your browser
Go to → http://localhost:5000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard |
| GET | `/api/attendance` | Get today's attendance + stats |
| POST | `/api/attendance/mark` | Mark a student present |
| POST | `/api/attendance/reset` | Reset today's attendance |
| GET | `/api/attendance/history` | Get all historical records |

### POST `/api/attendance/mark`
```json
{ "name": "Vismaya", "confidence": 0.92 }
```

## Notes
- Attendance resets on server restart (in-memory storage)
- To persist data, replace the `attendance_records` dict in `app.py` with SQLite using `flask-sqlalchemy`
- Confidence threshold is set to 75% (adjustable in `index.html`)
