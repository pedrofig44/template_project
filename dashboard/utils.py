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
    
    
    
def generate_bar_chart(df: pl.DataFrame, title: str, x_axis: str, y_axis: str, bg_color='#F3F6F9') -> str:
    """
    Generate a bar chart visualization using Plotly.
    
    Args:
        df: Polars DataFrame with 'timestamp' and another column for values
        title: Chart title
        x_axis: X-axis label
        y_axis: Y-axis label
        bg_color: Background color for the chart
    
    Returns:
        JSON string of the Plotly figure
    """
    if df.is_empty():
        # Create a trace with empty data
        trace = go.Bar(
            x=[],
            y=[],
            name=y_axis,
            marker_color='#1E88E5'  # Blue color for bars
        )
    else:
        # Create a trace with actual data
        trace = go.Bar(
            x=df['timestamp'].to_list(),
            y=df[df.columns[1]].to_list(),
            name=y_axis,
            marker_color='#1E88E5'  # Blue color for bars
        )

    layout = go.Layout(
        title=title,
        xaxis=dict(
            title=x_axis,
            type='category' if len(df) > 0 and isinstance(df['timestamp'][0], str) else None
        ),
        yaxis=dict(
            title=y_axis,
            rangemode='nonnegative'  # Important for precipitation which cannot be negative
        ),
        font=dict(
            family="Roboto, sans-serif",
            size=12,
            color="#000000"
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode='closest',
        bargap=0.1
    )

    # Create the figure with the trace and layout
    figure = go.Figure(data=[trace], layout=layout)

    # Convert the figure to JSON format
    chart_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)
    
    return chart_json


def generate_combined_chart(df: pl.DataFrame, title: str, x_axis: str, y_axis: str, bg_color='#F3F6F9') -> str:
    """
    Generate a combined bar and line chart visualization using Plotly.
    Useful for precipitation data to show daily bars and a cumulative line.
    
    Args:
        df: Polars DataFrame with 'timestamp' and value column
        title: Chart title
        x_axis: X-axis label
        y_axis: Y-axis label
        bg_color: Background color for the chart
    
    Returns:
        JSON string of the Plotly figure
    """
    if df.is_empty():
        # Create empty traces
        bar_trace = go.Bar(
            x=[],
            y=[],
            name=y_axis,
            marker_color='#1E88E5'
        )
        
        line_trace = go.Scatter(
            x=[],
            y=[],
            mode='lines',
            name=f"Cumulative {y_axis}",
            line=dict(color='#FF5722')
        )
    else:
        value_column = df.columns[1]
        
        # Create bar trace for individual values
        bar_trace = go.Bar(
            x=df['timestamp'].to_list(),
            y=df[value_column].to_list(),
            name=y_axis,
            marker_color='#1E88E5'
        )
        
        # Calculate cumulative sum
        cumulative_values = df[value_column].cumsum().to_list()
        
        # Create line trace for cumulative values
        line_trace = go.Scatter(
            x=df['timestamp'].to_list(),
            y=cumulative_values,
            mode='lines',
            name=f"Cumulative {y_axis}",
            line=dict(color='#FF5722'),
            yaxis='y2'  # Use secondary y-axis
        )

    layout = go.Layout(
        title=title,
        xaxis=dict(
            title=x_axis,
            type='category' if len(df) > 0 and isinstance(df['timestamp'][0], str) else None
        ),
        yaxis=dict(
            title=y_axis,
            rangemode='nonnegative',
            side='left'
        ),
        yaxis2=dict(
            title=f"Cumulative {y_axis}",
            rangemode='nonnegative',
            side='right',
            overlaying='y',
            showgrid=False
        ),
        font=dict(
            family="Roboto, sans-serif",
            size=12,
            color="#000000"
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode='closest',
        bargap=0.1,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Create the figure with the traces and layout
    figure = go.Figure(data=[bar_trace, line_trace], layout=layout)

    # Convert the figure to JSON format
    chart_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)
    
    return chart_json