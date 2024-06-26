import streamlit as st

def render_data_analyst_prompt_guide():

    with st.sidebar.expander(':blue[Pompting Guide]'):
        st.write("""Arctic Analytics is really good at filtering, aggregating and calculating KPIs from your data. Follow this guide to get the most out of Arctic Analytics:
1. Make sure you provided a good dataset description and a short description of each column in your dataset. This will help Arctic Analytics understand your data better.
2. Arctic Analytics performs best when you outline the steps the AI should take to answer your question. For example, if you want to know the average sales for each product category, you should provide the AI with the following prompt: :green[Group the data by category and calculate the average sales].
3. If you want to filter your data, make sure you provide the AI with the filter conditions. For example, if you want to know the average sales for each product category in the year 2020, you should provide the AI with the following prompt: :green[Filter the data for the year 2020, group the data by category and calculate the average sales].
4. If you want the AI to calculate a KPI like discount percentage, make sure you provide the AI with the formula to calculate the KPI. For example, if you want to know the discount percentage for each product category, you should provide the AI with the following prompt: :green[Group the data by category and calculate the discount percentage as (discount/sales)*100].
5. Finally, if the AI is not able to answer your question, try simplifying your prompt and/or providing more context to the AI.
""")
        st.info('Be sure to QA the python syntax generated by Arctic Analytics')


def render_chart_builder_prompt_guide():

    with st.sidebar.expander(':blue[Pompting Guide]'):
        st.write("""Arctic Analytics is really good at building charts and graphs from your data. Follow this guide to get the most out of Arctic Analytics:
1. Make sure you provided a good dataset description and a short description of each column in your dataset. This will help Arctic Analytics understand your data better.
2. Arctic Analytics performs best when you clearly describe the x and y axis of the chart you want to build. For example, if you want to decile the prices and show the profitability of each decile, set the x-axis as :green[deciles of the price] and the y-axis as :green[calculate the profitability of each decile using the formula (net_profit/revenue)*100].
3. If you want to built the chart on a subset of the data, you can provide these instructions in the additional_instructions field. For example, if you want to build a chart on the data for the year 2020, you add this to the additional_instructions: :green[Filter the data for the year 2020].
4. As a best practice, try a few different chart types to see which one best represents your data. 
5. Finally, if the AI is not able to build the chart you want, try simplifying your prompt and/or providing more context to the AI.
""")
        st.info('Be sure to QA the python syntax generated by Arctic Analytics')
