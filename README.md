
# Python JSON Parser

A simple top down JSON parser written in python, abiding by RFC 8259 and ECMA-404 standards.




## Usage

``` Python
from parser import JSON

parser = JSON()
json = parser.parse("test.json")
print(json)
```

The implementation currently only supports parsing file data.
The parser validates the given input on-the-go and in case of faulty structure throws an exception, indicating the line of error and invalid/expected token.
