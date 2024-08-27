import polars as pl
import plotly.graph_objs as go
import json
import plotly

def generate_line_chart(df: pl.DataFrame, title: str, x_axis: str, y_axis: str) -> str:
    # Create a single trace line chart
    trace = go.Scatter(
        x=df['timestamp'].to_list(),
        y=df[df.columns[1]].to_list(),  # Assumes the value column is the second one after 'timestamps'
        mode='lines',
        name=y_axis
    )

    layout = go.Layout(
        title=title,
        xaxis=dict(title=x_axis),
        yaxis=dict(title=y_axis)
    )

    # Create the figure with the trace and layout
    figure = go.Figure(data=[trace], layout=layout)

    # Convert the figure to JSON format
    chart_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)
    
    return chart_json
