from pyinline import inline


@inline
def log_error(msg):
    result = msg.upper()
    print(result)


log_error("Oh no!")
