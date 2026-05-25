# Tool: run_python_expression
# Reason: Compute the average tip percentage by day so we can identify which day has the highest average tip percentage.

tips.assign(tip_pct=tips['tip']/tips['total_bill']).groupby('day')['tip_pct'].mean().sort_values(ascending=False)
