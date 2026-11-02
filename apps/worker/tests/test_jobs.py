import fakeredis
from rq import Queue, SimpleWorker

from handball_worker.jobs import ping


def test_ping_direct() -> None:
    assert ping("x")["reply"] == "pong"


def test_ping_through_queue() -> None:
    conn = fakeredis.FakeStrictRedis()
    q = Queue("default", connection=conn)
    job = q.enqueue(ping, "hello")
    SimpleWorker([q], connection=conn).work(burst=True)
    result = job.return_value()
    assert result is not None
    assert result["payload"] == "hello"
