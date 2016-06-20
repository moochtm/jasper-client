__author__ = 'Matt Barr'

import textrazor
import yaml
import os, logging

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)

FREEBASE_FILTERS = os.path.join(dir_path, 'freebase_filters.yaml')
DBPEDIA_FILTERS = os.path.join(dir_path, 'dbpedia_filters.yaml')


class textRazor():
    def __init__(self, profile, dictionary):
        self._logger = logging.getLogger(__name__)
        self.profile = profile
        self.freebase_filters = yaml.load(open(FREEBASE_FILTERS, 'r'))
        self.dbpedia_filters = yaml.load(open(DBPEDIA_FILTERS, 'r'))
        self.dictionary = dictionary
        textrazor.api_key = self.profile['textrazor']['apiKey']
        self.client = textrazor.TextRazor()

    def handle(self, intent):
        text = intent.chunks[0].words
        self.client.set_extractors(["words", "entities"])
        self.client.set_entity_freebase_type_filters(self._get_freebase_filters())
        self.client.set_entity_dbpedia_type_filters(self._get_dbpedia_filters())
        response = self.client.analyze(text)

        words = []
        for word in response.words():
            words.append({'text': word.token, 'penn': word.part_of_speech})

        entities = []
        for entity in response.entities():
            entities.append({'text': entity.matched_text, 'type': self._get_entity_type(entity.freebase_types, entity.dbpedia_types)})

        analysis = {
            'words': words,
            'entities': entities
        }

        self._logger.info("NLP_TextRazor analysis: %s" % analysis)

        '''
        NLP_TextRazor analysis: {'entities': [{'text': u'JAMES BROWN', 'type': 'artist'}],
            'words': [{'text': u'PLAY', 'penn': u'VB'}, {'text': u'SOMETHING', 'penn': u'NN'}, {'text': u'BY', 'penn': u'IN'},
            {'text': u'JAMES', 'penn': u'NNP'}, {'text': u'BROWN', 'penn': u'NNP'}, {'text': u'.', 'penn': u'.'}]}
        Play
        '''
        # we're converting the full text to a list of multi-word chunks
        # try looking at each word in words in turn
        # named_entities should be checked for first
        for entity in analysis['entities']:
            text = entity['text'].lower()
            type = entity['type'].lower()
            target_chunk_id = intent.chunks.find_chunk_with_text(text)
            intent.chunks.split_chunk(words=text, meaning_value=text, meaning_type=type, id=target_chunk_id)

        # actions should be checked for next
        for word in analysis['words']:
            if word['penn'] == 'VB' or word['penn'] == 'VBP':
                for action in self.dictionary['action']:
                    if word['text'].lower() in (x.lower() for x in self.dictionary['action'][action]):
                        text = word['text'].lower()
                        type = 'action'
                        value = action
                        target_chunk_id = intent.chunks.find_chunk_with_text(text)
                        intent.chunks.split_chunk(words=text, meaning_value=value, meaning_type=type, id=target_chunk_id)

        return

    def _get_entity_type(self, freebase_types=None, dbpedia_types=None):
        # build types ranking dic
        types = {}
        for t in self.freebase_filters:
            if t not in types:
                types[t] = 0
        for t in self.dbpedia_filters:
            if t not in types:
                types[t] = 0
        for t in freebase_types:
            for u in self.freebase_filters:
                if self.freebase_filters[u]:
                    for v in self.freebase_filters[u]:
                        if t == v:
                            types[u] += 1
        for t in dbpedia_types:
            for u in self.dbpedia_filters:
                if self.dbpedia_filters[u]:
                    for v in self.dbpedia_filters[u]:
                        if t == v:
                            types[u] += 1
        current_score = 0
        current_type = 'none'
        for t in types:
            if types[t] > current_score:
                current_score = types[t]
                current_type = t
        return current_type

    def _get_freebase_filters(self):
        filters = []
        for t in self.freebase_filters:
            if self.freebase_filters[t]:
                for u in self.freebase_filters[t]:
                    filters.append(u)
        return filters

    def _get_dbpedia_filters(self):
        filters = []
        for t in self.dbpedia_filters:
            if self.dbpedia_filters[t]:
                for u in self.dbpedia_filters[t]:
                    filters.append(u)
        return filters