#!/usr/bin/python
# -*- coding: utf-8 -*

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go


# ---------------------------------------
# Reading data and graph layout
# ---------------------------------------
layout1 = go.Layout(
    legend={"x":0.8, "y":0.2},
    xaxis={"title":"Date"},
    yaxis={"title":"Humidity"},
    yaxis2={"title":"Tempareture", "overlaying":"y", "side":"right"},
)
layout2 = go.Layout(
    legend={"x":0.8, "y":0.1},
    xaxis={"title":"Date"},
    yaxis={"title":"Pressure"}
)
layout3 = go.Layout(
    legend={"x":0.8, "y":0.1},
    xaxis={"title":"Date"},
    yaxis={"title":"Luminous"}
)

def serve_layout():
    raw = pd.read_csv("../log.csv", names=('date', 'hum', 'temp', 'pres', 'lux'))

    temp_hum = [
        go.Scatter(x=raw["date"], y=raw["temp"], name="Temparature", mode = 'lines+markers'),
        go.Scatter(x=raw["date"], y=raw["hum"], name="Humidity", yaxis="y2", mode = 'lines+markers'),
    ]
    d_pres = [go.Scatter(x=raw["date"], y=raw["pres"], name="Pressure", mode = 'lines+markers')]
    d_lux = [go.Scatter(x=raw["date"], y=raw["lux"], name="Luminous", mode = 'lines+markers')]

    return html.Div(children=[
        html.H1(children='AirAlarm'),

        html.H3(children='Configure'),
        dcc.RadioItems(
            options=[
                {'label': 'ON', 'value': 'v_on'},
                {'label': 'OFF', 'value': 'v_off'}
            ],
            value='v_off'
        ),

        html.H3(children='Temparature and Humidity'),
        dcc.Graph(
            id='graph-temp-hum',
            figure={'data': temp_hum, 'layout': layout1}
        ),

        html.H3(children='Pressure'),
        dcc.Graph(
            id='graph-pres',
            figure={'data': d_pres, 'layout': layout2}
        ),

        html.H3(children='Luminous'),
        dcc.Graph(
            id='graph-lux',
            figure={'data': d_lux, 'layout': layout3}
        )
    ])



app = dash.Dash(__name__) # ファイル名をアプリ名に流用?
app.layout = serve_layout

if __name__ == '__main__':
    app.run_server(debug=False, port=5000, host='192.168.11.204')
