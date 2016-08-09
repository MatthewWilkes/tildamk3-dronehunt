### Author: Matthew Wilkes
### Description: Shoot down unauthorised flying toys
### Category: Games 
### License: MIT
### Appname : DroneHunt

import buttons
import ugfx
import micropython
import pyb
from dialogs import prompt_boolean, notice
import gc

crosshair_x = 100
crosshair_y = 100
score = 0
GROUND_1 = ugfx.html_color(0x804000)
GROUND_2 = ugfx.html_color(0xf05030)
GRASS = ugfx.html_color(0x4DBD33)
SKIES = (
    None,
    ugfx.html_color(0xA2B5BB),
    ugfx.html_color(0x91C3E0),
    ugfx.html_color(0x87CEFA),
    ugfx.html_color(0x4080DF),
    ugfx.html_color(0x1249C5),
    ugfx.html_color(0x082978),
)
QUADCOPTER_BODY = ugfx.BLACK
QUADCOPTER_BODY_SIZE = 5
SCREEN_DURATION = 100
ENEMY_FREQUENCY = 2800
next_change = 0
next_enemy = 0
animation_frame = 0
pixels = 0
tmc_count = 0
last_crosshair_move = 0
level = 1

def random_choice(objs):
    # We don't have import random :(
    return objs[pyb.rng() % len(objs)]

#@micropython.native
def get_background_pixel(x, y):
    y = 240 - y
    global pixels
    pixels += 1
    if y < 40:
        # this is the sub-ground, use sonic style checkerboard
        x_coord = x // 20
        y_coord = y // 20
        if x_coord % 2 == y_coord % 2:
            return GROUND_1
        else:
            return GROUND_2
    elif y < 50:
        # This is the grass
        return GRASS
    else:
        return SKIES[level]


def redraw_whole_bg():
    ugfx.clear(SKIES[level])
    ugfx.area(0, 191, 320, 10, GRASS)
    ugfx.area(0, 201, 320, 40, GROUND_2)
    redraw_bg_range(0, 201, 320, 240)


#@micropython.viper
def redraw_bg_range(x: int, y: int, to_x: int, to_y: int):
    if x < 0: x = 0
    if y < 0: y = 0
    if to_x > 319: to_x = 319
    if to_y > 239: to_y = 239

    if to_y < 190:
        # This is just sky
        ugfx.area(x, y, to_x-x, to_y-y, SKIES[level])
        complex_draw = False
    elif to_y > 190 and y < 190:
        # Partial sky coverage
        ugfx.area(x, y, to_x-x, 190-y, SKIES[level])
        y = 190
        complex_draw = True
    else:
        complex_draw = True
    
    if complex_draw:
        ugfx.stream_start(x, y, to_x-x, to_y-y)
        for x_value in range(x, to_x):
            for y_value in range(y, to_y):
                ugfx.stream_color(get_background_pixel(x_value, y_value))
        ugfx.stream_stop()


def draw_crosshair(x, y):
    ugfx.circle(x, y, CROSSHAIR_DIAMETER, ugfx.BLACK)
    ugfx.line(x, y - CROSSHAIR_RADIUS - CROSSHAIR_LINE_OFFSET, x, y - CROSSHAIR_RADIUS + CROSSHAIR_LINE_OFFSET, ugfx.BLACK)
    ugfx.line(x, y + CROSSHAIR_RADIUS - CROSSHAIR_LINE_OFFSET, x, y + CROSSHAIR_RADIUS + CROSSHAIR_LINE_OFFSET, ugfx.BLACK)
    ugfx.line(x - CROSSHAIR_RADIUS - CROSSHAIR_LINE_OFFSET, y, x - CROSSHAIR_RADIUS + CROSSHAIR_LINE_OFFSET, y, ugfx.BLACK)
    ugfx.line(x + CROSSHAIR_RADIUS - CROSSHAIR_LINE_OFFSET, y, x + CROSSHAIR_RADIUS + CROSSHAIR_LINE_OFFSET, y, ugfx.BLACK)


