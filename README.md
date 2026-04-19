# IoT-ML-Project: Machine-Learning Based Trust Assessment for Reliable IoT Data in Blockchain Networks

This project implements a secure, intelligent backend and interactive dashboard for evaluating the trustworthiness of IoT sensor data before it is recorded onto a blockchain. By integrating machine learning directly into the data verification pipeline, the system can detect anomalies, prevent malicious injections, and maintain a reputation score for different IoT sensor nodes.

## Main Features

-   **Machine Learning Based Anomaly Detection**: Uses Isolation Forests and 3-sigma statistical analysis to filter out malicious or faulty data.
-   **Ensemble Models & Composite Trust Score**: Leverages continuous reputation tracking and ensemble decision-making to reliably score each piece of incoming sensor data.
-   **Blockchain Data Integrity**: Data that passes the trust checks are logged securely onto an immutable blockchain ledger (simulated in `app.py`).
-   **Real-time Trust Dashboard**: A robust `Streamlit` frontend visualizes incoming sensor readings, block details, composite scores, and reputation over time.
-   **Sensor Simulation**: A dedicated script to simulate either normal or manual-override attacks for demonstration purposes.

---

## 🛠️ Prerequisites

Make sure you have [Python 3.8+](https://www.python.org/downloads/) installed. Depending on your environment, you may need to install the core libraries:

```bash
pip install pandas numpy scikit-learn Flask flask-cors joblib streamlit requests altair
```

---

## 🚀 How to Run the Project

To experience the full functionality of the application, follow these steps. **You will need three separate terminal windows** to run the backend, frontend, and simulated sensors concurrently.

### 1. Download the Dataset & Train the Models
For the best performance and to fully utilize the system's capabilities, it is highly recommended to use the real Intel Lab IoT dataset.
1. Download the `sensor_data.csv` (Intel Lab dataset) from Kaggle or an official source.
2. Place the `sensor_data.csv` file directly into the root directory of this project.

Once the dataset is in place, you should train the initial trust models. Run this command from the root directory:

```bash
python backend/train_model.py
```
> This will train the ensemble models and generate the necessary `.pkl` model files (e.g., `trust_model.pkl`) in the `backend/` directory.

### 2. Start the Backend API
In your **first terminal**, execute the backend. This initializes the machine-learning pipeline, handles incoming API requests from sensors, and maintains the simulated Blockchain.

```bash
python backend/app.py
```
> The API will be available at `http://127.0.0.1:5000`.

### 3. Start the Frontend Dashboard
In your **second terminal**, start your interactive `Streamlit` dashboard to view real-time data flow and blockchain blocks.

```bash
streamlit run streamlit_app.py
```
> After running, open your web browser to the Local URL provided (usually `http://localhost:8501`).

### 4. Run the Sensor Simulator
In your **third terminal**, fire up the data simulator. This script continuously requests real or synthetic data, simulates occasional malicious behavior (to trigger the AI's defenses), and pushes the data to the blockchain via our backend API.

```bash
python backend/simulate_sensors.py
```
> You will start seeing logs stream in the terminal showing whether data was accepted `✅` or blocked `🚨`. Hop into your browser to watch the Dashboard update in real-time!

---

## 📁 Project Structure

- `backend/app.py`: The core API handling ML inference, trust assessment, and the blockchain ledger.
- `backend/train_model.py`: Script to train the Isolation Forest and extra enhancement models.
- `backend/simulate_sensors.py`: Script to mimic IoT gateways, periodically emitting data to the backend API.
- `backend/trust_enhancements.py`: Auxiliary logic defining reputation weightings and ensemble testing.
- `streamlit_app.py`: The frontend UI to explore metrics, timelines, arrays of nodes, and blockchain internals.