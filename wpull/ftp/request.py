'''FTP conversation classes'''
import re

from wpull.abstract.request import CommonMixin
from wpull.errors import ProtocolError
import wpull.ftp.util


class Command(CommonMixin):
    '''FTP request command.

    Encoding is Latin-1.

    Attributes:
        name (str): The command. Usually 4 characters or less.
        argument (str): Optional argument for the command.
    '''
    def __init__(self, name=None, argument=''):
        self._name = None

        if name:
            self.name = name

        self.argument = argument

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value.upper()

    def parse(self, data):
        assert self.name is None
        assert not self.argument

        match = re.match(br'(\w+) ?([^\r\n]*)', data)

        if not match:
            raise ProtocolError('Failed to parse command.')

        self.name = match.group(1).decode('latin-1')
        self.argument = match.group(2).decode('latin-1')

    def to_bytes(self):
        return '{0} {1}\r\n'.format(self.name, self.argument).encode('latin-1')

    def to_dict(self):
        return {
            'name': self.name,
            'argument': self.argument,
        }


class Reply(CommonMixin):
    '''FTP reply.

    Encoding is always Latin-1.

    Attributes:
        code (int): Reply code.
        text (str): Reply message.
    '''
    def __init__(self, code=None, text=None):
        self.code = code
        self.text = text

    def parse(self, data):
        for line in data.splitlines(False):
            match = re.match(br'(\d{3}|^)([ -]?)(.*)', line)

            if not match:
                raise ProtocolError('Failed to parse reply.')

            if match.group(1) and match.group(2) == b' ':
                assert self.code is None
                self.code = int(match.group(1))

            if self.text is None:
                self.text = match.group(3).decode('latin-1')
            else:
                self.text += '\r\n{0}'.format(match.group(3).decode('latin-1'))

    def to_bytes(self):
        assert self.code is not None
        assert self.text is not None

        text_lines = self.text.splitlines(False)
        lines = []

        for row_num in range(len(text_lines)):
            line = text_lines[row_num]

            if row_num == len(text_lines) - 1:
                lines.append('{0} {1}\r\n'.format(self.code, line))
            else:
                lines.append('{0}-{1}\r\n'.format(self.code, line))

        return ''.join(lines).encode('latin-1')

    def to_dict(self):
        return {
            'code': self.code,
            'text': self.text
        }

    def code_tuple(self):
        '''Return a tuple of the reply code.'''
        return wpull.ftp.util.reply_code_tuple(self.code)
