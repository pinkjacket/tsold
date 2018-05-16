import tdl

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

tdl.set_font("arial10x10.png", greyscale=True, altLayout=True)

console = tdl.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Treasure Shark", fullscreen=False)

while not tdl.event.is_window_closed():
    console.draw_char(1, 1, "@", bg=None, fg=(255,255,255))

    tdl.flush()