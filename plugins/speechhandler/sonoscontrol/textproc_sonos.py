__author__ = 'Matt Barr'

import os, yaml, logging

# set up logging
_logger = logging.getLogger(__name__)

# import dictionary
path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)

def process(intent, dictionary, profile=None):
    _process_dictionary(intent, dictionary)

def _process_dictionary(intent, dictionary):
    for meaning_type in dictionary:
        for item in dictionary[meaning_type]:
            for phrase in (x.lower() for x in dictionary[meaning_type][item]):
                text = phrase.lower()
                value = item
                target_chunk_id = intent.chunks.find_chunk_with_text(text)
                if target_chunk_id:
                    target_chunk = intent.chunks.get_chunk(target_chunk_id)
                    if not target_chunk.meaning:
                        intent.chunks.split_chunk(words=text, meaning_value=value, meaning_type=meaning_type,
                                                  id=target_chunk_id)

