import streamlit as st
import logging

def render_about():
    logging.info(f'render_about - {st.session_state["session_id"]}')

    about_me_container = st.container()

    with about_me_container:
        st.write(
            """
            My name is [Balaji Kesavan](https://www.balajikesavan.com/) and I am passionate about AI. I am always looking for ways to improve my skills and learn new things.
            This is my submission to [The future of AI is open](https://arctic-streamlit-hackathon.devpost.com/) hackathon.

            You can access the source code for this project on [GitHub](https://github.com/balajikesavan90/future-of-ai-is-open-hackathon).
            The best way to reach me is on [LinkedIn](https://www.linkedin.com/in/balaji-kesavan/).
            """
        )

        with st.expander(':blue[What is Arctic Analytics?]', expanded=False):
            st.write(
                """
                Arctic Analytics is an experimental framework for metadata-aware, transparent, and constrained AI-assisted analysis over structured data. It focuses on:
                - editable metadata before inference.
                - visible generated code and tool calls.
                - constrained Python execution.
                - human review of outputs.
                """
            )
        with st.expander(':blue[What context is sent to the model?]', expanded=False):
            st.subheader(':blue[When Agent Mode is disabled]')
            st.write(
                """
                The model receives metadata and small row samples rather than direct dataframe tool access. In particular, it receives:
                - primary keys
                - column names
                - data types
                - dataset description
                - column descriptions
                - output of the pandas describe method on your data
                - first and last 5 rows of your data.
                """
            )
            st.subheader(':blue[When Agent Mode is enabled]')
            st.write(
                """
                The model can request constrained Python tool calls over the loaded data. The tool calls, generated code, and tool outputs are visible for review.
                """
            )
        with st.expander(':blue[What can the AI actually see?]', expanded=False):
            st.write(
                """
                After you load your data and start an analysis, you can view the prompt/context in the sidebar and export a JSON trace of the current session state.
                """
            )
                
