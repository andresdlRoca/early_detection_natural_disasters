import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from flask import Flask, jsonify

file_path = '/DISASTERS/1900_2021_DISASTERS.xlsx - emdat data.csv' 
df = pd.read_csv(file_path)

floods_yearly = df[df['Disaster Type'] == 'Flood'].groupby('Year').size()
storms_yearly = df[df['Disaster Type'] == 'Storm'].groupby('Year').size()

floods_storms_yearly = pd.DataFrame({
    'Floods': floods_yearly,
    'Storms': storms_yearly
}).fillna(0) 

def create_lag_features(df, lag=12):
    for i in range(1, lag + 1):
        df[f'lag_{i}'] = df['value'].shift(i)
    return df.dropna()

floods_df = floods_storms_yearly[['Floods']].rename(columns={'Floods': 'value'})
floods_df = create_lag_features(floods_df)

storms_df = floods_storms_yearly[['Storms']].rename(columns={'Storms': 'value'})
storms_df = create_lag_features(storms_df)

def train_random_forest(df):
    X = df.drop(columns=['value'])
    y = df['value']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    return model

floods_model = train_random_forest(floods_df)
storms_model = train_random_forest(storms_df)

# Save the models to disk
joblib.dump(floods_model, 'floods_model.pkl')
joblib.dump(storms_model, 'storms_model.pkl')

# Flask app
app = Flask(__name__)

# Load the models
floods_model = joblib.load('floods_model.pkl')
storms_model = joblib.load('storms_model.pkl')

# Function to create forecast
def create_forecast_df(model, df, steps=12):
    last_values = df.iloc[-1, :].values.reshape(1, -1)
    forecast = []

    for _ in range(steps):
        features = last_values[:, 1:]
        prediction = model.predict(features)
        forecast.append(prediction[0])
        last_values = np.roll(last_values, -1)
        last_values[0, -1] = prediction
    
    return forecast

@app.route('/forecast', methods=['GET'])
def forecast():
    floods_forecast = create_forecast_df(floods_model, floods_df)
    storms_forecast = create_forecast_df(storms_model, storms_df)

    response = {
        'FloodsForecast': floods_forecast,
        'StormsForecast': storms_forecast
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
