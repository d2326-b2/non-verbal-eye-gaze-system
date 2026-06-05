# Random Forest Algorithm Analysis
## Non-Verbal Eye-Gaze System

---

## 📊 Overview

The **Random Forest Classifier** is used in `alerts/alert.py` to intelligently detect when a patient needs urgent help by analyzing patterns in task selections during a session.

---

## 🔍 How Random Forest is Working

### 1. **Model Location & Usage**
- **File:** [alerts/alert.py](alerts/alert.py)
- **Class:** `RandomForestClassifier` from `scikit-learn`
- **Purpose:** Classify whether an alert should be sent based on patient behavior patterns

### 2. **Training Phase** (`_build_alert_model()`)

The model is trained **once at startup** with synthetically generated data covering all possible scenarios:

```
Training Data Generator: 
  Medicine:  0 to 14 selections
  Pain:      0 to 14 selections
  Help:      0 to 14 selections
  Fever:     0 to 14 selections
  
Total combinations: 15 × 15 × 15 × 15 = 50,625 training samples
```

#### Model Configuration:
```python
RandomForestClassifier(
    n_estimators=200,          # 200 decision trees
    max_depth=22,              # Each tree can be max 22 levels deep
    min_samples_split=2,       # Split node if it has ≥2 samples
    min_samples_leaf=1,        # Allow leaf nodes with 1 sample
    class_weight='balanced',   # Handle imbalanced classes (mostly 0s)
    n_jobs=-1,                 # Use all CPU cores
    random_state=42            # Reproducible results
)
```

### 3. **Feature Vector** (8 features per prediction)

For each prediction, the model analyzes:

| # | Feature | Description | Example |
|---|---------|-------------|---------|
| 1 | `med` | Medicine selections in session | 3 |
| 2 | `pain` | Pain selections in session | 1 |
| 3 | `help_cnt` | Help selections in session | 2 |
| 4 | `fever` | Fever selections in session | 0 |
| 5 | `total_count` | Sum of all 4 critical tasks | 6 |
| 6 | `tasks_selected` | How many different critical tasks selected | 3 |
| 7 | `max_single` | Highest count for one task | 3 (Medicine) |
| 8 | `avg_count` | Average across critical tasks | 1.5 |

**Example Feature Vector:** `[3, 1, 2, 0, 6, 3, 3, 1.5]`

### 4. **Alert Decision Logic** (Training Labels)

The model learns to predict when to send alerts based on **4 urgency patterns**:

```python
single_task_urgent = max_single >= 5          # Patient keeps asking for same thing
multiple_tasks_urgent = (tasks >= 3) AND (total >= 6)  # Multiple urgent needs
total_urgent = total_count >= 8               # Too many requests overall
many_tasks = tasks_selected >= 4              # Many different urgent needs
```

**Alert Triggered If:** Any pattern above is TRUE → `y = 1` (send alert)

### 5. **Prediction Phase** (`should_send_alert()`)

When patient selects a critical task:

1. **Extract 8-feature vector** from session counts
2. **Get probability** from RF model: `model.predict_proba(features)[0][1]`
   - `[0][0]` = probability of NO alert
   - `[0][1]` = probability of YES alert
3. **Compare to threshold:** `probability >= 0.55`
4. **Send alert if:** `probability >= 0.55` ✅

### 6. **Session Activity Window**

- **Tracked selections:** Last 20 selections OR last 5 minutes (whichever is less)
- **Reset:** Counts refresh as session progresses
- **Purpose:** Only recent activity matters; prevents old events from triggering alerts

---

## ⚠️ Issues & Problems Found

### 🔴 **CRITICAL ISSUE #1: Documentation Error**

**File:** `CODE_REVIEW.md` (Line ~30)
**Problem:** Module documentation says it's `alerts/email_alert.py` but actual file is `alerts/alert.py`
**Impact:** Low - Just documentation mismatch

---

### 🟡 **ISSUE #2: Feature Scaling Not Applied**

**Location:** `alerts/alert.py` lines 56-96, 131-149

**Problem:** 
- Features have **different ranges**:
  - Individual task counts: 0-14
  - Total count: 0-56
  - Average: 0-14
  - Max single: 0-14
  
- Random Forest doesn't require scaling (it splits on raw values), BUT:
  - Model was trained with specific value ranges
  - If `total_count` reaches 57+ in production, it's **outside training distribution**

**Current Protection:** ✅ Unlikely in practice (requires 57+ total urgent selections)

**Recommendation:** Document this assumption

---

### 🟡 **ISSUE #3: Model Not Saved to Disk**

**Location:** `alerts/alert.py` line 95

**Problem:**
```python
_alert_model = _build_alert_model()  # Rebuilt EVERY app restart
```

**Issues:**
- Model is retrained on app startup (slow, ~100-200ms)
- If training data generation changes, alerts behave differently
- No model versioning

**Recommendation:** Consider saving/loading model:
```python
import joblib
joblib.dump(model, 'alert_model.pkl')
model = joblib.load('alert_model.pkl')
```

---

### 🟡 **ISSUE #4: Training Data is Artificial, Not Real**

