from twisted.python.failure import Failure
from twisted.internet.defer import maybeDeferred, Deferred, DeferredList
from twisted.internet.defer import succeed, fail
from twisted.internet.defer import inlineCallbacks as future_generator
from twisted.internet.defer import returnValue  # XXX how to do in asyncio?
from twisted.internet.interfaces import IReactorTime

from txaio.interfaces import IFailedFuture
from txaio import config

# don't see how it *couldn't* be None, but...
if config.loop is None:
    from twisted.internet import reactor
    config.loop = reactor

using_twisted = True
using_asyncio = False


class FailedFuture(IFailedFuture):
    """
    XXX provide an abstract-base-class for IFailedFuture or similar,
    probably. For consistency between asyncio/twisted.

    ...i.e. to be explicit about what methods and variables may be
    used. Currently:

    .type
    .value
    .traceback

    .printTraceback
    """
    pass


FailedFuture.register(Failure)


def create_future(result=None, error=None):
    if result is not None and error is not None:
        raise ValueError("Cannot have both result and error.")

    f = Deferred()
    if result != None:
        resolve(f, result)
    elif error != None:
        reject(f, error)
    return f

# maybe delete, just use create_future()
def create_future_success(result):
    return succeed(result)


# maybe delete, just use create_future()
def create_future_error(error=None):
    return fail(create_failure(error))


# maybe rename to call()?
def as_future(fun, *args, **kwargs):
    return maybeDeferred(fun, *args, **kwargs)


def call_later(delay, fun, *args, **kwargs):
    return IReactorTime(config.reactor).callLater(seconds, fun, *args, **kw)


def resolve(future, result=None):
    future.callback(result)


def reject(future, error=None):
    if error is None:
        error = create_failure()
    elif isinstance(error, Exception):
        error = Failure(error)
    else:
        assert isinstance(error, IFailedFuture)
    future.errback(error)


def create_failure(exception=None):
    """
    Create a Failure instance.

    if ``exception`` is None (the default), we MUST be inside an
    "except" block. This encapsulates the exception into an object
    that implements IFailedFuture
    """
    if exception:
        return Failure(exception)
    return Failure()


def add_callbacks(future, callback, errback):
    """
    callback or errback may be None, but at least one must be
    non-None.
    """
    assert future is not None
    if callback is None:
        assert errback is not None
        future.addErrback(errback)
    else:
        # Twisted allows errback to be None here
        future.addCallbacks(callback, errback)
    return future


def gather(futures, consume_exceptions=True):
    def completed(res):
        rtn = []
        for (ok, value) in res:
            rtn.append(value)
            if not ok and not consume_exceptions:
                value.raiseException()
        return rtn

    # XXX if consume_exceptions is False in asyncio.gather(), it will
    # abort on the first raised exception -- should we set
    # fireOnOneErrback=True (if consume_exceptions=False?)
    dl = DeferredList(list(futures), consumeErrors=consume_exceptions)
    # we unpack the (ok, value) tuples into just a list of values, so
    # that the callback() gets the same value in asyncio and Twisted.
    add_callbacks(dl, completed, None)
    return dl
