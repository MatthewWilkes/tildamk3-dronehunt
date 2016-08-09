import buttons
import ugfx
import micropython
import pyb

crosshair_x = 100
crosshair_y = 100
score = 0
CROSSHAIR_DIAMETER = 10
CROSSHAIR_RADIUS = CROSSHAIR_DIAMETER // 2
CROSSHAIR_LINE_OFFSET = CROSSHAIR_RADIUS // 2
CROSSHAIR_BLANKING = CROSSHAIR_DIAMETER + CROSSHAIR_RADIUS
GROUND_1 = ugfx.html_color(0x804000)
GROUND_2 = ugfx.html_color(0xf05030)
GRASS = ugfx.html_color(0x4DBD33)
SKY = ugfx.html_color(0x87cefa)
QUADCOPTER_BODY = ugfx.BLACK
QUADCOPTER_BODY_SIZE = 5
SCREEN_DURATION = 100
ENEMY_FREQUENCY = 4000
next_change = 0
next_enemy = 0
animation_frame = 0
pixels = 0
@micropython.native
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
        return SKY


def redraw_whole_bg():
    ugfx.clear(SKY)
    ugfx.area(0, 191, 320, 10, GRASS)
    ugfx.area(0, 201, 320, 40, GROUND_2)
    redraw_bg_range(0, 201, 320, 240)


@micropython.viper
def redraw_bg_range(x: int, y: int, to_x: int, to_y: int):
    if x < 0: x = 0
    if y < 0: y = 0
    if x > 239: x = 239
    if y > 319: y = 319
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
    
def award_points(points):
    global score
    score += points
    ugfx.set_default_font(ugfx.FONT_SMALL)
    redraw_bg_range(10, 10, 20, 100)
    ugfx.text(10, 10, "%d" % score, ugfx.WHITE)


def is_hit(x_aim, y_aim):
    for copter in quadcopters:
        if copter.x - 20 < x_aim < copter.x + 20 and copter.y - 20 < y_aim < copter.y + 20:
            copter.undraw()
            quadcopters.remove(copter)
            return True

def shoot():
    if is_hit(crosshair_x, crosshair_y):
        tone(140,250,30)
        tone(180,250,30)
        award_points(10)
    else:
        tone(140,250,30)
        tone(100,250,30)
        

bz=pyb.Pin(pyb.Pin.cpu.D12, pyb.Pin.OUT_PP)

def tone(f,t,b=0):
    global bz
    p = int(1000000/f)
    t1 = pyb.millis()+t
    while pyb.millis() < t1:
        bz.high()
        pyb.udelay(p)
        bz.low()
        pyb.udelay(p)
    if b!=0: pyb.delay(b)
    
redraw_whole_bg()
award_points(0)

move_crosshair(0, 0)
buttons.init()

quadcopters = []
class Quadcopter(object):
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.crashing = False
        self.direction = direction
        self.animation_frame = 0
    
    def move_copter(self):
        self.undraw()
        if self.direction == '+':
            self.x += 2
        else:
            self.x -= 2
        if self.crashing:
            self.y -= 5
        self.draw()
    
    def undraw(self):
        ugfx.area(self.x-(QUADCOPTER_BODY_SIZE*4), self.y-(QUADCOPTER_BODY_SIZE*4), (QUADCOPTER_BODY_SIZE*8), (QUADCOPTER_BODY_SIZE*8), SKY)
        #redraw_bg_range(self.x - 20, self.y - 20, self.x + 20, self.y + 20)
    
    def draw(self):
        self.crashing = not (pyb.rng() % 100)
        ugfx.area(self.x-QUADCOPTER_BODY_SIZE, self.y-QUADCOPTER_BODY_SIZE, QUADCOPTER_BODY_SIZE*2, QUADCOPTER_BODY_SIZE*2, QUADCOPTER_BODY)
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
            ugfx.thickline(rotor_center_x, rotor_center_y, self.x, self.y, QUADCOPTER_BODY, 2, False)
            if self.animation_frame == 0:
                ugfx.line(rotor_center_x - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_x + int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y + int(QUADCOPTER_BODY_SIZE*0.7), ugfx.BLACK)
            elif self.animation_frame == 1:
                ugfx.line(rotor_center_x, rotor_center_y - QUADCOPTER_BODY_SIZE, rotor_center_x, rotor_center_y + QUADCOPTER_BODY_SIZE, ugfx.BLACK)
            elif self.animation_frame == 2:
                ugfx.line(rotor_center_x + int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y + int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_x - int(QUADCOPTER_BODY_SIZE*0.7), rotor_center_y - int(QUADCOPTER_BODY_SIZE*0.7), ugfx.BLACK)
            elif self.animation_frame == 3:
                ugfx.line(rotor_center_x - QUADCOPTER_BODY_SIZE, rotor_center_y, rotor_center_x + QUADCOPTER_BODY_SIZE, rotor_center_y, ugfx.BLACK)
        draw_crosshair(crosshair_x, crosshair_y)
    
def spawn_quadcopter():
    right = pyb.rng() % 2
    if right:
        x = 0
        direction = '+'
    else:
        x = 320
        direction = '-'
    quadcopter = Quadcopter(x, pyb.rng() % 200, direction=direction)
    quadcopters.append(quadcopter)

def animate_quadcopters():
    for quadcopter in quadcopters:
        quadcopter.move_copter()

frame_times = []

def draw_fps():
    ugfx.set_default_font(ugfx.FONT_SMALL)
    redraw_bg_range(300, 10, 320, 35)
    try:
        fps = int((len(frame_times) / (frame_times[-1] - frame_times[0])) * 1000)
    except ZeroDivisionError:
        fps = 0
    ugfx.text(300, 10, "%d" % fps, ugfx.WHITE)
    

while True:
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
    if buttons.is_pressed("JOY_CENTER"):
        shoot()
    if pyb.millis() > next_change:
        next_change = pyb.millis() + SCREEN_DURATION
        frame_times.append(pyb.millis())
        frame_times = frame_times[-50:]
        draw_fps()
        print(pixels)
        pixels = 0
        animate_quadcopters()
    if pyb.millis() > next_enemy:
        spawn_quadcopter()
        next_enemy = pyb.millis () + ENEMY_FREQUENCY - (score * 10)
        
    
