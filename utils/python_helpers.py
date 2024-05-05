import re

def remove_st_set_page_config(input_string):
    # This regex pattern matches 'st.set_page_config()' and its variants with any arguments
    pattern = r"st\.set_page_config\([^\)]*\)"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def remove_generate_report(input_string):
    # This regex pattern matches the line 'generate_report()'
    pattern = r"generate_report\(\)\n"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string