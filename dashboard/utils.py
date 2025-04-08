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



def generate_pie_chart(data: dict, title: str, bg_color='#F3F6F9', height=300) -> str:
    """
    Generate a pie chart visualization using Plotly.
    
    Args:
        data: Dictionary with 'labels', 'values', and optional 'colors'
        title: Chart title
        bg_color: Background color
        height: Chart height in pixels
    
    Returns:
        JSON string of the Plotly figure
    """
    if not data or 'labels' not in data or 'values' not in data or len(data['labels']) == 0:
        # Return empty chart if no data
        trace = go.Pie(
            labels=['No Data'],
            values=[1],
            textinfo='none'
        )
    else:
        # Create a pie chart with the provided data
        trace = go.Pie(
            labels=data['labels'],
            values=data['values'],
            marker=dict(
                colors=data.get('colors', None)
            ),
            textinfo='percent',
            hoverinfo='label+percent',
            hole=0.3,  # Creates a donut chart
            textposition='inside',  # Position text inside the pie slices
            insidetextorientation='radial'  # Orient text radially
        )

    layout = go.Layout(
        title={
            'text': title,
            'y': 0.95,  # Move title higher to avoid overlap
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        font=dict(
            family="Roboto, sans-serif",
            size=12,
            color="#000000"
        ),
        height=height + 50,  # Increase height to prevent cropping
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=30, r=30, t=80, b=50),  # Increased top and bottom margins
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        )
    )

    # Create the figure with the trace and layout
    figure = go.Figure(data=[trace], layout=layout)

    # Convert the figure to JSON format
    chart_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)
    
    return chart_json
    