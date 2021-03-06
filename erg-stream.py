import time
import csv
import threading

from datetime import datetime as dt
from enum import Enum
# import queue
from PIL import Image, ImageDraw, ImageFont

from pyrow import pyrow as pyrow
# from pyrow import simpyrow as pyrow
from pyrow.ergmanager import ErgManager


NUM_ERGS = 4
SWITCH_TIME = 30

LOG_FIELDNAMES = ['Time', 'Name', 'Distance']

DISTLOG_NAME = "ergdistances.csv"
DISTLOG_FIELDNAME = ['Time', 'Name', 'Erg', 'Distance']

OVERLAY = "v2.png"

BOX_X = [30, 150, 1060, 1180]
POS_Y = [635, 655, 680]
POSITIONS = {
    0: [(x, POS_Y[0]) for x in BOX_X],
    1: [(x, POS_Y[1]) for x in BOX_X],
    2: [(x, POS_Y[2]) for x in BOX_X],
}

def get_total_distance():
    total_distance = 0
    for erg_num in range(NUM_ERGS):
        with open(DISTLOG_NAME, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total_distance += int(row['Distance'])
    return total_distance

class Overlay(object):
    """docstring for Stream Overlay."""
    def __init__(self, ergs):
        super().__init__()
        self.base = Image.open(OVERLAY).convert('RGBA')
        try:
            self.vbigfnt = ImageFont.truetype('Pillow/Tests/fonts/arial.ttf', 32)
            self.bigfnt = ImageFont.truetype('Pillow/Tests/fonts/arial.ttf', 20)
            self.smallfnt = ImageFont.truetype('Pillow/Tests/fonts/arial.ttf', 16)
        except:
            self.vbigfnt = ImageFont.truetype('arial.ttf', 32)
            self.bigfnt = ImageFont.truetype('arial.ttf', 20)
            self.smallfnt = ImageFont.truetype('arial.ttf', 16)
        self.ergs = ergs

    def regenerate(self):
        txt = Image.new('RGBA', self.base.size, (255,255,255,0))
        d = ImageDraw.Draw(txt)
        d.text((600,10), "{:.0f}".format(get_total_distance()), font=self.vbigfnt, fill=(255,255,255,255))
        for erg_idx,erg in enumerate(self.ergs.ergs):
            d.text(POSITIONS[0][erg_idx], "{:.0f}m".format(erg.finish_distance), font=self.smallfnt, fill=(255,255,255,255))
            d.text(POSITIONS[1][erg_idx], "{:.0f}m".format(erg.distance), font=self.bigfnt, fill=(255,255,255,255))
            if False:
                min_val = int(status[erg_idx]['pace']//60)
                sec_val = int(status[erg_idx]['pace'] - min_val*60)
                d.text(POSITIONS[2][erg_idx], f"{min_val}:{sec_val:02d}", font=self.smallfnt, fill=(255,255,255,255))
        # out = Image.alpha_composite(self.base, txt)
        # out.save('overlay.png')
        txt.save('overlay.png')
        time.sleep(2)

class Erg(object):
    """docstring for Boat."""
    def __init__(self, erg_id, index, name, *, distance=0, finish_distance=2000, **kw):
        super().__init__()
        self.id = erg_id
        self.index = index
        self.name = name
        try:
            self.distance = distance
            self.finish_distance = finish_distance
        except AttributeError:
            pass

    @property
    def round_distance(self):
        return int(round(self.distance))

    def __repr__(self):
        return self.name

    def get_state(self):
        return {
            'name': self.name,
            'distance': self.distance,
            'finish_distance': self.finish_distance,
        }

    def save_erg(self):
        with open(DISTLOG_NAME) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=DISTLOG_FIELDNAME)
            writer.writerow({'Time': dt.now().isoformat(timespec='seconds'), 'Name': self.name, 'Erg': self.index+1, 'Distance': erg_obj.distance})

    def erg_update(self, erg_distance):
        self.distance = erg_distance

class Ergs(object):
    """docstring for Ergs."""
    def __init__(self, *, state=None):
        super().__init__()
        if state is None:
            self.ergs = []
        else:
            self.ergs = [Erg(**erg) for erg in state]

    def __repr__(self):
        return ', '.join([erg.__repr__() for erg in self.ergs])

    def get_state(self):
        return [erg.get_state() for erg in self.ergs]

    def add_erg(self, erg_id, index, name, *, finish_distance):
        erg = Erg(erg_id, index, name, finish_distance=finish_distance)
        self.ergs.insert(index, erg)

    def set_erg(self, index, name, *, finish_distance):
        self.ergs[index].name = name
        self.ergs[index].distance = 0
        self.ergs[index].finish_distance = finish_distance

    def save_erg(self, idx):
        self.ergs[idx].save_erg()

    def get_erg_by_id(self, erg_id):
        # print(f"Boats: {self.boats}")
        erg_list = [erg for erg in self.ergs if erg.id==erg_id]
        if len(erg_list)==1:
            return erg_list[0]

    def erg_update(self, erg_id, erg_distance):
        boat = self.get_erg_by_id(erg_id)
        if boat is not None:
            boat.erg_update(erg_distance)


def input_boat_details():
    print()
    valid = False
    while not valid:
        number = input("Enter erg number (1-4)\n--> ")
        if number.isdigit():
            valid = int(number) in (1, 2, 3, 4)
    number = int(number)
    name = input("Enter name\n--> ")
    distance = input("Enter distance\n--> ")
    distance = '2000' if distance=='' else distance
    while not distance.isdigit():
        distance = input("Enter distance as an integer\n--> ")
    distance = int(distance)
    return number-1, name, distance

def get_new_callback(ergs, ergs_write_lock, console_condition):
    def new_callback(erg):
        with console_condition:
            print("New erg: {}".format(erg))
            index, name, distance = input_boat_details()
            # Notifies main loop that asynchronous IO has occured
            console_condition.notify_all()
        with ergs_write_lock:
            ergs.add_erg(erg.id, index, name, finish_distance=distance)
        return name
    return new_callback

def get_update_callback(ergs, ergs_write_lock, overlay):
    def update_callback(erg):
        with ergs_write_lock:
            ergs.erg_update(erg.id, erg.data['distance'])
        erg_obj = ergs.get_erg_by_id(erg.id)
        if erg_obj:
            with open("erg{}.csv".format(erg_obj.index + 1), 'a') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDNAMES)
                writer.writerow({'Time': dt.now().isoformat(timespec='seconds'), 'Name': erg_obj.name, 'Distance': erg_obj.distance})
        overlay.regenerate()
    return update_callback

