from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# --- FLASK APP CONFIGURATION ---
app = Flask(__name__, template_folder='template', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key_12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///safemind.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    assessments = db.relationship('Assessment', backref='user', lazy=True)
    chats = db.relationship('ChatMessage', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    risk_level = db.Column(db.String(10), nullable=False)
    score = db.Column(db.Integer)  # Can be mapped to specific metric
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSON)  # Stores the input features

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MODEL TRAINING LOGIC ---
def generate_mock_data(n_samples=1000):
    np.random.seed(42)
    ages = np.random.randint(12, 60, n_samples)
    sleep_hours = np.random.normal(7, 2, n_samples).clip(2, 12).astype(int)
    stress_levels = np.random.randint(1, 11, n_samples)
    
    social_activities = []
    mood_swings = []
    screen_times = []
    risk_levels = []
    
    for i in range(n_samples):
        risk_score = 0
        if sleep_hours[i] < 6: risk_score += 2
        if stress_levels[i] >= 8: risk_score += 3
        elif stress_levels[i] >= 5: risk_score += 1
            
        if risk_score > 3: soc = np.random.choice([0, 1, 2], p=[0.5, 0.3, 0.2])
        else: soc = np.random.choice([1, 2, 3], p=[0.2, 0.4, 0.4])
        social_activities.append(soc)
        
        if soc <= 1: risk_score += 2
        if risk_score > 4: mood = np.random.choice([0, 1], p=[0.2, 0.8])
        else: mood = np.random.choice([0, 1], p=[0.8, 0.2])
        mood_swings.append(mood)
        
        if mood == 1: risk_score += 2
        if risk_score > 5: screen = np.random.randint(6, 16)
        else: screen = np.random.randint(2, 8)
        screen_times.append(screen)
        
        if screen > 8: risk_score += 1
            
        if risk_score >= 7: risk_levels.append(2) # High
        elif risk_score >= 4: risk_levels.append(1) # Medium
        else: risk_levels.append(0) # Low
            
    return pd.DataFrame({
        'age': ages, 'sleep_hours': sleep_hours, 'stress_level': stress_levels,
        'social_activity': social_activities, 'mood_swings': mood_swings,
        'screen_time': screen_times, 'risk_level': risk_levels
    })

def train_risk_model(model_path):
    print("No existing model found. Generating mock dataset and training...")
    df = generate_mock_data(2000)
    X = df.drop('risk_level', axis=1)
    y = df['risk_level']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    print(f"Model trained. Accuracy: {accuracy_score(y_test, y_pred):.2f}")
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    return model

# --- PREDICTOR LOGIC ---
class RiskPredictor:
    def __init__(self, model):
        self.model = model
            
    def preprocess_input(self, data):
        social_map = {'high': 3, 'moderate': 2, 'low': 1, 'isolated': 0}
        features = {
            'age': [int(data['age'])],
            'sleep_hours': [int(data['sleep'])],
            'stress_level': [int(data['stress'])],
            'social_activity': [social_map.get(data['social'], 1)],
            'mood_swings': [1 if data['mood'] else 0],
            'screen_time': [int(data['screen'])]
        }
        return pd.DataFrame(features)

    def get_recommendations(self, risk_level):
        if risk_level == 2: # High
            return {
                'level': 'High',
                'explanation': 'Significant risk indicators detected. Professional support is highly recommended.',
                'tips': [
                    'Reach out to a professional.',
                    'Prioritize at least 7-8 hours of sleep.',
                    'Identify and reduce primary stressors.',
                    'Talk to someone you trust.'
                ]
            }
        elif risk_level == 1: # Medium
            return {
                'level': 'Medium',
                'explanation': 'Moderate risk detected. Consider small lifestyle adjustments.',
                'tips': [
                    'Try 15-min mindfulness daily.',
                    'Improve sleep hygiene.',
                    'Engage in social activities weekly.',
                    'Find healthy outlets for stress.'
                ]
            }
        else: # Low
            return {
                'level': 'Low',
                'explanation': 'Stable routine with low risk indicators. Great job!',
                'tips': [
                    'Maintain your sleep schedule.',
                    'Keep up regular social engagements.',
                    'Continue current stress-relief habits.'
                ]
            }

    def predict(self, data):
        df_input = self.preprocess_input(data)
        prediction = self.model.predict(df_input)[0]
        return self.get_recommendations(prediction)

# --- INITIALIZATION ---
gemini_api_key = os.getenv('GEMINI_API_KEY')
ai_model = None
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    model_name = 'gemini-2.5-flash'
    ai_model = genai.GenerativeModel(model_name)
    print(f"Chatbot initialized with model: {model_name}")
else:
    print("Warning: GEMINI_API_KEY not found in .env")

model_path = os.getenv('MODEL_PATH', 'risk_model.pkl')
if not os.path.exists(model_path):
    ml_model = train_risk_model(model_path)
else:
    with open(model_path, 'rb') as f:
        ml_model = pickle.load(f)

predictor = RiskPredictor(ml_model)

# Create DB tables
with app.app_context():
    db.create_all()

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('assets', path)

# --- AUTH ROUTES ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({'message': 'Logged in successfully', 'username': user.username})
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/user_status')
def user_status():
    if current_user.is_authenticated:
        return jsonify({'logged_in': True, 'username': current_user.username})
    return jsonify({'logged_in': False})

# --- PROTECTED API ROUTES ---
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    try:
        data = request.json
        required_fields = ['age', 'sleep', 'stress', 'social', 'mood', 'screen']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        result = predictor.predict(data)
        
        # Save to DB
        assessment = Assessment(
            user_id=current_user.id,
            risk_level=result['level'],
            data=data
        )
        db.session.add(assessment)
        db.session.commit()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        if not ai_model:
            return jsonify({'reply': "AI model is not configured. Please check your API key."}), 500

        prompt = f"""
        You are SafeMind AI, an empathetic mental health assistant.
        User message: "{user_message}"
        Be supportive, safe, and encouraging. If the user is in crisis, suggest professional help.
        """
        response = ai_model.generate_content(prompt)
        reply_text = response.text
        
        # Save to DB
        chat_msg = ChatMessage(
            user_id=current_user.id,
            message=user_message,
            reply=reply_text
        )
        db.session.add(chat_msg)
        db.session.commit()
        
        return jsonify({'reply': reply_text})
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Chat error details:\n{error_msg}")
        return jsonify({'reply': "Error connecting to AI. Please try again later."}), 500

@app.route('/history')
@login_required
def get_history():
    assessments = Assessment.query.filter_by(user_id=current_user.id).order_by(Assessment.timestamp.desc()).all()
    history = []
    for a in assessments:
        history.append({
            'risk_level': a.risk_level,
            'timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'data': a.data
        })
    return jsonify(history)

@app.route('/api/community_stats')
def community_stats():
    """Aggregates public community data for the dashboard."""
    try:
        # 1. Risk Distribution
        total = Assessment.query.count()
        if total == 0:
            return jsonify({
                'total': 0,
                'distribution': {'Low': 0, 'Medium': 0, 'High': 0},
                'averages': {'stress': 0, 'sleep': 0},
                'trend': []
            })

        low = Assessment.query.filter_by(risk_level='Low').count()
        med = Assessment.query.filter_by(risk_level='Medium').count()
        high = Assessment.query.filter_by(risk_level='High').count()

        # 2. Average Metrics
        # This is a bit more complex since data is in JSON. For SQLite, we can iterate or use a simpler approach.
        # For a small app, fetching all is fine. For scale, we'd use a more structured schema or native JSON functions.
        all_assessments = Assessment.query.all()
        stress_sum = 0
        sleep_sum = 0
        for a in all_assessments:
            stress_sum += a.data.get('stress', 5)
            sleep_sum += a.data.get('sleep', 7)
        
        avg_stress = round(stress_sum / total, 1)
        avg_sleep = round(sleep_sum / total, 1)

        # 3. Trend (Last 7 days or last 10 entries)
        # Simplified: Get last 10 assessment timestamps
        recent = Assessment.query.order_by(Assessment.timestamp.asc()).limit(10).all()
        trend = []
        for r in recent:
            # Map risk level to a numeric value for the chart
            risk_val = {'Low': 10, 'Medium': 20, 'High': 30}.get(r.risk_level, 10)
            trend.append({
                'date': r.timestamp.strftime('%H:%M'), # Using time for recent trend
                'value': risk_val
            })

        return jsonify({
            'total': total,
            'distribution': {
                'Low': round((low/total)*100),
                'Medium': round((med/total)*100),
                'High': round((high/total)*100)
            },
            'averages': {
                'stress': avg_stress,
                'sleep': avg_sleep
            },
            'trend': trend
        })
    except Exception as e:
        print(f"Stats Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
