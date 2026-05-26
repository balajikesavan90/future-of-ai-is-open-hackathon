# Tool: run_python_expression
# Reason: Compute the average tip percentage by day, defined as tip divided by total_bill, and identify which day is highest.

tips.assign(tip_pct=tips['tip']/tips['total_bill']).groupby('day')['tip_pct'].mean().sort_values(ascending=False)