def display_menu():
    print()
    action = input(
        "Menu:\n"
        "   'quit' to quit\n"
        "   'view' to view boats\n"
        "   'add' to schedule boat\n"
        # "   Enter a number to start countdown\n"
        "--> "
    )
    print()
    return action

class AppState(Enum):
    exit = -1
    none = 0
    menu = 1
    boats = 2


def main():
    import os.path

    if not os.path.isfile(DISTLOG_NAME):
        print("Generating CSV Files")
        with open(DISTLOG_NAME, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=DISTLOG_FIELDNAME)
            writer.writeheader()

    for i in range(NUM_ERGS):
        fname = "erg{}.csv".format(i+1)
        if not os.path.isfile(fname):
            print("Generating CSV Files")
            with open(fname, 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=LOG_FIELDNAMES)
                writer.writeheader()

    console_condition = threading.Condition(lock=threading.Lock())
    ergs_write_lock = threading.Lock()
    ergs = Ergs()

    overlay = Overlay(ergs=ergs)

    # pipe_thread = threading.Thread(
    #     target=piper, args=(bumps,), name="pipe_thread", daemon=True)
    # pipe_thread.start()

    new_callback = get_new_callback(ergs, ergs_write_lock, console_condition)
    update_callback = get_update_callback(ergs, ergs_write_lock, overlay)

    ergman = ErgManager(
        pyrow,
        add_callback=new_callback,
        update_callback=update_callback,
        check_rate=2,
        update_rate=0.4,
    )

    app_state = AppState.none
    console_condition.acquire()
    print()
    print("Welcome to erg-streamer")
    while app_state is not AppState.exit:
        # print('step')
        # time.sleep(0.2)
        if app_state is AppState.none:
            try:
                print()
                print("CTRL-C to open the Menu")
                #Releases lock, waits until notified, then reacquires lock
                console_condition.wait()
            except KeyboardInterrupt:
                #Acquires lock if wait is broken, waiting on async
                # console_condition.acquire()
                app_state = AppState.menu
        elif app_state is AppState.menu:
            menu = False
            action = display_menu()
            if action == '':
                app_state = AppState.none
            elif action.lower().startswith('q'):
                app_state = AppState.exit
            elif action.lower().startswith('v'):
                app_state = AppState.boats
            elif action.lower().startswith('add'):
                index, name, distance = input_boat_details()
                with ergs_write_lock:
                    ergs.save_erg(index)
                    ergs.set_erg(index, name, finish_distance=distance)
            elif action.isdigit():
                pass
        elif app_state is AppState.boats:
            try:
                #Releases lock, waits until notified or 1s elapsed, then reacquires lock
                if not console_condition.wait(timeout=1):
                    pass
            except KeyboardInterrupt:
                #Acquires lock if wait is broken, waiting on async
                # console_condition.acquire()
                app_state = AppState.menu

    ergman.stop()



if __name__ == '__main__':
    main()
