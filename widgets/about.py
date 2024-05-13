import streamlit as st

def render_about():

    about_me_container = st.container()

    with about_me_container:
        text_col, photo_col = st.columns([3, 1])

        with text_col:
            st.write(
                """
                My name is [Balaji Kesavan](https://www.linkedin.com/in/balaji-kesavan/) and I am passionate about open source AI. I am always looking for ways to improve my skills and learn new things.
                This is my submission to [The future of AI is open](https://arctic-streamlit-hackathon.devpost.com/) hackathon. I hope you like it!

                You can access the source code for this project on [GitHub](https://github.com/balajikesavan90/future-of-ai-is-open-hackathon)
                """
            )
            
            with st.expander(':blue[What is Arctic Analytics?]', expanded=True):
                st.write(
                    """
                    Arctic Analytics is an AI tool that can 
                    - answer questions about your data.
                    - build charts and graphs from your data.
                    - help document and debug your codebase.
                        """
                )
            with st.expander(':blue[Does the AI have access to my data?]', expanded=True):
                st.write(
                    """
                    The AI model does not have access to your data. It does however have access to the metadata of your data. In particular, it has access to the 
                    - primary keys
                    - column names
                    - data types
                    - dataset description
                    - column descriptions
                    - output of the pandas describe method on your data
                    - first 5 rows of your data. 
                    """
                )
            with st.expander(':blue[What can the AI actually see?]', expanded=True):
                st.write(
                    """
                    After you load your data and starting engaging with the AI, you can view the prompt that the AI sees on your sidebar.
                    """
                )
    with photo_col:
        st.image('balaji.jpg', width=200, caption='Balaji Kesavan')
                