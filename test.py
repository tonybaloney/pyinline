from pyinline import inline


@inline
def foobar():
    print("hello world!")


foobar()
