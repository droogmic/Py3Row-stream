import queue
import threading
import time
import csv
from PIL import Image, ImageDraw, ImageFont

NUM_ERGS = 4
RATE = 10
SWITCH_TIME = 10
LOG_FIELDNAMES = ['Name', 'Distance', 'Time']
def stint(name, distance):
    try:
        d = int(distance)
    except ValueError:
        print(f"Invalid distance {distance}, defaulting to 2k")
        d = 2000
    return {
        'name': name,
        'target': d,
        'remain': d,
    }
STINT_DICT = stint("", -1)

BOX_X = [30, 150, 1060, 1180]
POS_Y = [635, 655, 680]
POSITIONS = {
    0: [(x, POS_Y[0]) for x in BOX_X],
    1: [(x, POS_Y[1]) for x in BOX_X],
    2: [(x, POS_Y[2]) for x in BOX_X],
}
status_q = queue.Queue()
status = [STINT_DICT for _ in range(NUM_ERGS)]
stint_qs = [queue.Queue() for _ in range(NUM_ERGS)]
exit_requested = False

def erg_monitor(erg_num):
    switch_timer = 0
    last_time = time.time()
    while not exit_requested:
        s = status[erg_num]
        diff_time = time.time() - last_time
        last_time = time.time()
        if switch_timer <= 0:
            switch_timer = SWITCH_TIME
            _item = stint_qs[erg_num].get()
            if _item is None:
                break
            s = _item
            stint_qs[erg_num].task_done()
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
        status_q.put({'erg_num': erg_num, 'status': s})
        time.sleep(2)

def stream_overlay():
    base = Image.open("v2.png").convert('RGBA')
    bigfnt = ImageFont.truetype('Pillow/Tests/fonts/DejaVuSans.ttf', 20)
    smallfnt = ImageFont.truetype('Pillow/Tests/fonts/DejaVuSans.ttf', 16)
    while not exit_requested:
        txt = Image.new('RGBA', base.size, (255,255,255,0))
        d = ImageDraw.Draw(txt)
        for erg_num in range(NUM_ERGS):
            d.text(POSITIONS[0][erg_num], f"{status[erg_num]['remain']}m", font=smallfnt, fill=(255,255,255,255))
            d.text(POSITIONS[1][erg_num], f"{status[erg_num]['target']}m", font=bigfnt, fill=(255,255,255,255))
            d.text(POSITIONS[2][erg_num], f"1:58r20", font=smallfnt, fill=(255,255,255,255))
        # out = Image.alpha_composite(base, txt)
        # out.save('overlay.png')
        txt.save('overlay.png')
        time.sleep(1.2)

def status_getter():
    while not exit_requested:
        _item = status_q.get()
        if _item is None:
            break
        status[_item['erg_num']] = _item['status']
        status_q.task_done()

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

t = threading.Thread(target=stream_overlay)
t.start()
threads.append(t)

t = threading.Thread(target=status_getter)
t.start()
threads.append(t)

while not exit_requested:
    response = input("Please enter erg 1 to 4 or 0 to exit: \n")
    try:
        response = int(response)
        if 1 <= response <= 4:
            rower_name = input("Name: ")
            distance = input("Distance /m: ")
            stint_qs[response-1].put(stint(rower_name, distance))
        else:
            exit_requested = True
    except ValueError:
        print("Invalid number")

# stop workers
status_q.put(None)
for q in stint_qs:
    q.put(None)
for t in threads:
    t.join()
