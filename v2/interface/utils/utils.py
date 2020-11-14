import plotly.graph_objects as go
import pandas

def plotTemp():
    temp = pandas.read_csv('v2/interface/static/data/temperature.csv')
    time = temp['datetime']
    temperature = temp['Portland']
    layout = go.Layout(
        title="Datos históricos de temperatura",
        xaxis_title="hora",
        yaxis_title="temperatura"
    )

    fig = go.Figure(
        data=go.Scatter(x=time, y=temperature),
        layout=layout
    )
    fig.show()

def plotPres():
    temp = pandas.read_csv('v2/interface/static/data/pressure.csv')
    time = temp['datetime']
    temperature = temp['Portland']
    layout = go.Layout(
        title="Datos históricos de presión",
        xaxis_title="hora",
        yaxis_title="presión"
    )

    fig = go.Figure(
        data=go.Scatter(x=time, y=temperature),
        layout=layout
    )
    fig.show()

def plotMap():
    df = pandas.read_csv('v2/interface/static/data/GPS.csv')
    fig = go.Figure(go.Scattermapbox(
    mode = "markers+lines",
    lon = df['longitude'].tolist(),
    lat = df['latitude'].tolist(),
    marker = {'size': 10}))

    fig.update_layout(
        margin ={'l':0,'t':0,'b':0,'r':0},
        mapbox = {
            'center': {'lon': -57, 'lat': -25},
            'style': "stamen-terrain",
            'zoom': 6})

    fig.show()
