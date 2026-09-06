import json

import pandas as pd

from arctic_analytics.streamlit.widgets.data_dictionary import (
    _restored_data_dictionary_frame,
    preserve_or_derive_primary_keys,
)


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


def test_restored_data_dictionary_frame_supports_record_lists():
    serialized_dictionary = json.dumps([
        {"Column Name": "id", "Data Type": "Int64", "Description": "Identifier", "Primary Key": True},
    ])

    result = _restored_data_dictionary_frame(serialized_dictionary)

    assert result.to_dict("records") == [
        {"Column Name": "id", "Data Type": "Int64", "Description": "Identifier", "Primary Key": True},
    ]


def test_restored_data_dictionary_frame_supports_indexed_dicts():
    serialized_dictionary = json.dumps({
        "id": {"Column Name": "id", "Data Type": "Int64", "Description": "Identifier"},
    })

    result = _restored_data_dictionary_frame(serialized_dictionary)

    assert result.index.tolist() == ["id"]