def move_crosshair(move_x, move_y):
    global crosshair_x
    global crosshair_y
    global last_crosshair_move
    if last_crosshair_move > pyb.millis() - 50:
        return
    last_crosshair_move = pyb.millis()
    redraw_bg_range(crosshair_x - CROSSHAIR_BLANKING, crosshair_y - CROSSHAIR_BLANKING,
                    crosshair_x + CROSSHAIR_BLANKING, crosshair_y + CROSSHAIR_BLANKING)
    crosshair_x += move_x
    crosshair_y += move_y
    if crosshair_x < 5: crosshair_x = 5
    if crosshair_y < 5: crosshair_y = 5
    if crosshair_x > 315: crosshair_x = 315
    if crosshair_y > 235: crosshair_y = 235

    if crosshair_x < 100 and crosshair_y < 20:
        award_points(0)

    draw_crosshair(crosshair_x, crosshair_y)
    
def refresh_score():
    ugfx.set_default_font(ugfx.FONT_SMALL)
    ugfx.text(10, 10, "%d" % score, ugfx.WHITE)

def award_points(points):
    global score
    score += points
    redraw_bg_range(10, 10, 20, 100)
    refresh_score()


def is_hit(x_aim, y_aim):
    for copter in quadcopters:
        if copter.x - 20 < x_aim < copter.x + 20 and copter.y - 20 < y_aim < copter.y + 20:
            copter.undraw()
            award_points(copter.score)
            move_crosshair(0, 0)
            quadcopters.remove(copter)
            return True

def shoot():
    if is_hit(crosshair_x, crosshair_y):
        tone(140,250,30)
        tone(180,250,30)
    else:
        tone(140,250,30)
        tone(100,250,30)
        

bz=pyb.Pin(pyb.Pin.cpu.D12, pyb.Pin.OUT_PP)

def tone(f,t,b=0):
    f = int(f)
    t = int(t)
    b = int(b)
    global bz
    p = int(1000000/f)
    t1 = pyb.millis()+t
    while pyb.millis() < t1:
        bz.high()
        pyb.udelay(p)
        bz.low()
        pyb.udelay(p)
    if b!=0: pyb.delay(b)
    
buttons.init()

quadcopters = []
class Quadcopter(object):
    def __init__(self, x, y, direction, speed):
        self.x = x
        self.y = y
        self.crashing = False
        self.direction = direction
        self.animation_frame = 0
        self.speed = speed
        self.color = random_choice((ugfx.BLACK, ugfx.ORANGE, ugfx.GREEN, ugfx.YELLOW, ugfx.PURPLE))
    
    @property
    def score(self):
        score = 10 * self.speed
        if self.crashing:
            score += 50
        return score
    
    def move_copter(self):
        if self.x < -20 or self.x > 350:
            raise ValueError("Too far outside the screen")
        if self.y > 250:
            raise ValueError("Crashed!")
        self.undraw()
        if self.direction == '+':
            self.x += 2 * self.speed
        else:
            self.x -= 2 * self.speed
        if self.crashing:
            self.y += 3
        self.draw()
    
    def undraw(self):
        redraw_bg_range(
            self.x - (QUADCOPTER_BODY_SIZE*5),
            self.y - (QUADCOPTER_BODY_SIZE*5),
            self.x + (QUADCOPTER_BODY_SIZE*5),
            self.y + (QUADCOPTER_BODY_SIZE*5)
        )
    
    def draw(self):
        if not self.crashing:
            self.crashing = not (pyb.rng() % 500)
        ugfx.area(self.x-QUADCOPTER_BODY_SIZE, self.y-QUADCOPTER_BODY_SIZE, QUADCOPTER_BODY_SIZE*2, QUADCOPTER_BODY_SIZE*2, self.color)
        self.animation_frame += 1
        self.animation_frame %= 4
        for armature_x, armature_y in (
            (-QUADCOPTER_BODY_SIZE*3, -QUADCOPTER_BODY_SIZE*2),
            (QUADCOPTER_BODY_SIZE*3, -QUADCOPTER_BODY_SIZE*2),
            (-QUADCOPTER_BODY_SIZE*3, QUADCOPTER_BODY_SIZE*2),
            (QUADCOPTER_BODY_SIZE*3, QUADCOPTER_BODY_SIZE*2)
        ):
            rotor_center_x = self.x + armature_x
            rotor_center_y = self.y + armature_y
            ugfx.thickline(rotor_center_x, rotor_center_y, self.x, self.y, self.color, 2, False)
            if self.animation_frame == 0:
                ugfx.line(rotor_center_x - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_x + int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y + int(QUADCOPTER_BODY_SIZE*0.7), ugfx.BLACK)
            elif self.animation_frame == 1:
                ugfx.line(rotor_center_x, rotor_center_y - QUADCOPTER_BODY_SIZE, rotor_center_x, rotor_center_y + QUADCOPTER_BODY_SIZE, ugfx.BLACK)
            elif self.animation_frame == 2:
                ugfx.line(rotor_center_x + int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_x - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y + int(QUADCOPTER_BODY_SIZE*0.7), ugfx.BLACK)
            elif self.animation_frame == 3:
                ugfx.line(rotor_center_x + QUADCOPTER_BODY_SIZE, rotor_center_y, rotor_center_x - QUADCOPTER_BODY_SIZE, rotor_center_y, ugfx.BLACK)
        draw_crosshair(crosshair_x, crosshair_y)

