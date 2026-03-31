#!/bin/zsh

cd /Users/karen/Documents/sales_analytics_portfolio || exit 1
python3 dashboard/export_html.py || exit 1
open /Users/karen/Documents/sales_analytics_portfolio/output/dashboard_preview.html
