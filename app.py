from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# --- MODEL TRAINING LOGIC (Combined from train_model.py) ---
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

# --- PREDICTOR LOGIC (Combined from predictor.py) ---
class RiskPredictor:
    def __init__(self, model):
        self.model = model
            
    def preprocess_input(self, data):
        social_map = {'high': 3, 'moderate': 2, 'low': 1, 'isolated': 0}
        features = [
            int(data['age']), int(data['sleep']), int(data['stress']),
            social_map.get(data['social'], 1), 1 if data['mood'] else 0,
            int(data['screen'])
        ]
        return np.array([features])

    def get_recommendations(self, risk_level):
        if risk_level == 2: # High
            return {
                'level': 'High',
                'explanation': 'Significant risk indicators detected. Professional support is highly recommended.',
                'tips': ['Reach out to a professional.', 'Prioritize 8h sleep.', 'Reduce primary stressors.', 'Talk to someone you trust.']
            }
        elif risk_level == 1: # Medium
            return {
                'level': 'Medium',
                'explanation': 'Moderate risk detected. Consider small lifestyle adjustments.',
                'tips': ['15-min mindfulness daily.', 'Improve sleep hygiene.', 'Socialize weekly.', 'Healthy outlets for stress.']
            }
        else: # Low
            return {
                'level': 'Low',
                'explanation': 'Stable routine with low risk indicators. Great job!',
                'tips': ['Maintain sleep schedule.', 'Regular social engagements.', 'Continue current stress-relief habits.']
            }

    def predict(self, data):
        X = self.preprocess_input(data)
        prediction = self.model.predict(X)[0]
        return self.get_recommendations(prediction)

# --- FLASK APP CONFIGURATION ---
app = Flask(__name__, template_folder='template', static_folder='static')
CORS(app)

# Configure Gemini AI (Upgraded to gemini-2.0-flash)
gemini_api_key = os.getenv('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    # Using gemini-2.0-flash as the requested "flash 2.0" version
    ai_model = genai.GenerativeModel('gemini-2.0-flash')
else:
    print("Warning: GEMINI_API_KEY not found in .env")

# Initialize Model and Predictor
model_path = os.getenv('MODEL_PATH', 'risk_model.pkl')
if not os.path.exists(model_path):
    ml_model = train_risk_model(model_path)
else:
    with open(model_path, 'rb') as f:
        ml_model = pickle.load(f)

predictor = RiskPredictor(ml_model)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('assets', path)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        required_fields = ['age', 'sleep', 'stress', 'social', 'mood', 'screen']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        result = predictor.predict(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        prompt = f"""
        You are SafeMind AI, an empathetic mental health assistant.
        User message: "{user_message}"
        Be supportive, safe, and encouraging. If the user is in crisis, suggest professional help.
        """
        response = ai_model.generate_content(prompt)
        return jsonify({'reply': response.text})
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'reply': "Error connecting to AI. Please try again."}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
