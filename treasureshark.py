import tdl
from random import randint

# gameplay window stuff
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# map size stuff
MAP_WIDTH = 80
MAP_HEIGHT = 45

# room generation stuff
ROOM_MAX_SIZE = 18
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

# vision stuff
FOV_ALGO = "BASIC"
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 7

LIMIT_FPS = 20

color_dark_wall = (0, 0, 100)
color_light_wall = (130, 110, 50)
color_dark_ground = (50, 50, 150)
color_light_ground = (200, 180, 50)


class Tile:
    # map tile
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
        self.explored = False

        # blocked tiles block sight by default
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


class Rect:
    # makes a rectangle for a room
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2
        return(center_x, center_y)

    def intersect(self, other):
        # true if rooms overlap
        return(self.x1 <= other.x2 and self.x2 >= other.x1 and
               self.y1 <= other.y2 and self.y2 >= other.y1)


class GameObject:
    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color

    def move(self, dx, dy):
        if not my_map[self.x + dx][self.y + dy].blocked:
            self.x += dx
            self.y += dy

    def draw(self):
        if (self.x, self.y) in visible_tiles:
            con.draw_char(self.x, self.y, self.char, self.color, bg=None)

    def clear(self):
        con.draw_char(self.x, self.y, " ", self.color, bg=None)


def make_map():
    global my_map

    # fill map with blocked tiles
    my_map = [[Tile(True) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]

    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        # random width and height
        w = randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        # random position inside the map
        x = randint(0, MAP_WIDTH-w-1)
        y = randint(0, MAP_HEIGHT-h-1)

        new_room = Rect(x, y, w, h)

        # check for intersection with other rooms
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            create_room(new_room)
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                # first room created, player starts here
                player.x = new_x
                player.y = new_y

            else:
                # rooms after the first
                # connected to previous room by a tunnel

                (prev_x, prev_y) = rooms[num_rooms-1].center()

                if randint(0, 1):
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            rooms.append(new_room)
            num_rooms += 1


def create_h_tunnel(x1, x2, y):
    global my_map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        my_map[x][y].blocked = False
        my_map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
    global my_map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        my_map[x][y].blocked = False
        my_map[x][y].block_sight = False


def is_visible_tile(x, y):
    global my_map
    if x >= MAP_WIDTH or x < 0:
        return False
    elif y >= MAP_HEIGHT or y < 0:
        return False
    elif my_map[x][y].blocked == True:
        return False
    elif my_map[x][y].block_sight == True:
        return False
    else:
        return True


def create_room(room):
    global my_map
    # make the tiles in a rectangle passable
    for x in range(room.x1 +1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            my_map[x][y].blocked = False
            my_map[x][y].block_sight = False


def render_all():
    global fov_recompute
    global visible_tiles

    if fov_recompute:
        fov_recompute = False
        visible_tiles = tdl.map.quickFOV(player.x, player.y,
                                         is_visible_tile,
                                         fov=FOV_ALGO,
                                         radius=TORCH_RADIUS,
                                         lightWalls=FOV_LIGHT_WALLS)

    # set tile backgrounds by FOV
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visible = (x, y) in visible_tiles
            wall = my_map[x][y].block_sight
            if not visible:
                if my_map[x][y].explored:
                    if wall:
                        con.draw_char(x, y, None, fg=None, bg=color_dark_wall)
                    else:
                        con.draw_char(x, y, None, fg=None, bg=color_dark_ground)
            else:
                if wall:
                    con.draw_char(x, y, None, fg=None, bg=color_light_wall)
                else:
                    con.draw_char(x, y, None, fg=None, bg=color_light_ground)
                # explore since it's visible
                my_map[x][y].explored = True

    for obj in objects:
        obj.draw()

    root.blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0)


def handle_keys():
    global playerx, playery
    global fov_recompute

    user_input = tdl.event.key_wait()

    if user_input.key == "ENTER" and user_input.alt:
        # Alt+enter: toggle fullscreen mode
        tdl.set_fullscreen(not tdl.get_fullscreen())

    elif user_input.key == "ESCAPE":
        return True # escape to exit game

    # movement keys
    if user_input.key == "UP":
        player.move(0, -1)
        fov_recompute = True

    elif user_input.key == "DOWN":
        player.move (0, 1)
        fov_recompute = True

    elif user_input.key == "LEFT":
        player.move(-1, 0)
        fov_recompute = True

    elif user_input.key == "RIGHT":
        player.move(1, 0)
        fov_recompute = True


tdl.set_font("arial10x10.png", greyscale=True, altLayout=True)
root = tdl.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Treasure Shark", fullscreen=False)
con = tdl.Console(SCREEN_WIDTH, SCREEN_HEIGHT)

player = GameObject(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, "@", (255, 255, 255))
npc = GameObject(SCREEN_WIDTH//2 - 5, SCREEN_HEIGHT//2, "@", (255, 255, 0))
objects = [npc, player]
make_map()

fov_recompute = True

while not tdl.event.is_window_closed():
    render_all()
    tdl.flush()

    for obj in objects:
        obj.clear()

    exit_game = handle_keys()
    if exit_game:
        break