**Location:** `alerts/alert.py` lines 56-75

**Problem:**
- Training data is **synthetically generated**, not based on real patient behavior
- All scenarios weighted equally (Medicine=0-14, Pain=0-14, etc.)
- Real patients likely don't distribute evenly across all tasks

**Example Problems:**
- System might under-trigger if actual patients show high `max_single` with low `total_count`
- System might over-trigger if real sessions naturally accumulate tasks differently

**Recommendation:** 
- Collect real session logs
- Retrain model with actual patient behavior patterns
- Use `class_weight='balanced'` is a good temporary measure

---

### 🟡 **ISSUE #5: Hardcoded Thresholds in Two Places**

**Locations:** 
- Training logic (lines 72-73): `max_single >= 5`, `total >= 8`, etc.
- Alert detection logging (lines 117-122): `max_single >= 4`, `total >= 6` (DIFFERENT!)

**Problem:**
```python
# TRAINING THRESHOLD (Line 72-73)
single_task_urgent = max_single >= 5  ← 5

# LOGGING THRESHOLD (Line 117)
if max_single >= 4:  ← 4 (DIFFERENT!)
    patterns.append(f"CONTINUOUS:{max_single}x")
```

These should match! The logging thresholds are **off by one** from training.

**Recommendation:** Sync thresholds or document why they differ

---

### 🟡 **ISSUE #6: Alert Cooldown vs. Threshold Mismatch**

**Location:** `ui/task_grid.py` lines 468-475

**Problem:**
- Cooldown: `30 seconds` — prevent alert spam
- Probability threshold: `0.55` — trigger alert
- But if patient selects "Medicine" at 0:00 AND 0:31, RF model may make different predictions depending on `recent_counts` state

**Current Behavior:**
1. Patient selects Medicine → recent_counts["Medicine"] = 1 → P = 0.30 → No alert (too low)
2. 29 seconds later: Select Medicine again → recent_counts["Medicine"] = 2 → P = 0.45 → No alert
3. 1 second later (cooldown expired): Select Medicine again → recent_counts["Medicine"] = 3 → P = 0.60 → **Alert sent!** ✅

This is OK, but users might be confused why same action at different times triggers different results.

---

### 🟢 **ISSUE #7: Unused Variable in Training**

**Location:** `alerts/alert.py` line 54

```python
tasks_selected = sum([1 for count in [med, pain, help_cnt, fever] if count > 0])
```

This is calculated but only used **in the feature vector**, not in label generation. Currently this is fine, but suggests incomplete feature engineering.

---

## ✅ What's Working Well

1. **Thread-safe predictions** — Background thread prevents UI freeze
2. **Balanced classes** — `class_weight='balanced'` handles alert rarity
3. **Session-based, not lifetime** — Prevents old alerts from triggering new ones
4. **Multi-recipient support** — Can send to multiple Telegram chat IDs
5. **Cooldown system** — Prevents alert spam
6. **Probability threshold** — Configurable sensitivity (0.55 is reasonable default)

---

## 📈 Suggested Improvements

### Priority 1 (Recommended)
- [ ] Fix threshold mismatch between training (≥5) and logging (≥4)
- [ ] Save/load model to disk instead of retraining each startup
- [ ] Document why Random Forest was chosen over simpler rules

### Priority 2 (Nice to Have)
- [ ] Collect real patient data and retrain model
- [ ] Add feature importance analysis to understand which features matter most
- [ ] Visualize decision boundaries with matplotlib

### Priority 3 (Future)
- [ ] A/B test different probability thresholds
- [ ] Add alert history tracking (which patterns triggered alerts)
- [ ] Monitor alert accuracy (did staff respond? was it urgent?)

---

## 🧪 Testing Recommendations

```python
# Test 1: Single task urgency
send_alert("Medicine", "I need medicine", {"Medicine": 5, "Pain": 0, "Help": 0, "Fever": 0})
# Expected: Alert should trigger (max_single >= 5)

# Test 2: Multiple tasks
send_alert("Pain", "I'm in pain", {"Medicine": 2, "Pain": 2, "Help": 2, "Fever": 0})
# Expected: No alert (total < 6)

# Test 3: Boundary condition
send_alert("Help", "Help me", {"Medicine": 2, "Pain": 2, "Help": 2, "Fever": 0})
# Expected: No alert (total = 6, tasks = 3; needs total >= 8 OR tasks >= 4)
```

---

## 🔧 Configuration Parameters

Located in [alerts/alert.py](alerts/alert.py#L27-L29):

```python
HIGH_PRIORITY_TASKS = {"Medicine", "Pain", "Help", "Fever"}
TASK_INDEX = {"Medicine": 0, "Pain": 1, "Help": 2, "Fever": 3}
ALERT_PROBA_THRESHOLD = 0.55  # ← Tune this to adjust sensitivity
```

**Tuning guidance:**
- **Lower threshold (0.4):** More alerts (higher sensitivity, may be noisy)
- **Higher threshold (0.7):** Fewer alerts (only very confident cases)
- **Current (0.55):** Balanced middle ground