class HAB(object):
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = self.color = random_choice((ugfx.BLACK, ugfx.ORANGE, ugfx.GREEN, ugfx.YELLOW, ugfx.PURPLE))
    
    @property
    def score(self):
        return 20
    
    def move_copter(self):
        if self.y < -20:
            raise ValueError("Escaped!")
        self.undraw()
        self.y -= 4
        self.draw()
    
    def undraw(self):
        redraw_bg_range(
            self.x - (QUADCOPTER_BODY_SIZE*5),
            self.y - (QUADCOPTER_BODY_SIZE*5),
            self.x + (QUADCOPTER_BODY_SIZE*5),
            self.y + (QUADCOPTER_BODY_SIZE*5)
        )
    
    def draw(self):
        ugfx.fill_circle(self.x, self.y, QUADCOPTER_BODY_SIZE*2, ugfx.GRAY)
        ugfx.line(self.x, self.y+(QUADCOPTER_BODY_SIZE), self.x, self.y+QUADCOPTER_BODY_SIZE*3, ugfx.BLACK)
        ugfx.area(self.x-5, self.y+QUADCOPTER_BODY_SIZE*3, QUADCOPTER_BODY_SIZE*2, QUADCOPTER_BODY_SIZE, self.color)
        draw_crosshair(crosshair_x, crosshair_y)
    


def spawn_quadcopter():
    if len(quadcopters) > level:
        print("Too many copters! Call the CAA")
        global tmc_count
        tmc_count += 1
        return
    right = pyb.rng() % 2
    if right:
        x = 0
        direction = '+'
    else:
        x = 320
        direction = '-'
    speed = (pyb.rng() % (level))
    if speed == 0:
        speed = 1
    quadcopter = Quadcopter(x, pyb.rng() % 160, direction=direction, speed=speed)
    quadcopters.append(quadcopter)

def spawn_hab():
    if len(quadcopters) > level:
        print("Too many copters! Call the CAA")
        #global tmc_count
        #tmc_count += 1
        return
    quadcopter = HAB(pyb.rng()%300, 180, speed=1)
    quadcopters.append(quadcopter)

def spawn_enemy():
    if level == 1:
        spawn_quadcopter()
    else:
        if pyb.rng() % 5 == 0:
            spawn_hab()
        else:
            spawn_quadcopter()

def animate_quadcopters():
    for quadcopter in quadcopters:
        try:
            quadcopter.move_copter()
        except ValueError:
            die()
            quadcopters.remove(quadcopter)

frame_times = []

