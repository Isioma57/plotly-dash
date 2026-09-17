# Global Superstore Dash App


## Table of Contents

- [Executive Summary](#executive-summary)
- [Data](#data)
- [Tools and Methodology](#tools-and-methodology)
  - [Tools](#tools)
  - [Methodology](#methodology)
- [Key Findings](#key-findings)
- [Recommendations](#recommendations)
- [Limitations](#limitations)
- [Run Locally](#run-locally)
  - [Prerequisites](#prerequisites)
  - [Clone the Repository](#1-clone-the-repository)
  - [Create a Virtual Environment, Install the Requirements, and Run the App](#2-create-a-virtual-environment-install-the-requirements-and-run-the-app)
  - [Open the Dashboard](#3-open-the-dashboard)
- [Deploy on Render](#deploy-on-render)
  - [Deploying Updates](#deploying-updates)


## Executive Summary

Retail leaders make decisions about product mix, regional priorities, and fulfillment. A strong sales figure can hide weak profitability, costly shipping, or differences between markets and products. Looking only at total revenue can lead them to overlook products that sell well but lose money, or markets where delivery costs warrant attention. Understanding those differences gives them a better basis for deciding what to investigate.

This project analyzed Global Superstore data to understand sales, profitability, orders, returns, and shipping across time, markets, and products. It addressed management’s need for one reliable way to compare these areas and spot where strong sales were accompanied by weak profits or listed returns.

The analysis found $11.82 million in sales and $1.35 million in profit from orders not listed as returned. The key outcome was an interactive Plotly Dash dashboard that makes those comparisons accessible through filters. Bringing these measures into one dashboard helps management identify areas that deserve closer investigation and make decisions using more than revenue alone.


## Data

**Source and coverage.** This project uses the [SuperStore sales DataSet on Kaggle](https://www.kaggle.com/datasets/amirmotefaker/superstore-sales-dataset), supplied as `superstore_sales.xlsx`. It contains sales records from 2011 to 2014 across seven markets.

| Sheet | What one row represents | Use in this project |
|---|---|---|
| Orders | One product line within an order | Sales, profit, products, locations, and shipping |
| Returns | One order listed as returned within a market | Identifying orders associated with returns |
| People | One manager-region assignment | Present in the workbook, but not used in the dashboard |

An order can contain several product lines, so counting rows would overstate the number of orders. The analysis identifies each order using its market and order ID together because an order ID can appear in more than one market. Africa and EMEA remain separate market labels, as they are in the source data.


### Data limitations

- The Returns sheet identifies orders listed as returned, but provides no return dates, quantities, refund amounts, or indication of partial returns. The analysis treats each listed return as a fully returned order. Sales associated with those orders are their original recorded sales, not confirmed refunds.
- The data ends in 2014, so the dashboard describes historical performance rather than current business results.


## Tools and Methodology

### Tools

| Tool | Purpose |
|---|---|
| Jupyter Notebook | Documented the analysis and checked results step by step |
| Python and pandas | Cleaned, joined, validated, and summarized the data |
| Plotly Express | Created interactive charts |
| Dash | Built the dashboard layout, filters, and callbacks |
| Render | Hosted the dashboard so it can be shared through a public link |

### Methodology

1. **Inspect the data.** Reviewed the Orders, Returns, and People sheets, including what one row represents in each sheet. Checked column types, missing values, and identifiers before calculating KPIs.
2. **Clean and combine the records.** Standardized column names, text values, dates, and numeric fields. Created an order key from `market` and `order_id`, then joined the Returns sheet to Orders without losing order lines.
3. **Define the metrics.** Counted distinct orders using the combined key. Marked all lines of an order listed in Returns as returned. Calculated retained sales and profit from orders not listed as returned, and calculated profit margin from total profit divided by total sales.
4. **Prepare the analysis and charts.** Summarized results by month, market, category, and subcategory, alongside return and shipping measures. Used Plotly Express to turn those summaries into charts.
5. **Build and validate the dashboard.** Added year, market, and category filters in Dash, with callbacks that update the KPI cards and charts. Checked the dashboard’s unfiltered KPIs against the pandas results, then used the prepared data in the deployed app.


## Key Findings

1. **Retained sales nearly doubled between 2011 and 2014.** Annual retained sales rose from **$2.10 million** to **$4.00 million**, an increase of about **90%**. Monthly sales fluctuated, so the annual growth did not represent steady gains every month.

2. **APAC and EU generated over half of retained sales.** APAC contributed **$3.32 million** and EU contributed **$2.73 million**. Together, they accounted for about **51%** of the total. Changes in either market can therefore have a substantial effect on overall sales, making it important to monitor profit alongside revenue in both.

3. **Strong Furniture sales masked a loss in Tables.** Furniture generated **$3.85 million** in retained sales, but its profit margin was **6.8%**, compared with **13.7%** for Technology. Within Furniture, Tables generated about **$705,000 in sales** while losing **$60,000**. Tables’ discounts and costs should be investigated by product and market before recommending a change to pricing or product mix.

4. **The return records raise a performance question, but their coverage is incomplete.** The analysis matched **1,173 distinct orders**, or **4.68% of all recorded orders**, to the Returns sheet. Those orders were associated with about **$818,000 in original recorded sales**. Because the sheet lists returns for only four of the seven markets and contains no refund amounts, 4.68% is not a confirmed companywide return rate, and $818,000 is not confirmed refunded revenue.


## Recommendations

1. **Plan for growth using monthly demand, not annual totals alone.** Retained sales grew substantially, but monthly results varied. Use the monthly pattern to plan inventory and fulfillment capacity for high-demand periods, and review profit alongside sales as the business grows.

2. **Protect profitable growth in APAC and EU.** These markets generate over half of retained sales. Prioritize product availability and service in both markets, while assessing profit margins before increasing promotions or investment in particular categories.

3. **Take targeted action on loss-making Tables.** Review the Table products with the largest losses and test changes to discounts or pricing where the economics support them. Address avoidable costs and reconsider products that remain unprofitable after those changes. Avoid applying one change to the entire subcategory before identifying which products drive the loss.

4. **Improve return management across all markets.** Require consistent return reporting, including the reason, quantity, and refund amount for each return. Use complete records to identify avoidable causes and address the product or fulfillment issues behind them. The current data does not support a companywide return-reduction target.


## Limitations

- **Return coverage is uncertain.** The Returns sheet contains records for APAC, EU, LATAM, and US, but none for Africa, Canada, or EMEA. The displayed 4.68% is the share of orders *listed* as returned in the available data, not a verified companywide return rate.

- **The financial impact of returns cannot be confirmed.** The data has no refund amounts, returned quantities, or indication of partial returns. The analysis treats each listed return as a fully returned order. Sales associated with returned orders are original recorded sales, not confirmed refunds; retained sales and profit follow this assumption.

- **The cause of Tables’ losses is not established.** The data identifies the loss, but it does not provide a complete cost breakdown or prove that discounts, shipping, or pricing caused it. Changes to those areas should be tested against more detailed product-level costs.

- **Shipping time ends when an order ships.** The dashboard measures days from order date to ship date. Without delivery dates or service targets, it cannot assess how long customers waited to receive their orders.

- **The analysis is historical.** The dataset covers 2011–2014 and is not connected to live sales data. Its findings should not be treated as a measure of current performance.

## Run Locally

### Prerequisites

Install [Git](https://git-scm.com/) and Python 3 before starting.

### 1. Clone the repository

```bash
git clone https://github.com/Isioma57/plotly-dash.git
cd plotly-dash
```

### 2. Create a virtual environment, install the requirements, and run the app

**Windows (Git Bash):**

```bash
py -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python app.py
```

**macOS or Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

### 3. Open the dashboard

Visit **http://127.0.0.1:8050/** in your browser. To stop the app, return to the terminal and press `Ctrl+C`.

The app loads the included `data/clean_data.csv` file. The source workbook, `data/superstore_sales.xlsx`, is available for exploring the analysis notebook but is not required to run `app.py`.


## Deploy on Render

The dashboard is available at [Global Superstore Performance Dashboard](https://global-superstore-dashboard-3xke.onrender.com/). To deploy your own copy:

1. Fork this repository to your GitHub account.
2. Sign in to [Render](https://dashboard.render.com/) and select **New → Web Service**.
3. Connect your GitHub account and select your fork of this repository.
4. Configure the service:

   | Setting | Value |
   |---|---|
   | Language | Python |
   | Branch | `main` |
   | Root Directory | Leave blank; `app.py` is in the repository root |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:server` |

5. Select a service plan and click **Create Web Service**. Check the deployment logs until the service is live, then open the public `onrender.com` URL Render provides.

The app reads `data/clean_data.csv`, which is included in the repository. No separate data upload is needed.

### Deploying updates

When Render is connected to your GitHub account with auto-deploy enabled, pushing changes to the selected branch triggers a new deployment. If auto-deploy is off, open the service in Render and select **Manual Deploy → Deploy latest commit**. See [Render’s deployment guide](https://render.com/docs/deploys) for details.
























