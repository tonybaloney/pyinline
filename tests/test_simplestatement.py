from pyinline import inline


@inline
def log_error():
    print("There has been an error!")


log_error()
