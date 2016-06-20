__author__ = 'Matt Barr'

from textproc_textrazor import textRazor
import textproc_sonos
import yaml, string, uuid, logging, re

class IntentAnalysis():
    def __init__(self, text, profile, dictionary):
        self._logger = logging.getLogger(__name__)
        self._logger.debug('Creating new IntentAnalysis with text "%s"' % text.lower())
        self.profile = profile
        exclude = set(string.punctuation)
        text = ''.join(ch for ch in text if ch not in exclude)
        self._text = text.lower()
        self.possible_intents = []
        self._dictionary = dictionary
        self._analyse()

    def _analyse(self):
        '''
        analyze text for possible intentions
        there are different plugins capable of processing text in differetn ways
        intentions are stored in a common format
        which class converts from the plugin response, to the common format?
        either all the plugins know about the common format, or the IA class knows about all the plugins.
        the plugins should know about the common format: that way only the plugins should need changing.
        writing a plugin should require only minimal editing of the IA class. Preferably none.

        it should be possible to alter the internal structure of the common format without the plugins
        knowing about it - which means the common format needs to be a class.
        _analyse should be capable for returning multiple intentions - but perhaps not in V1!
        '''
        intent = self.add_intent()
        textRazor(self.profile, self._dictionary).handle(intent)
        textproc_sonos.process(intent, self._dictionary)

        for intent in self.possible_intents:
            self._logger.info('Intent:')
            for chunk in intent.chunks:
                self._logger.info('\tChunk:')
                self._logger.info('\t\tWords: %s' % chunk.words)
                if not chunk.meaning:
                    self._logger.info('\t\t\tMeaning: None')
                else:
                    self._logger.info('\t\t\tMeaning: Type: %s, Value: %s' % (chunk.meaning.type, chunk.meaning.value))

    def add_intent(self):
        intent = Intent(self._text)
        self.possible_intents.append(intent)
        return intent

class Intent():
    def __init__(self, text):
        self._logger = logging.getLogger(__name__)
        self._logger.debug('Creating new Intent with text "%s"' % text)
        self.chunks = Chunks(text)

    def get_chunk_meaning_values(self, meaning_type=None):
        result = [chunk.meaning.value for chunk in self.chunks if chunk.meaning]
        if meaning_type:
            result = [chunk.meaning.value for chunk in self.chunks if chunk.meaning and \
                  chunk.meaning.type == meaning_type]
        return result

class Chunks():
    def __init__(self, text):
        self._logger = logging.getLogger(__name__)
        self.chunks = []
        self.add_chunk(words=text)

    def __iter__(self):
        for item in self.chunks:
            yield item

    def __getitem__(self, item):
        return self.chunks[item]

    def add_chunk(self, words):
        chunk = Chunk(words)
        self.chunks.append(chunk)
        return chunk

    def get_chunk(self, id):
        chunks = [chunk for chunk in self.chunks if chunk.id == id]
        return chunks[0] if len(chunks) else None

    def get_chunk_position(self, id):
        i = 0
        for chunk in self.chunks:
            if chunk.id == id:
                return i
            i += 1
        return None

    def split_chunk(self, words, meaning_value, meaning_type=None, **kwargs):

        # if chunk id kwarg provided...
        if 'id' in kwargs:

            id = kwargs['id']
            if id not in [chunk.id for chunk in self.chunks]:
                self._logger.warning('Chunk ID cannot be found in current Chunks: %s' % id)
                return None

            old_chunk = self.get_chunk(id)
            old_chunk_position = self.get_chunk_position(id)

            find_pos = old_chunk.words.find(words)
            if find_pos < 0:
                self._logger.warning('Words cannot be found in Chunk Words')
                self._logger.warning('Words: %s' % words)
                self._logger.warning('Chunk Words: %s' % old_chunk.words)
                return None

            # Delete old chunk
            self.chunks.remove(old_chunk)

            # Create the chunk to insert
            new_chunk = Chunk(words)
            new_chunk.add_meaning(type=meaning_type, value=meaning_value)

            split_words = [s.strip() for s in re.compile(r'\b%s\b' % words).split(old_chunk.words)]
            #split_words = [s.strip() for s in old_chunk.words.split(words)]
            print split_words

            if len(split_words[1]):
                post_chunk = Chunk(split_words[1])
                self.chunks.insert(old_chunk_position, post_chunk)

            self.chunks.insert(old_chunk_position, new_chunk)

            if len(split_words[0]):
                pre_chunk = Chunk(split_words[0])
                self.chunks.insert(old_chunk_position, pre_chunk)


        # if chunk number kwarg provided...
        elif 'chunk_number' in kwargs:
            chunk_number = kwargs['chunk_number']
            if chunk_number >= len(self.chunks):
                self._logger.warning('Chunk number cannot be found in current Chunks: %d' % chunk_number)
                return None
            return
        else:
            self._logger.warning('No Chunk provided')
            return None

        return

    def find_chunk_with_text(self, text):
        self._logger.debug('Finding Chunk: text: "%s"' % text)
        result = [chunk.id for chunk in self.chunks if re.search(r'\b%s\b' % text, chunk.words)]
        return result[0] if result else None

class Chunk():
    def __init__(self, words):
        self._logger = logging.getLogger(__name__)
        self._logger.debug('Creating new Chunk with words "%s"' % words)
        self.id = uuid.uuid4()
        self.words = words
        self.meaning = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_meaning(self, type, value):
        self.meaning = Meaning(type, value)


class Meaning():
    def __init__(self, type, value):
        self._logger = logging.getLogger(__name__)
        self._logger.debug('Creating new Meaning with type: %s and value: %s' % (type, value))
        self.type = type
        self.value = value



example_intention_analysis_1 = '''
full_text: play something by blahblahblah
possible_intentions:
    - intention:
        - chunk:
            words: play
            meaning:
                type: action
                value: play
        - chunk:
            words: something
            meaning: Null
        - chunk:
            words: by
            meaning:
                type: entity_pointer
                value: artist
        - chunk:
            words: jamiroquai
            meaning:
                type: artist
                value: jamiroquai
'''

example_intention_analysis_2 = '''
possible_intentions:
    - intention:
        - chunk:
            words: turn
            meaning:
                type: action
                value: set
        - chunk:
            words: the
            meaning: Null
        - chunk:
            words: volume
            meaning:
                type: property
                value: volume
        - chunk:
            words: down
            meaning:
                type: target value
                value: down
        - chunk:
            words: in the
            meaning: Null
        - chunk:
            words: kitchen
            meaning:
                type: location
                value: kitchen
'''

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    intent = Intent("play something by corrine bailey rae")
    intent.chunks.add_chunk('added chunk')
    intent.chunks.split_chunk('added', 'added', 'action', id=intent.chunks[1].id)
    intent.chunks.split_chunk('play', 'turn', 'action', id=intent.chunks[0].id)
    intent.chunks.split_chunk('by', None, None, id=intent.chunks[1].id)
    for chunk in intent.chunks:
        print chunk.id, ': ', chunk.words


