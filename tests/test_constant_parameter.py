from pyinline import inline


@inline
def log_error(msg):
    print(msg)


log_error("there has been an error!!")
