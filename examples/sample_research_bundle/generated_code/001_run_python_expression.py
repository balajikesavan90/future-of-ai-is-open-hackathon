# Tool: run_python_expression
# Reason: Calculate tip percentage for each visit, then compare the mean percentage by day.

tips.assign(tip_percentage=tips['tip'] / tips['total_bill']).groupby('day', observed=True)['tip_percentage'].mean().reset_index(name='average_tip_percentage').sort_values('average_tip_percentage', ascending=False)
