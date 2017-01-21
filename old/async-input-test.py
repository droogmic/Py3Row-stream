import queue
import threading

num_worker_threads = 5

def do_work(item):
    if item['count']>0:
        print(f"{item['name']}: {item['count']}")
        item['count'] -= 1
        do_work(item)

def source():
    return ({'name': x, 'count': 5} for x in range(10))

def worker():
    while True:
        item = q.get()
        if item is None:
            break
        do_work(item)
        q.task_done()

q = queue.Queue()
threads = []
for i in range(num_worker_threads):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for item in source():
    q.put(item)

# block until all tasks are done
q.join()

# stop workers
for i in range(num_worker_threads):
    q.put(None)
for t in threads:
    t.join()
