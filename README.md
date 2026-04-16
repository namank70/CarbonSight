# 🌍 CarbonSight

## Prototype Disclaimer

- CarbonSight is a hackathon prototype created for demonstration purposes.
- The data and outputs in this repository are illustrative and should not be interpreted as audited real-world analysis or production-ready decision support.


## 🚀 AI-Powered Supply Chain Carbon Intelligence Platform

---

## 1. Project Overview

CarbonSight is an AI-assisted carbon footprint estimation platform for product supply chains.

It predicts **per-unit CO₂ emissions** and recommends **realistic greener alternatives** based on:

- Route & transport mode  
- Material composition  
- Manufacturing energy intensity  
- Packaging type  
- Recycled content  

### Architecture Stack

CarbonSight combines:

- FastAPI backend  
- Random Forest ML model  
- React + Vite frontend  
- CSV-driven environmental datasets  

---

## 2. Core Objective

CarbonSight helps users compare:

- **Original Carbon Footprint**
- **Greener Optimized Footprint**
- **Estimated Reduction Percentage**
- **Actionable Emission Reduction Suggestions**

### Carbon Tax Simulation Layer

CarbonSight also adds an economics intelligence layer:

- Simulated $100/ton carbon pricing  
- Baseline cost exposure  
- Greener scenario cost exposure  
- Estimated tax savings per unit  

This transforms sustainability from measurement-only → financial decision support.

---

## 3. Key Features

### Intelligent Prediction
- ML-based CO₂ estimation (Random Forest)
- Per-unit footprint calculation

### Route-Aware Logic
- Transport validation
- Mode recommendation (air/ship/road/rail)
- Geographic feasibility checks

### Emission Breakdown
- Materials
- Manufacturing
- Transport
- Packaging

### Optimization Engine
- Field-level greener suggestions
- Estimated kg CO₂ savings per unit
- Category-specific realism constraints

### Scoring System
- Category-relative performance score
- Letter grade (A–F)
- Reduction %

### Carbon Risk Meter
- LOW / MEDIUM / HIGH
- Identifies major emission drivers

### Carbon Tax Simulation
- Baseline cost impact
- Greener cost impact
- Estimated tax savings per unit

---

## 4. Project Structure

CarbonSight/
│
├── backend/
│   ├── main.py
│   ├── rf_model.pkl
│   ├── rf_feature_columns.json
│   └── Dataset/
│       ├── emission_factors.csv
│       ├── energy_grid_intensity.csv
│       ├── products.csv
│       ├── routes.csv
│
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── styles.css
    │   ├── components/
    │   │   └── InfoTip.jsx
    │   └── assets/

---

## 5. End-to-End Workflow

Step 1: Frontend loads metadata from backend  
(materials, countries, presets, routes, options)

Step 2: User selects:
- Product category  
- Materials  
- Route  
- Manufacturing country  
- Packaging  

Step 3: Backend:
- Normalizes inputs
- Applies route & category constraints
- Validates feasibility

Step 4: ML model predicts original per-unit CO₂.

Step 5: Optimization engine searches valid lower-carbon alternatives.

Step 6: Backend returns:
- Original CO₂
- Greener CO₂
- Reduction %
- Suggested changes
- Emission breakdown
- Score & grade
- Carbon risk level

Step 7: Frontend renders:
- Interactive result cards
- Visual comparison
- Savings metrics

---

## 6. Setup & Run

### Backend

Set up the backend from the `backend` folder by creating a Python virtual environment, installing the dependencies from `requirements.txt`, and starting the FastAPI server locally on `http://localhost:8000`.

### Frontend

Set up the frontend from the `frontend` folder by installing the dependencies and starting the development server locally on `http://localhost:5173`.

### Environment Variable

If needed, create a `.env` file inside `frontend/` and set:

`VITE_API_URL=http://localhost:8000`

If no `.env` file is set, the frontend defaults to `http://localhost:8000`.

---

## 7. Main API Endpoints

GET  /health  
GET  /metadata  
GET  /distance  
POST /analyze/{category}  

---

## 8. Technologies Used

### Backend
- Python
- FastAPI
- Pydantic
- Pandas
- NumPy
- scikit-learn
- joblib

### Frontend
- React
- Vite
- Axios
- Custom CSS (dark UI with gradients and animations)

---

## 9. Notes & Assumptions

- CarbonSight is a hackathon prototype created for demonstration purposes.
- The data and outputs in this repository are illustrative and should not be interpreted as audited real-world analysis or production-ready decision support.
- Emission breakdown is a scaled explainability proxy.
- Includes manufacturing, packaging, and transport.
- Excludes use-phase and end-of-life emissions.
- Data is CSV-based for demo speed and transparency.

---

## 10. Future Improvements

- Persistent database storage
- User authentication & scenario history
- Explainable ML diagnostics
- Dynamic carbon pricing modules
- Region-specific policy engine
- CI/CD deployment pipeline
- Monitoring & analytics

---

## 11. Team Contributions

- Hetav Vyas: contributed to the ML workflow and frontend development
- Naman Kumar: contributed to backend and frontend development
- Frontend and backend work included shared collaboration across the project

---

## 12. Credits

Project Name: CarbonSight  
Developers: Hetav Vyas & Naman Kumar  

---

CarbonSight  
From Carbon Measurement → To Climate Decision Intelligence.


