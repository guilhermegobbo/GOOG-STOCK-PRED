# -*- coding: utf-8 -*-
import pandas as pd
import datetime
from flask import Flask, render_template, jsonify
from tensorflow.keras.models import load_model
import joblib
from flask_cors import CORS
import plotly.express as px

df = pd.read_csv('../GOOG1.csv') # dataset
data = df.filter(['Close'])

time_steps = 20 

model = load_model('lstm_model.h5') # modelo LSTM
scaler = joblib.load('scaler.pkl') # scaler MinMaxScaler

last_results = pd.DataFrame({'close': data.values.reshape(-1, )}, index=data.index)
last_results['close'] = scaler.transform(last_results['close'].values.reshape(-1, 1))
# start_date = data.index[-1].date().strftime('%Y-%m-%d')
start_date = '2023-10-18' # útlima data de registro de nosso dataset
         


app = Flask(__name__)
CORS(app)



# função para predição com nosso modelo LSTM
def predict_values_for_future_dates(model, data, start_date, num_dates, time_steps):
    predictions = []

    current_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    
    for _ in range(num_dates):
        input_data = data[-time_steps:].values
        input_data = input_data.reshape(1, time_steps, 1)
        
        prediction = model.predict(input_data)
        predictions.append(prediction[0, 0])
        
        current_date += datetime.timedelta(days=1)
        
        data = pd.concat([data, pd.DataFrame({'close': prediction[0, 0]}, index=[current_date])])

    return predictions


# rota para prever os valores futuros com base na quantidade de dias (num_dates)
@app.route('/forecast/<int:num_dates>', methods=['GET'])
def forecast(num_dates):
    try:
        # calcular os valores futuros (em USD $)
        predicted_values = predict_values_for_future_dates(model, last_results, start_date, int(num_dates)+1, time_steps)

        NEW_DATES = [start_date]

        # adicionar as datas futuras com base na última data do dataset (start_date)
        for _ in range(num_dates):
            NEW_DATES.append((pd.to_datetime(start_date) + pd.DateOffset(days=_+1)).strftime('%Y-%m-%d'))

        # colocar nossos resultados em um DataFrame separado e com os valores em escala normal
        RESULTS = pd.DataFrame({'close': predicted_values[:]}, index=NEW_DATES)
        RESULTS['close'] = scaler.inverse_transform(RESULTS[['close']])
        predictions = RESULTS['close']
         
        # organizar em um dicionário para facilitar nossa vida com o JavaScript
        date_value_pairs = {}
        for date, prediction in zip(RESULTS.index, predictions):
            date_value_pairs[str(date)] = prediction

        date_value_pairs.pop(next(iter(date_value_pairs))) # ignorar o primeiro valor (que é com o start_date)

        forecast_data = {
            'num_dates': date_value_pairs
        }

        fig = px.line(RESULTS, x=RESULTS.index, y='close')
        fig.update_xaxes(title_text='DATA')
        fig.update_yaxes(title_text='VALOR EM USD$')

        forecast_data['graph'] = fig.to_json() # adicionar o gráfico em json ao dict 'forecast'

        return jsonify(forecast_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 400



if __name__ == '__main__':
    app.run(debug=True)

