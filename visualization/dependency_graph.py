import networkx as nx
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
from utils.logger import logger

def generate_interactive_graph(graph: nx.DiGraph, title: str) -> go.Figure:
    """Generates an interactive Plotly scatter plot for a NetworkX directed graph."""
    if not graph.nodes:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[{
                "text": "No nodes/connections to visualize.",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 16, "color": "#888"}
            }],
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ccc')
        )
        return fig

    # Determine layout positions
    pos = nx.spring_layout(graph, k=0.5, iterations=50)

    # Edge data structures
    edge_x = []
    edge_y = []
    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.8, color='#555'),
        hoverinfo='none',
        mode='lines'
    )

    # Node data structures
    node_x = []
    node_y = []
    node_text = []
    node_degrees = []
    
    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"<b>{node}</b><br>Degree (connections): {graph.degree(node)}")
        node_degrees.append(graph.degree(node))

    max_degree = max(node_degrees) if node_degrees else 1
    node_sizes = [15 + (deg / max_degree) * 20 for deg in node_degrees]

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node.split("::")[-1] if "::" in node else node for node in graph.nodes()],
        textposition="top center",
        textfont=dict(size=8, color="#aaa"),
        hovertext=node_text,
        marker=dict(
            showscale=True,
            colorscale='Blues',
            color=node_degrees,
            size=node_sizes,
            colorbar=dict(
                thickness=12,
                title=dict(
                    text='Degree',
                    side='right',
                    font=dict(color='#ccc')
                ),
                xanchor='left',
                tickfont=dict(color='#ccc')
            ),
            line=dict(width=1, color='#1e3c72')
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace],
             layout=go.Layout(
                title=dict(text=title, font=dict(size=16, color='#eee')),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ccc')
            )
    )
    return fig
