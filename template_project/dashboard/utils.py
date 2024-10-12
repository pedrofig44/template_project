# dashboard/utils.py
import polars as pl
import plotly.graph_objs as go
import json
import plotly

def generate_line_chart(df: pl.DataFrame, title: str, x_axis: str, y_axis: str, bg_color='#F3F6F9') -> str:
    if df.is_empty():
        # Create a trace with empty data
        trace = go.Scatter(
            x=[],
            y=[],
            mode='lines',
            name=y_axis
        )
    else:
        # Create a trace with actual data
        trace = go.Scatter(
            x=df['timestamp'].to_list(),
            y=df[df.columns[1]].to_list(),
            mode='lines',
            name=y_axis
        )

    layout = go.Layout(
        title=title,
        xaxis=dict(title=x_axis),
        yaxis=dict(title=y_axis),
        font=dict(
            family="Roboto, sans-serif",
            size=12,
            color="#000000"
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode='closest',
    )

    # Create the figure with the trace and layout
    figure = go.Figure(data=[trace], layout=layout)

    # Convert the figure to JSON format
    chart_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)
    
    return chart_json
