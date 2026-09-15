# Tool: run_python_expression
# Reason: Calculate each meal's tip percentage, then compare the mean percentage across days.

tips.assign(tip_percentage=tips['tip'] / tips['total_bill'] * 100).groupby('day', observed=True)['tip_percentage'].mean().reset_index(name='average_tip_percentage').sort_values('average_tip_percentage', ascending=False)
