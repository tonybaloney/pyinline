from pyinline import inline


@inline
def log_error():
    msg = "there has been an error!"
    print(msg)

@inline
def log_error2():
    msg = "there has been an error!"
    result = msg.upper()
    print(result)

log_error()
log_error2()