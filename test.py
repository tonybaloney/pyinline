from ast import increment_lineno


from inline import inline


@inline
def foobar():
    print("hello world!")
