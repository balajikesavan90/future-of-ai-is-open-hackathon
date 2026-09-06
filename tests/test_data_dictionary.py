import pandas as pd

from arctic_analytics.streamlit.widgets.data_dictionary import preserve_or_derive_primary_keys


def test_preserve_or_derive_primary_keys_keeps_restored_selections():
    restored_dictionary = pd.DataFrame(
        {
            'Column Name': ['id', 'amount'],
            'Data Type': ['Int64', 'Float64'],
            'Primary Key': [True, False],
        }
    )

    result = preserve_or_derive_primary_keys(restored_dictionary, [])

    assert result['Primary Key'].tolist() == [True, False]


def test_preserve_or_derive_primary_keys_uses_metadata_for_new_dictionary():
    new_dictionary = pd.DataFrame(
        {
            'Column Name': ['id', 'amount'],
            'Data Type': ['Int64', 'Float64'],
        }
    )

    result = preserve_or_derive_primary_keys(new_dictionary, ['id'])

    assert result['Primary Key'].tolist() == [True, False]
