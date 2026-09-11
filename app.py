"""Global Superstore retail dashboard.

Run locally with:
    python app.py

For a production server:
    gunicorn app:server
"""

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "clean_data.csv"

COLORS = {
    "page": "#F4F7FB",
    "surface": "#FFFFFF",
    "primary": "#173F5F",
    "secondary": "#2F75B5",
    "accent": "#E67E22",
    "success": "#1E8449",
    "text": "#1F2937",
    "muted": "#6B7280",
    "border": "#DDE3EA",
}

CARD_STYLE = {
    "backgroundColor": COLORS["surface"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "12px",
    "padding": "18px",
    "boxShadow": "0 2px 8px rgba(31, 41, 55, 0.06)",
}

GRAPH_CARD_STYLE = {
    **CARD_STYLE,
    "padding": "8px 12px 4px 12px",
    "minWidth": 0,
}

FILTER_STYLE = {
    "minWidth": "210px",
    "flex": "1 1 210px",
}


def clean_column_names(dataframe):
    """Return a copy with consistent snake_case column names."""
    cleaned = dataframe.copy()
    cleaned.columns = (
        cleaned.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return cleaned


def prepare_data(workbook_path):
    """Load, clean and combine the Orders and Returns sheets."""
    if not workbook_path.exists():
        raise FileNotFoundError(
            f"Required workbook was not found: {workbook_path}"
        )

    orders = clean_column_names(
        pd.read_excel(workbook_path, sheet_name="Orders")
    )
    returns = clean_column_names(
        pd.read_excel(workbook_path, sheet_name="Returns")
    )

    for dataframe in [orders, returns]:
        text_columns = dataframe.select_dtypes(
            include=["object", "string"]
        ).columns
        for column in text_columns:
            dataframe[column] = (
                dataframe[column].astype("string").str.strip()
            )

    # The two sheets use different labels for the US market.
    returns["market"] = returns["market"].replace(
        {"United States": "US"}
    )
    returns["returned"] = returns["returned"].str.title()

    # Market is required because some order IDs occur in multiple markets.
    orders["line_id"] = range(1, len(orders) + 1)
    orders["order_key"] = orders["market"] + "|" + orders["order_id"]
    returns["order_key"] = returns["market"] + "|" + returns["order_id"]

    date_columns = ["order_date", "ship_date"]
    numeric_columns = [
        "sales",
        "quantity",
        "discount",
        "profit",
        "shipping_cost",
    ]

    for column in date_columns:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")

    for column in numeric_columns:
        orders[column] = pd.to_numeric(orders[column], errors="coerce")

    if orders[date_columns + numeric_columns].isna().any().any():
        raise ValueError("A required date or numeric value could not be converted.")

    return_lookup = returns[["order_id", "market", "returned"]].copy()
    if return_lookup.duplicated(["order_id", "market"]).any():
        raise ValueError("The Returns sheet contains duplicate composite keys.")

    cleaned = orders.merge(
        return_lookup,
        on=["order_id", "market"],
        how="left",
        validate="many_to_one",
    )

    cleaned["return_status"] = (
        cleaned["returned"]
        .map({"Yes": "Returned"})
        .fillna("Not Returned")
    )
    cleaned = cleaned.drop(columns="returned")

    cleaned["shipping_days"] = (
        cleaned["ship_date"] - cleaned["order_date"]
    ).dt.days
    cleaned["year"] = cleaned["order_date"].dt.year
    cleaned["month_start"] = (
        cleaned["order_date"].dt.to_period("M").dt.to_timestamp()
    )

    # Deployment-time safety checks.
    if not cleaned["line_id"].is_unique:
        raise ValueError("line_id is not unique.")
    if not returns["order_key"].is_unique:
        raise ValueError("The return order_key is not unique.")
    if not set(returns["order_key"]).issubset(set(cleaned["order_key"])):
        raise ValueError("One or more return keys do not exist in Orders.")
    if (cleaned["ship_date"] < cleaned["order_date"]).any():
        raise ValueError("A ship date occurs before its order date.")

    return cleaned


if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Clean dataset was not found: {DATA_PATH}"
    )

df_clean = pd.read_csv(
    DATA_PATH,
    parse_dates=[
        "order_date",
        "ship_date",
        "month_start"
    ]
)

def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0


def format_currency(value):
    return f"${value:,.2f}"


def format_integer(value):
    return f"{value:,.0f}"


def format_percentage(value):
    return f"{value:.2%}"


def filter_dashboard_data(
    dataframe,
    selected_year="All",
    selected_market="All",
    selected_category="All",
):
    """Return a filtered copy without modifying the global DataFrame."""
    filtered = dataframe.copy()

    if selected_year not in [None, "All"]:
        filtered = filtered[filtered["year"] == int(selected_year)]
    if selected_market not in [None, "All"]:
        filtered = filtered[filtered["market"] == selected_market]
    if selected_category not in [None, "All"]:
        filtered = filtered[filtered["category"] == selected_category]

    return filtered


def calculate_dashboard_kpis(filtered_data):
    returned = filtered_data[
        filtered_data["return_status"] == "Returned"
    ]
    retained = filtered_data[
        filtered_data["return_status"] == "Not Returned"
    ]

    gross_orders = filtered_data["order_key"].nunique()
    returned_orders = returned["order_key"].nunique()
    retained_orders = retained["order_key"].nunique()
    retained_sales = retained["sales"].sum()
    retained_profit = retained["profit"].sum()

    return {
        "retained_sales": retained_sales,
        "retained_profit": retained_profit,
        "profit_margin": safe_divide(retained_profit, retained_sales),
        "retained_orders": retained_orders,
        "return_rate": safe_divide(returned_orders, gross_orders),
        "gross_orders": gross_orders,
        "returned_orders": returned_orders,
    }


def empty_figure(title):
    figure = go.Figure()
    figure.add_annotation(
        text="No data is available for this filter combination.",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 15, "color": COLORS["muted"]},
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=390,
        margin={"l": 50, "r": 30, "t": 65, "b": 50},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def finish_figure(figure):
    figure.update_layout(
        height=390,
        margin={"l": 55, "r": 30, "t": 65, "b": 55},
        title={"x": 0.02, "xanchor": "left"},
        font={"color": COLORS["text"]},
        transition_duration=250,
    )
    return figure


def build_monthly_sales_figure(filtered_data):
    title = "Retained Sales Over Time"
    retained = filtered_data[
        filtered_data["return_status"] == "Not Returned"
    ]
    if retained.empty:
        return empty_figure(title)

    summary = (
        retained.groupby("month_start", as_index=False)
        .agg(
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            total_orders=("order_key", "nunique"),
        )
        .sort_values("month_start")
    )
    figure = px.line(
        summary,
        x="month_start",
        y="total_sales",
        markers=True,
        title=title,
        labels={
            "month_start": "Month",
            "total_sales": "Retained Sales",
        },
        hover_data={
            "total_profit": ":$,.2f",
            "total_orders": ":,",
        },
        template="plotly_white",
        color_discrete_sequence=[COLORS["secondary"]],
    )
    figure.update_yaxes(tickprefix="$", tickformat=",")
    figure.update_layout(hovermode="x unified")
    return finish_figure(figure)


def build_market_sales_figure(filtered_data):
    title = "Retained Sales by Market"
    retained = filtered_data[
        filtered_data["return_status"] == "Not Returned"
    ]
    if retained.empty:
        return empty_figure(title)

    summary = retained.groupby("market", as_index=False).agg(
        total_sales=("sales", "sum"),
        total_profit=("profit", "sum"),
        total_orders=("order_key", "nunique"),
    )
    summary["profit_margin"] = (
        summary["total_profit"] / summary["total_sales"]
    )
    summary = summary.sort_values("total_sales", ascending=True)

    figure = px.bar(
        summary,
        x="total_sales",
        y="market",
        orientation="h",
        color="total_sales",
        color_continuous_scale="Blues",
        title=title,
        labels={"market": "Market", "total_sales": "Retained Sales"},
        hover_data={
            "total_profit": ":$,.2f",
            "profit_margin": ":.1%",
            "total_orders": ":,",
        },
        template="plotly_white",
    )
    figure.update_xaxes(tickprefix="$", tickformat=",")
    figure.update_layout(coloraxis_showscale=False)
    return finish_figure(figure)


def build_category_sales_figure(filtered_data):
    title = "Retained Sales by Product Category"
    retained = filtered_data[
        filtered_data["return_status"] == "Not Returned"
    ]
    if retained.empty:
        return empty_figure(title)

    summary = (
        retained.groupby("category", as_index=False)
        .agg(
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            total_orders=("order_key", "nunique"),
        )
        .sort_values("total_sales", ascending=False)
    )
    summary["profit_margin"] = (
        summary["total_profit"] / summary["total_sales"]
    )
    figure = px.bar(
        summary,
        x="category",
        y="total_sales",
        color="category",
        title=title,
        labels={
            "category": "Product Category",
            "total_sales": "Retained Sales",
        },
        hover_data={
            "total_profit": ":$,.2f",
            "profit_margin": ":.1%",
            "total_orders": ":,",
        },
        template="plotly_white",
    )
    figure.update_yaxes(tickprefix="$", tickformat=",")
    figure.update_layout(showlegend=False)
    return finish_figure(figure)


def build_market_return_figure(filtered_data):
    title = "Order Return Rate by Market"
    if filtered_data.empty:
        return empty_figure(title)

    orders = (
        filtered_data.groupby(["order_key", "market"], as_index=False)
        .agg(return_status=("return_status", "first"))
    )
    orders["returned_order"] = (
        orders["return_status"].eq("Returned").astype(int)
    )
    summary = orders.groupby("market", as_index=False).agg(
        total_orders=("order_key", "nunique"),
        returned_orders=("returned_order", "sum"),
    )
    summary["return_rate"] = (
        summary["returned_orders"] / summary["total_orders"]
    )
    summary = summary.sort_values("return_rate", ascending=False)

    figure = px.bar(
        summary,
        x="market",
        y="return_rate",
        color="market",
        title=title,
        labels={"market": "Market", "return_rate": "Return Rate"},
        hover_data={"total_orders": ":,", "returned_orders": ":,"},
        template="plotly_white",
    )
    figure.update_yaxes(tickformat=".1%")
    figure.update_layout(showlegend=False)
    return finish_figure(figure)


def build_subcategory_profit_figure(filtered_data):
    title = "Subcategory Sales and Profit"
    retained = filtered_data[
        filtered_data["return_status"] == "Not Returned"
    ]
    if retained.empty:
        return empty_figure(title)

    summary = retained.groupby(
        ["category", "sub_category"], as_index=False
    ).agg(
        total_sales=("sales", "sum"),
        total_profit=("profit", "sum"),
        units_sold=("quantity", "sum"),
        average_discount=("discount", "mean"),
    )
    summary["profit_margin"] = (
        summary["total_profit"] / summary["total_sales"]
    )

    figure = px.scatter(
        summary,
        x="total_sales",
        y="total_profit",
        color="category",
        size="units_sold",
        hover_name="sub_category",
        hover_data={
            "profit_margin": ":.1%",
            "average_discount": ":.1%",
            "units_sold": ":,",
        },
        title=title,
        labels={
            "total_sales": "Retained Sales",
            "total_profit": "Retained Profit",
            "category": "Product Category",
        },
        template="plotly_white",
    )
    figure.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"])
    figure.update_xaxes(tickprefix="$", tickformat=",")
    figure.update_yaxes(tickprefix="$", tickformat=",")
    return finish_figure(figure)


def build_shipping_figure(filtered_data):
    title = "Shipping Efficiency by Market"
    retained = filtered_data[
        filtered_data["return_status"] == "Not Returned"
    ]
    if retained.empty:
        return empty_figure(title)

    orders = retained.groupby(
        ["order_key", "market"], as_index=False
    ).agg(
        order_sales=("sales", "sum"),
        order_shipping_cost=("shipping_cost", "sum"),
        order_completion_days=("shipping_days", "max"),
    )
    summary = orders.groupby("market", as_index=False).agg(
        total_orders=("order_key", "nunique"),
        total_sales=("order_sales", "sum"),
        total_shipping_cost=("order_shipping_cost", "sum"),
        average_shipping_cost_per_order=("order_shipping_cost", "mean"),
        average_completion_days=("order_completion_days", "mean"),
    )
    summary["shipping_cost_share"] = (
        summary["total_shipping_cost"] / summary["total_sales"]
    )

    figure = px.scatter(
        summary,
        x="average_completion_days",
        y="shipping_cost_share",
        size="total_shipping_cost",
        color="market",
        hover_name="market",
        hover_data={
            "total_orders": ":,",
            "total_sales": ":$,.2f",
            "total_shipping_cost": ":$,.2f",
            "average_shipping_cost_per_order": ":$,.2f",
        },
        title=title,
        labels={
            "average_completion_days": "Average Completion Time (Days)",
            "shipping_cost_share": "Shipping Cost as a Share of Sales",
        },
        template="plotly_white",
    )
    figure.update_yaxes(tickformat=".1%")
    return finish_figure(figure)


def make_kpi_card(title, value_id, description, accent_color):
    return html.Div(
        [
            html.Div(
                style={
                    "width": "42px",
                    "height": "4px",
                    "backgroundColor": accent_color,
                    "borderRadius": "4px",
                    "marginBottom": "14px",
                }
            ),
            html.P(
                title,
                style={
                    "margin": "0 0 8px 0",
                    "color": COLORS["muted"],
                    "fontSize": "14px",
                    "fontWeight": "600",
                },
            ),
            html.H3(
                id=value_id,
                style={
                    "margin": 0,
                    "color": COLORS["text"],
                    "fontSize": "26px",
                },
            ),
            html.P(
                description,
                style={
                    "margin": "8px 0 0 0",
                    "color": COLORS["muted"],
                    "fontSize": "12px",
                    "lineHeight": "1.4",
                },
            ),
        ],
        style=CARD_STYLE,
    )


year_options = [{"label": "All Years", "value": "All"}] + [
    {"label": str(year), "value": int(year)}
    for year in sorted(df_clean["year"].dropna().unique())
]
market_options = [{"label": "All Markets", "value": "All"}] + [
    {"label": market, "value": market}
    for market in sorted(df_clean["market"].dropna().unique())
]
category_options = [{"label": "All Categories", "value": "All"}] + [
    {"label": category, "value": category}
    for category in sorted(df_clean["category"].dropna().unique())
]


app = Dash(__name__)
server = app.server
app.title = "Global Superstore Dashboard"

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    "Global Superstore Performance Dashboard",
                    style={
                        "margin": 0,
                        "color": "white",
                        "fontSize": "32px",
                    },
                ),
                html.P(
                    "Retained sales, profitability, returns and shipping performance",
                    style={
                        "margin": "8px 0 0 0",
                        "color": "#DCEAF7",
                        "fontSize": "15px",
                    },
                ),
            ],
            style={
                "background": (
                    f"linear-gradient(120deg, {COLORS['primary']}, "
                    f"{COLORS['secondary']})"
                ),
                "padding": "28px 32px",
                "borderRadius": "0 0 18px 18px",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Year", style={"fontWeight": "600"}),
                        dcc.Dropdown(
                            id="year-filter",
                            options=year_options,
                            value="All",
                            clearable=False,
                        ),
                    ],
                    style=FILTER_STYLE,
                ),
                html.Div(
                    [
                        html.Label("Market", style={"fontWeight": "600"}),
                        dcc.Dropdown(
                            id="market-filter",
                            options=market_options,
                            value="All",
                            clearable=False,
                        ),
                    ],
                    style=FILTER_STYLE,
                ),
                html.Div(
                    [
                        html.Label(
                            "Product Category",
                            style={"fontWeight": "600"},
                        ),
                        dcc.Dropdown(
                            id="category-filter",
                            options=category_options,
                            value="All",
                            clearable=False,
                        ),
                    ],
                    style=FILTER_STYLE,
                ),
                html.Button(
                    "Reset Filters",
                    id="reset-filters-button",
                    n_clicks=0,
                    style={
                        "height": "38px",
                        "alignSelf": "end",
                        "padding": "0 18px",
                        "backgroundColor": COLORS["primary"],
                        "color": "white",
                        "border": "none",
                        "borderRadius": "7px",
                        "fontWeight": "600",
                        "cursor": "pointer",
                    },
                ),
            ],
            style={
                **CARD_STYLE,
                "display": "flex",
                "gap": "16px",
                "alignItems": "end",
                "flexWrap": "wrap",
                "margin": "22px 24px 12px 24px",
            },
        ),
        html.P(
            id="filter-summary",
            style={
                "margin": "0 28px 14px 28px",
                "color": COLORS["muted"],
                "fontSize": "13px",
            },
        ),
        html.Div(
            [
                make_kpi_card(
                    "Retained Sales",
                    "retained-sales-value",
                    "Sales from orders not listed as returned",
                    COLORS["secondary"],
                ),
                make_kpi_card(
                    "Retained Profit",
                    "retained-profit-value",
                    "Profit from orders not listed as returned",
                    COLORS["success"],
                ),
                make_kpi_card(
                    "Profit Margin",
                    "profit-margin-value",
                    "Retained profit divided by retained sales",
                    COLORS["success"],
                ),
                make_kpi_card(
                    "Retained Orders",
                    "retained-orders-value",
                    "Distinct non-returned market-order keys",
                    COLORS["primary"],
                ),
                make_kpi_card(
                    "Return Rate",
                    "return-rate-value",
                    "Returned distinct orders divided by all orders",
                    COLORS["accent"],
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
                "gap": "14px",
                "margin": "0 24px 20px 24px",
            },
        ),
        dcc.Loading(
            type="circle",
            children=html.Div(
                [
                    html.Div(
                        dcc.Graph(
                            id="monthly-sales-chart",
                            config={"displaylogo": False},
                        ),
                        style=GRAPH_CARD_STYLE,
                    ),
                    html.Div(
                        dcc.Graph(
                            id="market-sales-chart",
                            config={"displaylogo": False},
                        ),
                        style=GRAPH_CARD_STYLE,
                    ),
                    html.Div(
                        dcc.Graph(
                            id="category-sales-chart",
                            config={"displaylogo": False},
                        ),
                        style=GRAPH_CARD_STYLE,
                    ),
                    html.Div(
                        dcc.Graph(
                            id="market-return-chart",
                            config={"displaylogo": False},
                        ),
                        style=GRAPH_CARD_STYLE,
                    ),
                    html.Div(
                        dcc.Graph(
                            id="subcategory-profit-chart",
                            config={"displaylogo": False},
                        ),
                        style=GRAPH_CARD_STYLE,
                    ),
                    html.Div(
                        dcc.Graph(
                            id="shipping-chart",
                            config={"displaylogo": False},
                        ),
                        style=GRAPH_CARD_STYLE,
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(auto-fit, minmax(430px, 1fr))"
                    ),
                    "gap": "16px",
                    "margin": "0 24px 20px 24px",
                },
            ),
        ),
        html.Div(
            [
                html.H4("Methodology", style={"margin": "0 0 8px 0"}),
                html.P(
                    "Retained metrics exclude orders listed in the Returns sheet. "
                    "Returned-order sales represent original recorded sales associated "
                    "with those orders—not confirmed refund amounts.",
                    style={
                        "margin": 0,
                        "color": COLORS["muted"],
                        "fontSize": "13px",
                        "lineHeight": "1.6",
                    },
                ),
            ],
            style={**CARD_STYLE, "margin": "0 24px 30px 24px"},
        ),
    ],
    style={
        "backgroundColor": COLORS["page"],
        "minHeight": "100vh",
        "fontFamily": "Arial, sans-serif",
        "color": COLORS["text"],
    },
)


