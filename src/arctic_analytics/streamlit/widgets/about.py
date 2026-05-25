import streamlit as st
import logging

def render_about():
    logging.info(f'render_about - {st.session_state["session_id"]}')

    about_me_container = st.container()

    with about_me_container:
        st.write(
            """
            Arctic Analytics is an experimental open-source framework for metadata-aware, transparent, and constrained AI-assisted analysis over structured data.
            """
        )

        with st.expander(':blue[What is Arctic Analytics?]', expanded=False):
            st.write(
                """
                Arctic Analytics is an experimental framework for metadata-aware, transparent, and constrained AI-assisted analysis over structured data. It focuses on:
                - editable metadata before inference.
                - visible reasoning, generated code, and tool calls.
                - constrained Python execution.
                - JSON trace export.
                - human review of outputs.
                """
            )
        with st.expander(':blue[What context is sent to the model?]', expanded=False):
            st.write(
                """
                The model receives editable metadata and small row samples before it can request constrained tool calls. In particular, it receives:
                - primary keys
                - column names
                - data types
                - dataset description
                - column descriptions
                - output of the pandas describe method on your data
                - first and last 5 rows of your data.
                The tool calls, generated code, and tool outputs are visible for review.
                """
            )
        with st.expander(':blue[What can the AI actually see?]', expanded=False):
            st.write(
                """
                The model sees the current conversation state sent to the API, including:
                - the system prompt
                - all prior user inputs in the conversation
                - all prior assistant responses
                - all prior tool calls
                - all prior tool responses.

                The system prompt includes an editable metadata bundle for each loaded dataset:
                - dataframe name and shape
                - dataset description
                - data dictionary
                - pandas summary statistics
                - missing-value counts
                - first 5 rows
                - last 5 rows.

                The full dataset is loaded in the app as a pandas DataFrame. The model can request visible Python tool calls against that DataFrame, and those tool outputs become part of the conversation history.
                """
            )
                
