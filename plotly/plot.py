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

# def layout_templete2(title, y_axis1, y_axis2):
#     return go.Layout(
#         title=title,
#         xaxis={"title":"Date"},
#         yaxis={"title":y_axis1},
#         yaxis2={"title":"y_", "overlaying":"y", "side":"right"},
#     )
def serve_layout():
    
    def layout_template(title, y_axis):
        return go.Layout(
            title=title,
            legend={"x": 0.1, "y": 0.8},
            xaxis={"title":"Date"},
            yaxis={"title":y_axis},
            width=700,
            height=500,
        )

    raw = pd.read_csv("/home/naoya/airalarm/log.csv",
                      names=('date', 'hum', 'temp', 'pres', 'lux'))

    temp_hum = [
        go.Scatter(x=raw["date"], y=raw["temp"], name="Temparature[C]", mode = 'lines+markers'),
        go.Scatter(x=raw["date"], y=raw["hum"], name="Humidity[%]",  mode = 'lines+markers'),
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

        html.H3(children='Graphs'),
        dcc.Graph(
            id='graph-temp-hum',
            figure={
                'data': temp_hum,
                'layout': layout_template("Temparature and Humidity", "Value")
            }),
        dcc.Graph(
            id='graph-pres',
            figure={
                'data': d_pres,
                'layout': layout_template("Pressure", "Pressure[hPa]")
            }),
        dcc.Graph(
            id='graph-lux',
            figure={
                'data': d_lux,
                'layout': layout_template("Luminous intensity", "Luminous intensity[lux]")
            })
    ])



app = dash.Dash(__name__) # ファイル名をアプリ名に流用?
app.layout = serve_layout

if __name__ == '__main__':
    app.run_server(debug=False, port=5000, host='192.168.11.204')
