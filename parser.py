import io
import re
from enum import IntEnum


class JSON:
    class __NonTerminals(IntEnum):
        JSON = 261
        VALUE = 262
        OBJECT = 263
        ARRAY = 264
        FIELDS = 265
        FIELD = 266
        FIELDS_REST = 267
        ITEMS = 268
        ITEMS_REST = 269

    class __Terminals(IntEnum):
        INVALID_TOKEN = -2
        EOF = 0
        STRING = 256
        NUMBER = 257
        TRUE = 258
        FALSE = 259
        NULL = 260

    __keywords = {
        "true": __Terminals.TRUE,
        "false": __Terminals.FALSE,
        "null": __Terminals.NULL
    }

    __keywordToValues = {
        __Terminals.TRUE: True,
        __Terminals.FALSE: False,
        __Terminals.NULL: None
    }

    __jump_table = {
        __NonTerminals.JSON: {
            __Terminals.STRING: [__NonTerminals.VALUE],
            __Terminals.NUMBER: [__NonTerminals.VALUE],
            "{": [__NonTerminals.VALUE],
            "[": [__NonTerminals.VALUE],
            __Terminals.TRUE: [__NonTerminals.VALUE],
            __Terminals.FALSE: [__NonTerminals.VALUE],
            __Terminals.NULL: [__NonTerminals.VALUE],
            __Terminals.EOF: []
        },
        __NonTerminals.VALUE: {
            __Terminals.STRING: [__Terminals.STRING],
            __Terminals.NUMBER: [__Terminals.NUMBER],
            "{": [__NonTerminals.OBJECT],
            "[": [__NonTerminals.ARRAY],
            __Terminals.TRUE: [__Terminals.TRUE],
            __Terminals.FALSE: [__Terminals.FALSE],
            __Terminals.NULL: [__Terminals.NULL]
        },
        __NonTerminals.OBJECT: {
            "{": ["{", __NonTerminals.FIELDS, "}"]
        },
        __NonTerminals.FIELDS: {
            __Terminals.STRING: [__NonTerminals.FIELD, __NonTerminals.FIELDS_REST],
            "}": []
        },
        __NonTerminals.FIELD: {
            __Terminals.STRING: [__Terminals.STRING, ":", __NonTerminals.VALUE]
        },
        __NonTerminals.FIELDS_REST: {
            ",": [",", __NonTerminals.FIELD, __NonTerminals.FIELDS_REST],
            "}": []
        },
        __NonTerminals.ARRAY: {
            "[": ["[", __NonTerminals.ITEMS, "]"]
        },
        __NonTerminals.ITEMS: {
            __Terminals.STRING: [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            __Terminals.NUMBER: [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            "{": [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            "[": [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            __Terminals.TRUE: [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            __Terminals.FALSE: [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            __Terminals.NULL: [__NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            "]": []
        },
        __NonTerminals.ITEMS_REST: {
            ",": [",", __NonTerminals.VALUE, __NonTerminals.ITEMS_REST],
            "]": []
        }
    }

    __file = None
    __cache = None
    __line = 1

    def __get_token(self):
        while True:
            c = self.__cache or self.__file.read(1)
            if not c:
                return {"tag": self.__Terminals.EOF, "lexeme": None}
            if c == "\n" or c == "\r" or c == "\t" or c == " ":
                self.__cache = None
                if c == "\n":
                    self.__line += 1
                continue
            # parse string
            if c == '"':
                lexeme = ""
                while True:
                    self.__cache = self.__cache or self.__file.read(1)
                    # end string parsing
                    if self.__cache == '"' or not self.__cache:
                        self.__cache = None
                        break
                    # parse escape sequence
                    lexeme += self.__cache
                    if self.__cache == "\\":
                        self.__cache = self.__file.read(1)
                        match self.__cache:
                            case '"' | "\\" | "/" | "b" | "f" | "n" | "r" | "t":
                                lexeme += self.__cache
                                self.__cache = None
                                continue
                            case "u":
                                lexeme += self.__cache
                                for i in range(4):
                                    self.__cache = self.__file.read(1)
                                    if re.match("[a-fA-F0-9]", self.__cache):
                                        lexeme += self.__cache
                                        self.__cache = None
                                    else:
                                        return {"tag": self.__Terminals.INVALID_TOKEN, "lexeme": self.__cache}
                            case _:
                                token = {"tag": self.__Terminals.INVALID_TOKEN, "lexeme": self.__cache}
                                self.__cache = None
                                return token
                    else:
                        self.__cache = None
                return {"tag": self.__Terminals.STRING, "lexeme": lexeme}
            # parse keyword
            elif c.isalpha():
                lexeme = c
                while True:
                    self.__cache = self.__file.read(1)
                    if not self.__cache.isalpha():
                        break
                    lexeme += self.__cache
                new_tag = self.__keywords.get(lexeme)
                new_lexeme = self.__keywordToValues.get(new_tag)
                return {"tag": new_tag or self.__Terminals.INVALID_TOKEN,
                        "lexeme": new_lexeme if new_lexeme is not None else lexeme}
            # parse number
            elif c.isnumeric() or c == '-':
                is_int = True
                lexeme = c
                # parse int
                while True:
                    self.__cache = self.__file.read(1)
                    if self.__cache.isnumeric():
                        if c == "0":
                            return {"tag": self.__Terminals.INVALID_TOKEN, "lexeme": lexeme}
                        lexeme += self.__cache
                    else:
                        break
                # parse float
                if self.__cache == ".":
                    is_int = False
                    lexeme += self.__cache
                    self.__cache = self.__file.read(1)
                    if self.__cache.isnumeric():
                        lexeme += self.__cache
                    else:
                        return {"tag": self.__Terminals.INVALID_TOKEN, "lexeme": lexeme}
                    while True:
                        self.__cache = self.__file.read(1)
                        if self.__cache.isnumeric():
                            lexeme += self.__cache
                        else:
                            break
                    if self.__cache == "E" or self.__cache == "e":
                        lexeme += self.__cache
                        self.__cache = self.__file.read(1)
                        if self.__cache == "+" or self.__cache == "-":
                            lexeme += self.__cache
                            self.__cache = self.__file.read(1)
                        if self.__cache.isnumeric():
                            lexeme += self.__cache
                            while True:
                                self.__cache = self.__file.read(1)
                                if self.__cache.isnumeric():
                                    lexeme += self.__cache
                                else:
                                    break
                        else:
                            return {"tag": self.__Terminals.INVALID_TOKEN, "lexeme": lexeme}
                return {"tag": self.__Terminals.NUMBER, "lexeme": int(lexeme) if is_int else float(lexeme)}
            # separators
            self.__cache = None
            return {"tag": c, "lexeme": None}

    def __get_production(self, nt, t):
        return self.__jump_table.get(nt, {}).get(t)

    def __load_file(self, fn):
        self.__file = open(fn, encoding="utf-8")

    def __load_str(self, string):
        buffer = io.StringIO()
        buffer.write(string)
        buffer.seek(0)
        self.__file = buffer

    def parsef(self, fn):
        self.__load_file(fn)
        res = self.__parse()
        self.__file.close()
        return res

    def parses(self, string):
        self.__load_str(string)
        return self.__parse()

    def __parse(self):
        self.__line = 1
        self.__cache = None
        token = self.__get_token()
        stack = [self.__Terminals.EOF, self.__NonTerminals.JSON]
        json = None
        nesting = []
        parsingDict = False
        parsingArray = False
        currentKey = None
        while True:
            top = stack[-1]
            if top == self.__Terminals.EOF:
                if token.get("tag") == self.__Terminals.EOF:
                    # parsing finished without errors
                    break
                else:
                    raise Exception(f"SYNTAX ERROR: unexpected EOF while parsing.")
            # terminal on stack
            if type(top) is str or self.__Terminals.STRING.value <= top <= self.__Terminals.NULL.value:
                # match terminal and reduce stack
                tag = token.get("tag")
                if tag == top:
                    match tag:
                        case "]":
                            parsingArray = False
                            json = nesting.pop()
                        case "}":
                            parsingDict = False
                            currentKey = None
                            json = nesting.pop()
                        case self.__Terminals.STRING:
                            if type(nesting[-1]) is dict:
                                if currentKey:
                                    nesting[-1].update({currentKey: token.get("lexeme")})
                                    currentKey = None
                                else:
                                    currentKey = token.get("lexeme")
                            elif type(nesting[-1]) is list:
                                nesting[-1].append(token.get("lexeme"))
                            else:
                                json = token.get("lexeme")
                        case (self.__Terminals.NUMBER | self.__Terminals.TRUE |
                              self.__Terminals.FALSE | self.__Terminals.NULL):
                            if parsingDict and currentKey:
                                nesting[-1].update({currentKey: token.get("lexeme")})
                                currentKey = None
                            elif parsingArray:
                                nesting[-1].append(token.get("lexeme"))
                            else:
                                json = token.get("lexeme")
                    stack.pop()
                    token = self.__get_token()
                else:
                    raise Exception(
                        f"SYNTAX ERROR: unexpected token {token.get('lexeme') or token.get('tag')} "
                        f"at line {self.__line}. "
                        f"Expected a <{top.name}>")
                    # non-terminal on stack
            else:
                # get production body and push to stack
                prod = self.__get_production(top, token.get("tag"))
                if prod is None:
                    raise Exception(
                        f"SYNTAX ERROR: unexpected token {token.get('lexeme') or token.get('tag')} "
                        f"at line {self.__line}. "
                        f"Expected a <{top.name}>")
                if self.__NonTerminals.OBJECT in prod:
                    new_dict = {}
                    if parsingDict and currentKey:
                        nesting[-1].update({currentKey: new_dict})
                        currentKey = None
                        nesting.append(new_dict)
                    elif parsingArray:
                        nesting[-1].append(new_dict)
                        parsingDict = True
                        nesting.append(new_dict)
                    else:
                        parsingDict = True
                        currentKey = None
                        nesting.append(new_dict)
                elif self.__NonTerminals.ARRAY in prod:
                    new_arr = []
                    if parsingDict and currentKey:
                        nesting[-1].update({currentKey: new_arr})
                        currentKey = None
                        nesting.append(new_arr)
                        parsingArray = True
                    elif parsingArray:
                        new_arr = []
                        nesting[-1].append(new_arr)
                        nesting.append(new_arr)
                    else:
                        parsingArray = True
                        nesting.append(new_arr)
                stack.pop()
                stack.extend(prod[::-1])
        return json
