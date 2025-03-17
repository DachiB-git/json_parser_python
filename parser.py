import re
import time

from enum import IntEnum

INVALID_TOKEN = -2
EPS = -1


class Terminals(IntEnum):
    EOF = 0
    STRING = 256
    NUMBER = 257
    TRUE = 258
    FALSE = 259
    NULL = 260


class NonTerminals(IntEnum):
    JSON = 261
    VALUE = 262
    OBJECT = 263
    ARRAY = 264
    FIELDS = 265
    FIELD = 266
    FIELDS_REST = 267
    ITEMS = 268
    ITEMS_REST = 269


file = None
cache = None
line = 1
jump_table = {}

keywords = {
    "true": Terminals.TRUE,
    "false": Terminals.FALSE,
    "null": Terminals.NULL
}

keywordToValues = {
    Terminals.TRUE: True,
    Terminals.FALSE: False,
    Terminals.NULL: None
}


def load_file(fn):
    return open(fn, encoding="utf-8")


# lexer
def get_token():
    global file, cache, line
    c = None
    while True:
        c = cache or file.read(1)
        if not c:
            return {"tag": Terminals.EOF, "lexeme": None}
        if c == "\n" or c == "\r" or c == "\t" or c == " ":
            cache = None
            if c == "\n":
                line += 1
            continue
        # parse string
        if c == '"':
            lexeme = ""
            while True:
                cache = cache or file.read(1)
                # end string parsing
                if cache == '"' or not cache:
                    cache = None
                    break
                # parse escape sequence
                lexeme += cache
                if cache == "\\":
                    cache = file.read(1)
                    match cache:
                        case '"' | "\\" | "/" | "b" | "f" | "n" | "r" | "t":
                            lexeme += cache
                            cache = None
                            continue
                        case "u":
                            lexeme += cache
                            for i in range(4):
                                cache = file.read(1)
                                if re.match("[a-fA-F0-9]", cache):
                                    lexeme += cache
                                    cache = None
                                else:
                                    return {"tag": INVALID_TOKEN, "lexeme": cache}
                        case _:
                            token = {"tag": INVALID_TOKEN, "lexeme": cache}
                            cache = None
                            return token
                else:
                    cache = None
            return {"tag": Terminals.STRING, "lexeme": lexeme}
        # parse keyword
        elif c.isalpha():
            lexeme = c
            while True:
                cache = file.read(1)
                if not cache.isalpha():
                    break
                lexeme += cache
            ctag = keywords.get(lexeme)
            return {"tag": ctag or INVALID_TOKEN, "lexeme": keywordToValues.get(ctag)}
        # parse number
        elif c.isnumeric() or c == '-':
            is_int = True
            lexeme = c
            # parse int
            while True:
                cache = file.read(1)
                if cache.isnumeric():
                    if c == "0":
                        return {"tag": INVALID_TOKEN, "lexeme": lexeme}
                    lexeme += cache
                else:
                    break
            # parse float
            if cache == ".":
                is_int = False
                lexeme += cache
                cache = file.read(1)
                if cache.isnumeric():
                    lexeme += cache
                else:
                    return {"tag": INVALID_TOKEN, "lexeme": lexeme}
                while True:
                    cache = file.read(1)
                    if cache.isnumeric():
                        lexeme += cache
                    else:
                        break
                if cache == "E" or cache == "e":
                    lexeme += cache
                    cache = file.read(1)
                    if cache == "+" or cache == "-":
                        lexeme += cache
                        cache = file.read(1)
                    if cache.isnumeric():
                        lexeme += cache
                        while True:
                            cache = file.read(1)
                            if cache.isnumeric():
                                lexeme += cache
                            else:
                                break
                    else:
                        return {"tag": INVALID_TOKEN, "lexeme": lexeme}
            return {"tag": Terminals.NUMBER, "lexeme": int(lexeme) if is_int else float(lexeme)}
        # separators
        cache = None
        return {"tag": c, "lexeme": None}


