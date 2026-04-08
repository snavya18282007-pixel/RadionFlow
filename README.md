# 🧠 RadionFlow — AI Radiology Triage System

AI-powered clinical decision-support system that analyzes radiology reports, predicts diseases, and prioritizes cases using triage intelligence.

# 🚀 Key Features
🧠 Disease Prediction using ML (Linear SVM + TF-IDF)

⚡ Urgency Triage (Critical / High / Medium / Low)

🔍 Explainable AI (feature-level insights)

🧾 Clinical Finding Extraction (medSpaCy with negation handling)

⚠️ Inconsistency Detection in reports

👨‍⚕️ Doctor-first workflow dashboard

📩 Automation via n8n (alerts, notifications)

# Real-World Workflow
Lab technician uploads report

AI processes through multi-stage pipeline

Case prioritized by urgency

Doctor reviews AI suggestions + explanations

Final diagnosis + automated alerts triggered

# 🧠 ML Architecture
Model: TF-IDF (word + char n-grams) + LinearSVC

# Performance:
Accuracy: 97.1%

F1 Score: 0.97

Enhancements:

Negation-aware NLP (medSpaCy)

Hybrid rule + ML system for safety
# ⚙️ Tech Stack

## Frontend
React 18 + Vite (TypeScript)

Tailwind CSS

## Backend
FastAPI

SQLAlchemy (Async)

PostgreSQL (Supabase)

## AI Pipeline
scikit-learn

medSpaCy

spaCy (en_core_sci_sm)

## Automation
n8n (Webhook-based workflows)

# 🧩 System Architecture
Modular microservices (/services)

Decoupled frontend & backend

Event-driven automation

# ▶️ Run Locally
## Backend
cd backend

pip install -r requirements.txt

uvicorn app.main:app --reload


## Frontend
cd frontend

npm install

npm run dev

# 📌 Future Improvements
Deep learning models (BERT-based clinical NLP)

Real-time streaming pipeline

Deployment with Docker + CI/CD

Monitoring (Prometheus + Grafana)

# 📬 Author
Navya S

Aspiring ML Engineer | MLOps Learner
