# Tool: run_python_expression
# Reason: Calculate tip percentage for each transaction, then compare average tip percentage by day.

tips.assign(tip_percentage=tips['tip'].div(tips['total_bill']).mul(100)).groupby('day', observed=True)['tip_percentage'].mean().reset_index(name='average_tip_percentage').sort_values('average_tip_percentage', ascending=False)
