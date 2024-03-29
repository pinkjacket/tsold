import tdl
from random import randint
import colors
import math

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
MAX_ROOM_MONSTERS = 3

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
        return center_x, center_y

    def intersect(self, other):
        # true if rooms overlap
        return(self.x1 <= other.x2 and self.x2 >= other.x1 and
               self.y1 <= other.y2 and self.y2 >= other.y1)


class GameObject:
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:  # let fighter component know its owner
            self.fighter.owner = self

        self.ai = ai
        if self.ai:  # let AI component know its owner
            self.ai.owner = self

    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_towards(self, target_x, target_y):
        # vector from object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        # normalize to length 1 (keeping direction), then round and
        # convert to integer so the movement is restricted to the map grid
        dx = int(round(dx/distance))
        dy = int(round(dy/distance))
        self.move(dx, dy)

    def distance_to(self, other):
        # return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def draw(self):
        if (self.x, self.y) in visible_tiles:
            con.draw_char(self.x, self.y, self.char, self.color, bg=None)

    def send_to_back(self):
        # draw this object first so others are shown over it
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def clear(self):
        con.draw_char(self.x, self.y, " ", self.color, bg=None)


class Fighter:
    # can engage in combat
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage

            # check for death
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)

    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            # target takes damage
            print(self.owner.name.capitalize() + " attacks " + target.name + " for " + str(damage) + " damage!")
            target.fighter.take_damage(damage)
        else:
            print(self.owner.name.capitalize() + " attacks " + target.name + ", to no effect!")


class BasicEnemy:
    # basic enemy AI
    def take_turn(self):
        # basic monster turn. if it can see you, it chases you
        monster = self.owner
        if (monster.x, monster.y) in visible_tiles:

            # move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)

            # attack if close enough
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)


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

            # add contents to the room, ie enemies
            place_objects(new_room)

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


def is_blocked(x, y):
    # test the map tile
    if my_map[x][y].blocked:
        return True

    # check for blocking objects
    for obj in objects:
        if obj.blocks and obj.x == x and obj.y == y:
            return True

    return False


def create_room(room):
    global my_map
    # make the tiles in a rectangle passable
    for x in range(room.x1 +1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            my_map[x][y].blocked = False
            my_map[x][y].block_sight = False


def place_objects(room):
    # get random number of monsters
    num_monsters = randint(0, MAX_ROOM_MONSTERS)

    for i in range(num_monsters):
        # enemy placement
        x = randint(room.x1, room.x2)
        y = randint(room.y1, room.y2)

        # only place it if tile is unblocked
        if not is_blocked(x, y):
            # enemy odds
            choice = randint(0,100)
            if choice < 60:
                # withered husk
                fighter_component = Fighter(hp=10, defense=0,power=3, death_function=monster_death)
                ai_component = BasicEnemy()

                monster = GameObject(x, y, "h", "withered husk", colors.dark_gray, blocks=True,
                                     fighter=fighter_component, ai=ai_component)
            elif choice < 60 + 30:
                # rusted automaton
                fighter_component = Fighter(hp=16, defense=1, power=4, death_function=monster_death)
                ai_component = BasicEnemy()

                monster = GameObject(x, y, "a", "rusted automaton", colors.darker_orange, blocks=True,
                                     fighter=fighter_component, ai=ai_component)
            else:
                # kobold bandit
                fighter_component = Fighter(hp=20, defense=0, power=5, death_function=monster_death)
                ai_component = BasicEnemy()

                monster = GameObject(x, y, "k", "kobold bandit", colors.darker_flame, blocks=True,
                                     fighter=fighter_component, ai=ai_component)

            objects.append(monster)


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
        if obj != player:
            obj.draw()
    player.draw()

    # blit the contents of "con" to the root console and present it
    root.blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0)

    # show player's stats
    con.draw_str(1, SCREEN_HEIGHT - 2, "HP: " + str(player.fighter.hp) + "/" + str(player.fighter.max_hp) + " ")


def player_move_or_attack(dx, dy):
    global fov_recompute

    # coordinates the player is going to/attacking
    x = player.x + dx
    y = player.y + dy

    # look for attackable object
    target = None
    for obj in objects:
        if obj.fighter and obj.x == x and obj.y == y:
            target = obj
            break

    # attack if target found, otherwise move
    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True


def player_death(player):
    # game over!
    global game_state
    print("It is a sad thing that your adventures have ended here!")
    game_state = "dead"

    # player becomes corpse
    player.char = "%"
    player.color = colors.darkest_red


def monster_death(monster):
    print(monster.name.capitalize() + " falls!")
    monster.char = "%"
    monster.color = colors.darkest_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = "remains of " + monster.name
    monster.send_to_back()


def handle_keys():
    global playerx, playery
    global fov_recompute

    user_input = tdl.event.key_wait()

    if user_input.key == "ENTER" and user_input.alt:
        # Alt+enter: toggle fullscreen mode
        tdl.set_fullscreen(not tdl.get_fullscreen())

    elif user_input.key == "ESCAPE":
        return "exit" # escape to exit game

    if game_state == "playing":
        # movement keys
        if user_input.key == "UP":
            player_move_or_attack(0, -1)

        elif user_input.key == "DOWN":
            player_move_or_attack(0, 1)

        elif user_input.key == "LEFT":
            player_move_or_attack(-1, 0)

        elif user_input.key == "RIGHT":
            player_move_or_attack(1, 0)

        else:
            return "didnt-take-turn"


tdl.set_font("arial10x10.png", greyscale=True, altLayout=True)
root = tdl.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Treasure Shark", fullscreen=False)
con = tdl.Console(SCREEN_WIDTH, SCREEN_HEIGHT)

# create the player
fighter_component = Fighter(hp=40, defense=2, power=5, death_function=player_death)
player = GameObject(0, 0, "@", "Shark", colors.white, blocks=True, fighter=fighter_component)
objects = [player]
make_map()

fov_recompute = True
game_state = "playing"
player_action = None

while not tdl.event.is_window_closed():
    render_all()
    tdl.flush()

    for obj in objects:
        obj.clear()

    player_action = handle_keys()
    if player_action == "exit":
        break

    # Let enemies go
    if game_state == "playing" and player_action != "didnt-take-turn":
        for obj in objects:
            if obj.ai:
                obj.ai.take_turn()
