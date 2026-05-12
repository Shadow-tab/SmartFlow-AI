# SmartFlow AI — Smart City Traffic & Emergency Response

## Setup on Ubuntu

### 1. Install system Tkinter (if not already present)
```bash
sudo apt update
sudo apt install python3-tk
```

### 2. Clone the repo and enter the folder
```bash
cd SmartFlow-AI
```

### 3. Create and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the application
```bash
python3 main.py
```

## Project Structure
```
SmartFlow-AI/
├── main.py                        ← Launch point
├── modules/
│   ├── gui.py                     ← Tkinter GUI
│   ├── input_preprocessing.py     ← Validation & normalization
│   ├── request_router.py          ← Pipeline controller
│   ├── ann_priority.py            ← MLPClassifier priority prediction
│   ├── knowledge_base.py          ← Rule-based policy engine
│   ├── csp_scheduler.py           ← Backtracking CSP signal allocator
│   ├── search_navigation.py       ← BFS / UCS / A* route finder
│   └── final_response.py          ← Output aggregator
├── data/
│   └── training_data.csv          ← ANN training samples (60 rows)
├── requirements.txt
└── README.md
```

## Demo Cases
| # | Scenario | Expected result |
|---|---|---|
| 1 | Civilian: Police_HQ → City_Hospital | BFS route printed |
| 2 | Civilian policy check | Rejected — unauthorized |
| 3 | Ambulance emergency | Critical priority, approved, A* route |
| 4 | Ambulance integrated | Full ANN + KB + CSP + A* output |

## Screenshots for Report
1. Main window on startup (Demo 1 auto-runs)
2. Demo 2 — rejection message in output console
3. Demo 3 — full emergency response output
4. Demo 4 — integrated service full output
5. Priority badge turning red (Critical)
6. Green signal plan in CSP output line