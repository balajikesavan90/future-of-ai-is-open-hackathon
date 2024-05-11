import streamlit as st

from utils.streamlit_helpers import goto_data_dictionary_widget, goto_data_analysis_widget

def render_uploaded_data(page):
    st.toast(':blue[Data Dictionaries have been saved!]')
    st.success(':green[Make sure your data looks good especially if you changed the data types]')

    for filename in st.session_state['vetted_files']:
        df = st.session_state['vetted_files'][filename]['dataframe']
        st.subheader(f':blue[{filename}]')
        st.dataframe(
            data=df,
            hide_index=True,
            height=250,
            use_container_width=True
        )
        st.divider()
    
    back_col, proceed_col = st.columns(2)
    with back_col:
        st.button(
            label=':red[Go Back]',
            on_click=goto_data_dictionary_widget,
            use_container_width=True
        )
    with proceed_col:
        st.button(
            label=':green[Proceed to Analysis]',
            on_click=goto_data_analysis_widget,
            use_container_width=True
        )