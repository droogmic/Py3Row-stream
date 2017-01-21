import queue
import threading
import time
import csv

NUM_ERGS = 4
RATE = 10
SWITCH_TIME = 10
LOG_FIELDNAMES = ['Name', 'Distance', 'Time']
def stint(name, distance):
    return {
        'name': name,
        'target': int(distance),
        'remain': int(distance),
    }
STINT_DICT = stint("", -1)
status = [STINT_DICT for _ in range(4)]
stint_queues = [[],[],[],[]]

exit_requested = False

def erg_monitor(erg_num):
    s = status[erg_num]
    switch_timer = 0
    last_time = time.time()
    while not exit_requested:
        diff_time = time.time() - last_time
        last_time = time.time()
        if switch_timer <= 0:
            if len(stint_queues[erg_num]) > 0:
                switch_timer = SWITCH_TIME
                s = stint_queues[erg_num].pop(0)
                print(f"Person {s['name']} rowing distance of {s['target']}m")
        elif s['remain'] > 0:
            s['remain'] -= int(diff_time * RATE)
        else:
            if switch_timer == SWITCH_TIME:
                with open(f'erg{erg_num}.csv', 'a') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDNAMES)
                    writer.writerow({'Name': s['name'], 'Distance': s['target'], 'Time': 10})
            print(f"Person {s['name']} finished distance of {s['target']}m, waiting {switch_timer:.0f}s")
            switch_timer -= diff_time
        time.sleep(2)

for i in range(NUM_ERGS):
    fname = f'erg{i}.csv'
    import os.path
    if not os.path.isfile(fname):
        print("Generating CSV Files")
        with open(fname, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDNAMES)
            writer.writeheader()

threads = []
for i in range(NUM_ERGS):
    t = threading.Thread(target=erg_monitor, args=(i,))
    t.start()
    threads.append(t)

while not exit_requested:
    response = input("Please enter erg 1 to 4 or 0 to exit: \n")
    response = int(response)
    if 1 <= response <= 4:
        rower_name = input("Name: ")
        distance = input("Distance /m: ")
        stint_queues[response-1].append(stint(rower_name, distance))
    else:
        exit_requested = True

# stop workers
for t in threads:
    t.join()