@app.callback(
    Output("retained-sales-value", "children"),
    Output("retained-profit-value", "children"),
    Output("profit-margin-value", "children"),
    Output("retained-orders-value", "children"),
    Output("return-rate-value", "children"),
    Output("monthly-sales-chart", "figure"),
    Output("market-sales-chart", "figure"),
    Output("category-sales-chart", "figure"),
    Output("market-return-chart", "figure"),
    Output("subcategory-profit-chart", "figure"),
    Output("shipping-chart", "figure"),
    Output("filter-summary", "children"),
    Input("year-filter", "value"),
    Input("market-filter", "value"),
    Input("category-filter", "value"),
)
def update_dashboard(selected_year, selected_market, selected_category):
    filtered = filter_dashboard_data(
        df_clean,
        selected_year,
        selected_market,
        selected_category,
    )
    kpis = calculate_dashboard_kpis(filtered)

    return (
        format_currency(kpis["retained_sales"]),
        format_currency(kpis["retained_profit"]),
        format_percentage(kpis["profit_margin"]),
        format_integer(kpis["retained_orders"]),
        format_percentage(kpis["return_rate"]),
        build_monthly_sales_figure(filtered),
        build_market_sales_figure(filtered),
        build_category_sales_figure(filtered),
        build_market_return_figure(filtered),
        build_subcategory_profit_figure(filtered),
        build_shipping_figure(filtered),
        (
            f"Showing {len(filtered):,} order lines and "
            f"{kpis['gross_orders']:,} distinct orders."
        ),
    )


@app.callback(
    Output("year-filter", "value"),
    Output("market-filter", "value"),
    Output("category-filter", "value"),
    Input("reset-filters-button", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_number_of_clicks):
    return "All", "All", "All"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=False)

