from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.clock import Clock
from kivy.vector import Vector
from kivy.metrics import dp
from kivy.uix.label import Label
from random import randint, choice
from math import sqrt, atan2, degrees, sin, cos, radians
from heapq import heappush, heappop


class Player:
    def __init__(self, x, y):
        self.pos = Vector(x, y)
        self.size = 30
        self.health = 100
        self.max_health = 100
        self.speed = 5
        self.angle = 0


class Bullet:
    def __init__(self, x, y, angle):
        self.pos = Vector(x, y)
        self.speed = 12
        self.angle = angle
        self.size = 5
        self.life = 100


class Enemy:
    def __init__(self, x, y):
        self.pos = Vector(x, y)
        self.size = 25
        self.health = 50
        self.speed = 2.5  # Slightly faster now
        self.shoot_timer = randint(60, 120)
        self.bullets = []
        self.state = "CHASE"  # Start smart
        self.path = []
        self.path_timer = 0
        self.target_pos = Vector(0, 0)


class Crate:
    def __init__(self, x, y):
        self.pos = Vector(x, y)
        self.size = 40
        self.looted = False


class FireCloneGame(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player = Player(400, 300)
        self.bullets = []
        self.enemies = []
        self.crates = [Crate(randint(100, 700), randint(100, 700)) for _ in range(5)]
        self.score = 0
        self.game_over = False
        self.joystick_pos = Vector(50, 100)
        self.joystick_touch = None
        self.shoot_touch = None
        self.walls = [
            (100, 100, 200, 20),
            (500, 100, 200, 20),
            (100, 600, 200, 20),
            (500, 600, 200, 20),
            (300, 200, 20, 400),
            (500, 300, 20, 200),
        ]
        self.CELL_SIZE = 20
        self.cols = 800 // self.CELL_SIZE  # 40
        self.rows = 700 // self.CELL_SIZE  # 35
        self.grid = None
        self.build_grid()
        Clock.schedule_interval(self.update, 1 / 60)

    def build_grid(self):
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        for wx, wy, w, h in self.walls:
            col_start = int(wx // self.CELL_SIZE)
            row_start = int(wy // self.CELL_SIZE)
            col_end = int((wx + w) // self.CELL_SIZE)
            row_end = int((wy + h) // self.CELL_SIZE)
            for r in range(row_start, min(row_end + 1, self.rows)):
                for c in range(col_start, min(col_end + 1, self.cols)):
                    self.grid[r][c] = 1

    def pos_to_grid(self, x, y):
        return int(y // self.CELL_SIZE), int(x // self.CELL_SIZE)

    def grid_to_pos(self, row, col):
        return (
            col * self.CELL_SIZE + self.CELL_SIZE / 2,
            row * self.CELL_SIZE + self.CELL_SIZE / 2,
        )

    def find_free_cell(self):
        attempts = 0
        while attempts < 200:
            r = randint(2, self.rows - 3)
            c = randint(2, self.cols - 3)
            if self.grid[r][c] == 0:
                return (r, c)
            attempts += 1
        return None

    def a_star(self, start, goal):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = []
        heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        while open_set:
            _, current = heappop(open_set)
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = current[0] + dr, current[1] + dc
                neighbor = (nr, nc)
                if (
                    0 <= nr < self.rows
                    and 0 <= nc < self.cols
                    and self.grid[nr][nc] == 0
                ):
                    tent_g = g_score[current] + 1
                    if neighbor not in g_score or tent_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tent_g
                        f_score[neighbor] = tent_g + heuristic(neighbor, goal)
                        heappush(open_set, (f_score[neighbor], neighbor))
        return []

    def line_of_sight(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        dist = sqrt(dx * dx + dy * dy)
        steps = max(1, int(dist / 5))
        for i in range(1, steps + 1):
            t = i / steps
            px = x1 + dx * t
            py = y1 + dy * t
            row, col = self.pos_to_grid(px, py)
            if (
                0 <= row < self.rows
                and 0 <= col < self.cols
                and self.grid[row][col] == 1
            ):
                return False
        return True

    def reset(self):
        self.player = Player(400, 300)
        self.bullets = []
        self.enemies = []
        self.crates = [Crate(randint(100, 700), randint(100, 700)) for _ in range(5)]
        self.score = 0
        self.game_over = False

    def on_touch_down(self, touch):
        if self.game_over:
            self.reset()
            return True
        if touch.x < 150 and touch.y < 250:
            self.joystick_touch = touch.uid
            touch.grab(self)
            return True
        else:
            self.shoot(touch.x, touch.y)
            return True

    def on_touch_move(self, touch):
        if touch.uid == self.joystick_touch:
            dx = touch.x - 50
            dy = touch.y - 100
            dist = Vector(dx, dy).length()
            if dist > 50:
                dist = 50
            if dist > 0:
                self.joystick_pos = Vector(
                    50 + dx / dist * dist, 100 + dy / dist * dist
                )
            else:
                self.joystick_pos = Vector(50, 100)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.uid == self.joystick_touch:
            self.joystick_pos = Vector(50, 100)
            self.joystick_touch = None
            touch.ungrab(self)
            return True
        return False

    def shoot(self, tx, ty):
        dx = tx - self.player.pos.x
        dy = ty - self.player.pos.y
        angle = atan2(dy, dx)
        self.player.angle = degrees(angle)
        self.bullets.append(Bullet(self.player.pos.x, self.player.pos.y, angle))

    def spawn_enemy(self):
        if len(self.enemies) < 8:  # More enemies now!
            side = choice(["top", "bottom", "left", "right"])
            if side == "top":
                e = Enemy(randint(50, 750), randint(0, 50))
            elif side == "bottom":
                e = Enemy(randint(50, 750), randint(650, 700))
            elif side == "left":
                e = Enemy(randint(0, 50), randint(50, 650))
            else:
                e = Enemy(randint(750, 800), randint(50, 650))
            e.state = "CHASE"
            e.path_timer = 0
            e.target_pos = self.player.pos.copy()
            self.enemies.append(e)

    def update(self, dt):
        if self.game_over:
            return

        # Player movement
        move_vec = Vector(self.joystick_pos.x - 50, self.joystick_pos.y - 100)
        dist = move_vec.length()
        if dist > 0:
            move_vec = move_vec.normalize() * min(
                dist / 50 * self.player.speed, self.player.speed
            )
            self.player.pos += move_vec

        # Player boundaries
        self.player.pos.x = max(
            self.player.size / 2, min(800 - self.player.size / 2, self.player.pos.x)
        )
        self.player.pos.y = max(
            self.player.size / 2, min(700 - self.player.size / 2, self.player.pos.y)
        )

        # Player bullets
        for b in self.bullets[:]:
            b.pos.x += cos(radians(b.angle)) * b.speed
            b.pos.y += sin(radians(b.angle)) * b.speed
            b.life -= 1
            if b.life <= 0 or not (0 < b.pos.x < 800 and 0 < b.pos.y < 700):
                self.bullets.remove(b)
                continue

        # Enemies AI
        for e in self.enemies[:]:
            dist_to_player = (self.player.pos - e.pos).length()
            los = self.line_of_sight(
                e.pos.x, e.pos.y, self.player.pos.x, self.player.pos.y
            )

            # State machine
            if e.health < 25:
                e.state = "FLEE"
            elif dist_to_player < 80 and los:
                e.state = "ATTACK"
            elif dist_to_player < 250:
                e.state = "CHASE"
            else:
                e.state = "PATROL"

            # Set target
            if e.state in ["ATTACK", "CHASE"]:
                e.target_pos = self.player.pos.copy()
            elif e.state == "FLEE":
                away_dir = (e.pos - self.player.pos).normalize()
                e.target_pos = e.pos + away_dir * 150
                e.target_pos.x = max(50, min(750, e.target_pos.x))
                e.target_pos.y = max(50, min(650, e.target_pos.y))
            elif e.state == "PATROL":
                if len(e.path) <= 1:
                    free_cell = self.find_free_cell()
                    if free_cell:
                        tr, tc = free_cell
                        e.target_pos = Vector(*self.grid_to_pos(tr, tc))

            # Pathfinding
            e.path_timer -= 1
            if e.path_timer <= 0:
                s_row, s_col = self.pos_to_grid(e.pos.x, e.pos.y)
                g_row, g_col = self.pos_to_grid(e.target_pos.x, e.target_pos.y)
                e.path = self.a_star((s_row, s_col), (g_row, g_col))
                e.path_timer = randint(15, 35)

            # Move along path
            if e.path and len(e.path) > 1:
                next_row, next_col = e.path[1]
                nx, ny = self.grid_to_pos(next_row, next_col)
                move_dir = Vector(nx - e.pos.x, ny - e.pos.y)
                dist_to_next = move_dir.length()
                if dist_to_next > 0:
                    move_dir = move_dir.normalize() * e.speed
                    e.pos += move_dir
                if dist_to_next < self.CELL_SIZE / 2:
                    e.path.pop(0)

            # Shooting
            e.shoot_timer -= 1
            if e.shoot_timer <= 0 and e.state in ["ATTACK", "CHASE"] and los:
                angle = atan2(self.player.pos.y - e.pos.y, self.player.pos.x - e.pos.x)
                e.bullets.append(Bullet(e.pos.x, e.pos.y, angle))
                e.shoot_timer = randint(45 if e.state == "ATTACK" else 90, 120)

            # Enemy bullets
            for eb in e.bullets[:]:
                eb.pos.x += cos(radians(eb.angle)) * 8
                eb.pos.y += sin(radians(eb.angle)) * 8
                eb.life -= 1
                if eb.life <= 0 or not (0 < eb.pos.x < 800 and 0 < eb.pos.y < 700):
                    e.bullets.remove(eb)
                    continue
                dist = (eb.pos - self.player.pos).length()
                if dist < self.player.size / 2 + eb.size:
                    self.player.health -= 12
                    e.bullets.remove(eb)
                    if self.player.health <= 0:
                        self.game_over = True
                    break

        # Player bullets hit enemies
        for b in self.bullets[:]:
            for e in self.enemies[:]:
                dist = (b.pos - e.pos).length()
                if dist < e.size / 2 + b.size:
                    e.health -= 25
                    self.bullets.remove(b)
                    if e.health <= 0:
                        self.enemies.remove(e)
                        self.score += 100
                        if randint(1, 3) == 1:
                            self.crates.append(Crate(e.pos.x, e.pos.y))
                    break

        # Loot
        for c in self.crates[:]:
            dist = (c.pos - self.player.pos).length()
            if dist < c.size / 2 + self.player.size / 2 and not c.looted:
                self.player.health = min(
                    self.player.max_health, self.player.health + 30
                )
                c.looted = True
                self.crates.remove(c)

        # Spawn
        if randint(1, 100) < 3:
            self.spawn_enemy()

        # Simple wall push for player
        for wall in self.walls:
            if (
                wall[0] < self.player.pos.x < wall[0] + wall[2]
                and wall[1] < self.player.pos.y < wall[1] + wall[3]
            ):
                self.player.pos.x -= self.player.speed * 0.5

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            # Background
            Color(0.2, 0.6, 0.2)
            Rectangle(pos=(0, 0), size=(800, 700))

            # Walls
            Color(0.5, 0.5, 0.5)
            for wall in self.walls:
                Rectangle(pos=(wall[0], wall[1]), size=(wall[2], wall[3]))

            # Player
            Color(0, 0.5, 1)
            Ellipse(
                pos=(
                    self.player.pos.x - self.player.size / 2,
                    self.player.pos.y - self.player.size / 2,
                ),
                size=(self.player.size, self.player.size),
            )
            Color(1, 1, 1, 0.5)
            Line(
                points=[
                    self.player.pos.x,
                    self.player.pos.y,
                    self.player.pos.x + cos(radians(self.player.angle)) * 100,
                    self.player.pos.y + sin(radians(self.player.angle)) * 100,
                ],
                width=3,
            )

            # Player bullets
            Color(1, 1, 0)
            for b in self.bullets:
                Ellipse(
                    pos=(b.pos.x - b.size / 2, b.pos.y - b.size / 2),
                    size=(b.size * 2, b.size * 2),
                )

            # Enemies + AI Paths
            for e in self.enemies:
                # State color
                if e.state == "ATTACK":
                    col = (1, 0, 0)
                elif e.state == "CHASE":
                    col = (1, 0.3, 0)
                elif e.state == "FLEE":
                    col = (0.5, 0, 1)
                else:
                    col = (0, 1, 0)
                Color(*col)
                Ellipse(
                    pos=(e.pos.x - e.size / 2, e.pos.y - e.size / 2),
                    size=(e.size, e.size),
                )

                # Path line (AI brain visible!)
                if len(e.path) > 1:
                    points = []
                    for r, c in e.path[:15]:  # Cap for perf
                        px, py = self.grid_to_pos(r, c)
                        points += [px, py]
                    Color(1, 1, 1, 0.4)
                    Line(points=points, width=3)

            # Enemy bullets
            Color(1, 0.5, 0)
            for e in self.enemies:
                for eb in e.bullets:
                    Ellipse(
                        pos=(eb.pos.x - eb.size / 2, eb.pos.y - eb.size / 2),
                        size=(eb.size * 2, eb.size * 2),
                    )

            # Crates
            Color(0.8, 0.6, 0.2)
            for c in self.crates:
                Rectangle(
                    pos=(c.pos.x - c.size / 2, c.pos.y - c.size / 2),
                    size=(c.size, c.size),
                )

            # Joystick
            Color(0.3, 0.3, 0.3, 0.5)
            Ellipse(pos=(0, 50), size=(100, 100))
            Color(0.5, 0.5, 0.5)
            Ellipse(
                pos=(self.joystick_pos.x - 20, self.joystick_pos.y - 20), size=(40, 40)
            )

            # Game Over overlay
            if self.game_over:
                Color(0, 0, 0, 0.8)
                Rectangle(pos=(0, 0), size=(800, 700))


class FireCloneApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        screen = MDScreen()
        self.game = FireCloneGame(size_hint=(1, 1))
        screen.add_widget(self.game)

        # HUD
        hud = MDBoxLayout(
            orientation="horizontal", size_hint=(1, 0.1), pos_hint={"top": 1}
        )
        self.health_label = Label(
            text="Health: 100", size_hint_x=0.5, color=(1, 1, 1, 1)
        )
        self.score_label = Label(text="Score: 0", size_hint_x=0.5, color=(1, 1, 1, 1))
        hud.add_widget(self.health_label)
        hud.add_widget(self.score_label)
        screen.add_widget(hud)

        Clock.schedule_interval(self.update_hud, 0.1)
        return screen

    def update_hud(self, dt):
        self.health_label.text = f"Health: {self.game.player.health}"
        self.score_label.text = f"Score: {self.game.score}"
        if self.game.game_over:
            self.health_label.text = "GAME OVER!"


            # Test trigger
            self.score_label.text = f"Final Score: {self.game.score}"


if __name__ == "__main__":
    FireCloneApp().run()