def die():
    global lives
    lives -= 1
    tone(300,100,30)
    tone(200,100,30)
    tone(100,100,30)
    tone(50,200,30)

def draw_fps():
    ugfx.set_default_font(ugfx.FONT_SMALL)
    #redraw_bg_range(300, 10, 320, 35)
    try:
        fps = int((len(frame_times) / (frame_times[-1] - frame_times[0])) * 1000)
    except ZeroDivisionError:
        fps = 0
    ugfx.text(300, 10, "%d" % fps, ugfx.WHITE)
    

def maybe_advance_level():
    global level
    if score < 80:
        new_level = 1
    elif score < 150:
        new_level = 2
    elif score < 300:
        new_level = 3
    elif score < 600:
        new_level = 4
    elif score < 1000:
        new_level = 5
    else:
        new_level = 6
    if new_level != level:
        #notice(text="You have reached level %d" % level, title="Congratulations")
        level = new_level
        tone(100,250,30)
        tone(150,50,30)
        tone(180,50,30)
        tone(150,50,30)
        tone(180,50,30)
        tone(150,50,30)
        tone(180,50,30)
        tone(100,250,30)
        redraw_whole_bg()
        for copter in quadcopters:
            copter.draw()


A = 880
AS = 932.33
C = 1046.50
CS = 1108.73
D = 1174.66
SPEED = 500

ugfx.clear(SKIES[level])
ugfx.set_default_font(ugfx.FONT_NAME)
ugfx.text(110, 10, "EMF", ugfx.WHITE)
ugfx.set_default_font(ugfx.FONT_MEDIUM)
ugfx.text(100, 80, "It's unbelievable!", ugfx.WHITE)

ugfx.text(15, 140, "There are too many toys in the skies.", ugfx.WHITE)
ugfx.text(95, 160, "Shoot them down.", ugfx.WHITE)


tone(A, SPEED*0.75, SPEED*0.25)
tone(A, SPEED*0.5, SPEED*0.5)
tone(C, SPEED*0.2, SPEED*0.1)
tone(A, SPEED*0.3, SPEED*0.3)
tone(C, SPEED*0.4, SPEED*0.25)
tone(C, SPEED*0.5, SPEED*0.4)
tone(CS, SPEED*0.4, SPEED*0.25)
tone(D, SPEED*0.15, SPEED*0.4)
tone(D, SPEED*0.6, SPEED*0.4)
tone(C, SPEED*0.5, SPEED*0.4)
tone(C, SPEED*0.3, 0)
tone(AS, SPEED*0.2, SPEED*0.3)
tone(AS, SPEED*0.4, SPEED*0.1)
tone(A, SPEED*0.1, SPEED*0.4)
tone(A, SPEED*0.6, SPEED*0.4)

playing = True
while playing:
    points = 0
    lives = 3
    redraw_whole_bg()
    award_points(0)
    move_crosshair(0, 0)
    while lives >= 0:
        if buttons.is_pressed("BTN_MENU"):
            break
        if buttons.is_pressed("JOY_LEFT"):
            move_crosshair(-5, 0)
        if buttons.is_pressed("JOY_RIGHT"):
            move_crosshair(5, 0)
        if buttons.is_pressed("JOY_UP"):
            move_crosshair(0, -5)
        if buttons.is_pressed("JOY_DOWN"):
            move_crosshair(0, 5)
        if buttons.is_pressed("JOY_CENTER") or buttons.is_pressed("BTN_A") or buttons.is_pressed("BTN_B"):
            shoot()
        if pyb.millis() > next_change:
            next_change = pyb.millis() + SCREEN_DURATION
            frame_times.append(pyb.millis())
            frame_times = frame_times[-50:]
            #print(pixels)
            #pixels = 0
            animate_quadcopters()
        if pyb.millis() > next_enemy:
            spawn_enemy()
            next_enemy = pyb.millis () + ENEMY_FREQUENCY - (level * 300)
        maybe_advance_level()
        refresh_score()
    playing = prompt_boolean("You scored %d. Try again?" % score, title="Game over!")