def init_jump_table():
    global jump_table
    jump_table[NonTerminals.JSON] = {
        Terminals.STRING: [NonTerminals.VALUE],
        Terminals.NUMBER: [NonTerminals.VALUE],
        "{": [NonTerminals.VALUE],
        "[": [NonTerminals.VALUE],
        Terminals.TRUE: [NonTerminals.VALUE],
        Terminals.FALSE: [NonTerminals.VALUE],
        Terminals.NULL: [NonTerminals.VALUE],
        Terminals.EOF: []
    }
    jump_table[NonTerminals.VALUE] = {
        Terminals.STRING: [Terminals.STRING],
        Terminals.NUMBER: [Terminals.NUMBER],
        "{": [NonTerminals.OBJECT],
        "[": [NonTerminals.ARRAY],
        Terminals.TRUE: [Terminals.TRUE],
        Terminals.FALSE: [Terminals.FALSE],
        Terminals.NULL: [Terminals.NULL]
    }
    jump_table[NonTerminals.OBJECT] = {
        "{": ["{", NonTerminals.FIELDS, "}"]
    }
    jump_table[NonTerminals.FIELDS] = {
        Terminals.STRING: [NonTerminals.FIELD, NonTerminals.FIELDS_REST],
        "}": []
    }
    jump_table[NonTerminals.FIELD] = {
        Terminals.STRING: [Terminals.STRING, ":", NonTerminals.VALUE]
    }
    jump_table[NonTerminals.FIELDS_REST] = {
        ",": [",", NonTerminals.FIELD, NonTerminals.FIELDS_REST],
        "}": []
    }
    jump_table[NonTerminals.ARRAY] = {
        "[": ["[", NonTerminals.ITEMS, "]"]
    }
    jump_table[NonTerminals.ITEMS] = {
        Terminals.STRING: [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        Terminals.NUMBER: [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        "{": [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        "[": [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        Terminals.TRUE: [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        Terminals.FALSE: [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        Terminals.NULL: [NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        "]": []
    }
    jump_table[NonTerminals.ITEMS_REST] = {
        ",": [",", NonTerminals.VALUE, NonTerminals.ITEMS_REST],
        "]": []
    }


def get_production(nt, t):
    return jump_table.get(nt, {}).get(t)


if __name__ == '__main__':
    start = time.time()
    file = load_file("generated_big.json")
    init_jump_table()
    token = get_token()
    top = None
    prod = None
    stack = [Terminals.EOF, NonTerminals.JSON]
    json = None
    nesting = []
    tag = None
    parsingDict = False
    parsingArray = False
    currentKey = None
    while True:
        top = stack[-1]
        if top == Terminals.EOF:
            if token.get("tag") == Terminals.EOF:
                print("SYNTAX CHECK FINISHED")
                break
            else:
                raise Exception(f"SYNTAX ERROR: unexpected EOF while parsing.")
        # terminal on stack
        if type(top) is str or Terminals.STRING.value <= top <= Terminals.NULL.value:
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
                    case Terminals.STRING:
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
                    case Terminals.NUMBER | Terminals.TRUE | Terminals.FALSE | Terminals.NULL:
                        if parsingDict and currentKey:
                            nesting[-1].update({currentKey: token.get("lexeme")})
                            currentKey = None
                        elif parsingArray:
                            nesting[-1].append(token.get("lexeme"))
                        else:
                            json = token.get("lexeme")
                stack.pop()
                token = get_token()
            else:
                raise Exception(
                    f"SYNTAX ERROR: unexpected token {token.get('lexeme') or token.get('tag')} at line {line}. "
                    f"Expected a <{top.name}>")
        # non-terminal on stack
        else:
            # get production body and push to stack
            prod = get_production(top, token.get("tag"))
            if prod is None:
                raise Exception(
                    f"SYNTAX ERROR: unexpected token {token.get('lexeme') or token.get('tag')} at line {line}. "
                    f"Expected a <{top.name}>")
            if NonTerminals.OBJECT in prod:
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
            elif NonTerminals.ARRAY in prod:
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
    print(json)
    # for (k, v) in json[0].items():
    #     print(f"{k} : {v}")
    file.close()
    end = time.time()
    print(round(end - start, 3))

# TODO : add ECMA 404 standard parsing grammar DONE
# TODO : add float parsing DONE
# TODO : optimize parsing logic and branching
# TODO : add duplicate key checking in dicts
# The JSON interchange format used in this specification is exactly that described by RFC 4627 with two exceptions:
# The top level JSONText production of the ECMAScript JSON grammar may consist of
# any JSONValue rather than being restricted to being a JSONObject or a JSONArray as specified by RFC 4627.
