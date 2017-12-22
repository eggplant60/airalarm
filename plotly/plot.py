#!/usr/bin/python
# -*- coding: utf-8 -*

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go


app = dash.Dash(__name__)
app.layout = html.Div(children=[
    html.H1(children='AirAlarm'),
    html.H3(children='Configure'),
    dcc.Dropdown(
        id='range-dropdown',
        options=[
            {'label': 'All', 'value': 'v_all'},
            {'label': 'Last week', 'value': 'v_week'},
            {'label': 'Last 3 days', 'value': 'v_3days'}
        ],
        value='v_week'
    ),

    html.H3(children='Graphs'),
    dcc.Graph(id='graph-temp-hum'),
    dcc.Graph(id='graph-pres'),
    dcc.Graph(id='graph-lux'),

     # Hidden div inside the app that stores the intermediate value
    html.Div(id='intermediate-value', style={'display': 'none'})
])



# ---------------------------------------
# update data
# ---------------------------------------
@app.callback(
    dash.dependencies.Output('intermediate-value', 'children'),
    [dash.dependencies.Input('range-dropdown', 'value')])
def update_data(selected_range):
    raw = pd.read_csv("/home/naoya/airalarm/log.csv",
                      names=('date', 'hum', 'temp', 'pres', 'lux'))
    if selected_range == 'v_all':
        data = raw
    elif selected_range == 'v_week':
        data = raw[-1008:] # 7days x 24hours x 60min / 10min
    else:
        data = raw[-432:] # 3days x 24hours x 60min / 10min
    return data.to_json(date_format='iso', orient='split')


# ---------------------------------------
# update graphs
# ---------------------------------------
def layout_template(title, y_axis):
    return go.Layout(
        title=title,
        legend={"x": 0.1, "y": 0.8},
        xaxis={"title":"Date"},
        yaxis={"title":y_axis},
        width=700,
        height=500,
    )

@app.callback(
    dash.dependencies.Output('graph-temp-hum', 'figure'),
    [dash.dependencies.Input('intermediate-value', 'children')])
def update_graph_temp_hum(jsonified_data):
    data = pd.read_json(jsonified_data, orient='split')
    temp_hum = [
        go.Scatter(x=data["date"], y=data["temp"],
            name="Temparature [℃]", mode = 'lines+markers'),
        go.Scatter(x=data["date"], y=data["hum"],
            name="Humidity [%]",  mode = 'lines+markers'),
    ]
    return {'data': temp_hum,
            'layout': layout_template("Temparature and Humidity", "Value")}


@app.callback(
    dash.dependencies.Output('graph-pres', 'figure'),
    [dash.dependencies.Input('intermediate-value', 'children')])
def update_graph_temp_hum(jsonified_data):
    data = pd.read_json(jsonified_data, orient='split')
    d_pres = [go.Scatter(x=data["date"], y=data["pres"],
        name="Pressure", mode = 'lines+markers')]
    return {'data': d_pres,
            'layout': layout_template("Pressure", "Pressure [hPa]")}


@app.callback(
    dash.dependencies.Output('graph-lux', 'figure'),
    [dash.dependencies.Input('intermediate-value', 'children')])
def update_graph_temp_hum(jsonified_data):
    data = pd.read_json(jsonified_data, orient='split')
    d_lux = [go.Scatter(x=data["date"], y=data["lux"],
        name="Luminous", mode = 'lines+markers')]
    return {'data': d_lux,
            'layout': layout_template("Luminous intensity", \
            "Luminous intensity [lux]")}


if __name__ == '__main__':
    app.run_server(debug=False, port=5000, host='192.168.11.204')
