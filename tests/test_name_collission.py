from pyinline import inline


@inline
def log_error(msg):
    x = 2
    print(msg, x)


x = 1
log_error("Oh no!")
print(x)
