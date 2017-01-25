import queue
import threading
import time
import csv
from PIL import Image, ImageDraw, ImageFont
from pyrow import pyrow

#Create a dictionary of the different status states
ERG_state = ['Error', 'Ready', 'Idle', 'Have ID', 'N/A', 'In Use',
         'Pause', 'Finished', 'Manual', 'Offline']


ERG_stroke = ['Wait for min speed', 'Wait for acceleration', 'Drive', 'Dwelling', 'Recovery']

ERG_workout = ['Waiting begin', 'Workout row', 'Countdown pause', 'Interval rest',
           'Work time inverval', 'Work distance interval', 'Rest end time', 'Rest end distance',
           'Time end rest', 'Distance end rest', 'Workout end', 'Workout terminate',
           'Workout logged', 'Workout rearm']

ERG_command = ['CSAFE_GETSTATUS_CMD', 'CSAFE_PM_GET_STROKESTATE', 'CSAFE_PM_GET_WORKOUTSTATE']

NUM_ERGS = 4
RATE = 10
SWITCH_TIME = 30
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

def erg_monitor(erg_num, erg):
    switch_timer = 0
    last_time = time.time()
    
    #prime status number
    cstate = -1
    cstroke = -1
    cworkout = -1

    while not exit_requested:
        if ERG_state[erg.get_status()['status']] != 'Ready':
            print(ERG_state[erg.get_status()['status']])
            print(erg.get_workout())
        s = status[erg_num]
        diff_time = time.time() - last_time
        last_time = time.time()
        monitor = erg.get_monitor()
        workout = erg.get_workout()
        # if switch_timer <= 0:
        if workout['state'] == 11:
            print(f"Workout erg {erg_num} finished")
            switch_timer = SWITCH_TIME
            _item = stint_qs[erg_num].get()
            if _item is None:
                break
            s = _item
            # erg.set_workout(distance=s['target'])
            # erg.set_workout(distance=s['target'], split=120)
            # time.sleep(1)
            stint_qs[erg_num].task_done()
            print(f"Person {s['name']} rowing distance of {s['target']}m")
        elif s['remain'] > 0:
            # s['remain'] = s['target']- monitor['distance']
            s['remain'] = monitor['distance']
            s['pace'] = monitor['pace']
        else:
            if switch_timer == SWITCH_TIME:
                with open(f'erg{erg_num}.csv', 'a') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDNAMES)
                    writer.writerow({'Name': s['name'], 'Distance': s['target'], 'Time': 10})
            # print(f"Person {s['name']} finished distance of {s['target']}m, waiting {switch_timer:.0f}s")
            switch_timer -= diff_time
        status_q.put({'erg_num': erg_num, 'status': s})
        time.sleep(2)

def stream_overlay():
    base = Image.open("v2.png").convert('RGBA')
    vbigfnt = ImageFont.truetype('Pillow/Tests/fonts/arial.ttf', 32)
    bigfnt = ImageFont.truetype('Pillow/Tests/fonts/arial.ttf', 20)
    smallfnt = ImageFont.truetype('Pillow/Tests/fonts/arial.ttf', 16)
    while not exit_requested:
    
        total_distance = 0
        for erg_num in range(NUM_ERGS):
            with open(f'erg{erg_num}.csv', 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    total_distance += int(row['Distance'])
    
        txt = Image.new('RGBA', base.size, (255,255,255,0))
        d = ImageDraw.Draw(txt)
        d.text((600,10), f"{total_distance:.0f}", font=vbigfnt, fill=(255,255,255,255))
        for erg_num in range(NUM_ERGS):
            d.text(POSITIONS[0][erg_num], f"{status[erg_num]['remain']:.0f}m", font=smallfnt, fill=(255,255,255,255))
            d.text(POSITIONS[1][erg_num], f"{status[erg_num]['target']:.0f}m", font=bigfnt, fill=(255,255,255,255))
            if 'pace' in status[erg_num]:
                min_val = int(status[erg_num]['pace']//60)
                sec_val = int(status[erg_num]['pace'] - min_val*60)
                d.text(POSITIONS[2][erg_num], f"{min_val}:{sec_val:02d}", font=smallfnt, fill=(255,255,255,255))
        # out = Image.alpha_composite(base, txt)
        # out.save('overlay.png')
        txt.save('overlay.png')
        time.sleep(2)

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

ergs = list(pyrow.find())
if len(ergs) == 0:
    exit("No ergs found.")
print(ergs)

for i in range(NUM_ERGS):
    erg = pyrow.PyRow(ergs[i])
    print("Connected to erg.")
    t = threading.Thread(target=erg_monitor, args=(i,erg))
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
