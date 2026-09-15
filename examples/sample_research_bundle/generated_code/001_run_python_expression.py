# Tool: run_python_expression
# Reason: Calculate tip percentage for each meal, average it by day, and rank days from highest to lowest.

tips.assign(tip_pct=tips['tip'] / tips['total_bill'] * 100).groupby('day', observed=True)['tip_pct'].mean().reset_index(name='average_tip_percentage').sort_values('average_tip_percentage', ascending=False)
