import logging

import streamlit as st


def render_tool_calling_analysis_prompt_guide():
    logging.info(f'render_tool_calling_analysis_prompt_guide - {st.session_state["session_id"]}')
    
    with st.sidebar.expander(':blue[Prompt Guide]'):
        st.write("""Arctic Analytics is designed for metadata-aware analysis over structured data. Follow this guide to make the analysis easier to inspect:
1. Make sure you provide a good dataset description and a short description of each column in your dataset. This will help Arctic Analytics understand your data better.
2. Outline the steps the analysis should take. For example: :green[Group the data by category and calculate average sales].
3. Provide filter conditions explicitly. For example: :green[Filter to 2020, group by category, and calculate average sales].
4. Define custom KPIs. For example: :green[Calculate discount percentage as (discount / sales) * 100 by product category].
5. Review the visible tool calls, generated code, outputs, and trace export before relying on the answer.
""")
        st.info('Review the tool calls made by Arctic Analytics.')
