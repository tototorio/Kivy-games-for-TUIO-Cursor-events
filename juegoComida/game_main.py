from engine.core.commons import *
from engine.core.AssetManager import AssetManager

class JuegoComida(Screen):

    def __init__(self, assets : AssetManager, **kwargs):
        super().__init__(**kwargs)
        self.name = 'juego_comida'
        self.assets = assets
        self.game_active = False
        self.active_food = []

        self.spawn_side_dict = {
            'top': lambda: (random.randint(0, self.width - 50), self.height - 50),
            'bottom': lambda: (random.randint(0, self.width - 50), 0),
            'left': lambda: (0, random.randint(0, self.height - 50)),
            'right': lambda: (self.width - 50, random.randint(0, self.height - 50))
        }

    def on_enter(self):
        self._setup_game()

    def on_leave(self):
        pass

    def _setup_game(self):
        
        # Fondo gris
        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            Rectangle(pos=self.pos, size=self.size)
        
        self.game_active = True
        # Internal game timer
        self.timer = 300
        self.miliseconds = 0 

        self.kid = Kid(pos=(self.width / 2 - 25, self.height / 2 - 25), size_hint=(None, None), size=(50, 50))
        self.add_widget(self.kid)
        
        # Timer label en la esquina superior derecha
        self.timer_label = Label(text="05:00", font_size=30, pos=(self.width - 100, self.height - 50), size_hint=(None, None), size=(100, 50))
        self.add_widget(self.timer_label)

        Clock.schedule_interval(self._update, 1/60) # 60 FPS update loop

        Clock.schedule_interval(self._spawn_food, 0.5) # Spawn food every 2 seconds

    def _update(self, dt):
        """Main update loop for the game, called every frame when active"""
        
        if not self.game_active:
            return
        
        self.miliseconds += dt
        if self.miliseconds >= 60:
            self.miliseconds = 0
            self._update_screen_timer(1)

        if self.active_food:
            self._update_food(dt)
    
    def _update_food(self, dt):
        """Updates the position of all active food items and checks for collisions with the kid"""

        food_to_remove = []
        
        for food in self.active_food:
            # Move food towards the kid
            food.x += food.velocity[0] * dt
            food.y += food.velocity[1] * dt

            # Check for collision with the kid
            if None:
                self.kid.eat_food(food)
                self.remove_widget(food)
                food_to_remove.append(food)
        
        # Remover comida después de iterar
        for food in food_to_remove:
            self.active_food.remove(food)

    def _update_screen_timer(self, dt):
        """Updates the on screen timer and checks for timeout"""

        self.timer -= 1

        if (self.timer <= 0):
            self.timer_label.text = "TIEMPO" # type: ignore
            # ADD HERE ENDING SEQUENCE

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.timer_label.text = f"{mins:02d}:{secs:02d}"
    
    def _spawn_food(self, dt):
        """Spawns a new food item at a random position on the screen"""

        # Randomly decide if it's good or bad food
        is_good = random.choice([True, False])
        food_type = 'good' if is_good else 'bad'
        
        # Get a random position on the screen
        spawn_side = random.choice(['top', 'bottom', 'left', 'right'])
        x, y = self.spawn_side_dict[spawn_side]()
        
        if is_good:
            food_item = GoodFood(
                speed=50, 
                health_mod=10, 
                pos=(x, y),
                size_hint=(None, None),
                size=(50, 50)
                )
        else:
            food_item = BadFood(
                speed=50,
                health_mod=-10, 
                pos=(x, y),
                size_hint=(None, None),
                size=(50, 50)
            )
        
        self.active_food.append(food_item)
        self.add_widget(food_item)

        food_item.update_velocity()

    
    
# Singleton class for the kid. It will be a static object in the center of the screen.
# Both good and bad food will move towards the kid, and the player will have to avoid 
# the bad food from reaching the kid. Its weight and mood will change based on the food it eats.
class Kid(Widget):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.health = 50
        
        # Fondo visual del Kid
        with self.canvas.before:
            Color(1, 0.8, 0.6, 1)
            self.background_rect = Rectangle(pos=self.pos, size=self.size)
        
        self.visual = Label(
                text=f"{self.health}",
                font_size=20,
                color=(0, 0, 0, 1),
                pos=self.pos,
                size=self.size
            )
        self.add_widget(self.visual)

    def _update_visuals(self):
        self.visual.text = f"{self.health}"

    def eat_food(self, food):
        self.health += food.health_mod
        self._update_visuals()
            
        
        

class Food(Widget):
    def __init__(self, speed=1, health_mod=0, texture:Texture=None, **kwargs):
        super().__init__(**kwargs)
        self.health_mod = health_mod
        self.speed = speed

        if not texture:
            self.texture = Texture.create(size=(50, 50))    
            self.texture.blit_buffer(bytes([255, 0, 0] * 2500), colorfmt='rgb', bufferfmt='ubyte')
        else:
            self.texture = texture

        # Imagen visual de la comida
        self.image = Image(texture=self.texture, size=self.size, pos=self.pos)
        self.add_widget(self.image)
        self.bind(pos=lambda instance, value: setattr(self.image, 'pos', value)) # type: ignore
        self.bind(size=lambda instance, value: setattr(self.image, 'size', value)) # type: ignore

        
    
    def update_velocity(self):
        """Calcula la velocidad hacia el kid"""
        kid_pos = (self.parent.width / 2 - 25, self.parent.height / 2 - 25)
        dx = kid_pos[0] - self.pos[0]
        dy = kid_pos[1] - self.pos[1]
        
        magnitude = (dx**2 + dy**2) ** 0.5
        if magnitude == 0:
            self.velocity = (0, 0)
        else:
            self.velocity = (dx / magnitude * self.speed, dy / magnitude * self.speed)

class GoodFood(Food):
    def __init__(self, speed=1, health_mod=1, texture=None, **kwargs):
        # Crear textura verde para comida buena
        if texture is None:
            texture = Texture.create(size=(50, 50))
            texture.blit_buffer(bytes([0, 255, 0] * 2500), colorfmt='rgb', bufferfmt='ubyte')
        super().__init__(speed, health_mod, texture, **kwargs)   

class BadFood(Food):
    def __init__(self, speed=1, health_mod=0, texture=None, **kwargs):
        # Crear textura roja para comida mala
        if texture is None:
            texture = Texture.create(size=(50, 50))
            texture.blit_buffer(bytes([255, 0, 0] * 2500), colorfmt='rgb', bufferfmt='ubyte')
        
        super().__init__(speed, health_mod, texture, **kwargs)
        