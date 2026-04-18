from engine.core.commons import *
from engine.core.GameState import game
from engine.core.AssetManager import AssetManager
from cepilloParty.managers.inputManager import InputManager

class CepilloParty(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Screen config

        self.name = 'cepillo_party'

        # Game board

        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # Game state
        self.game_active = True
        self.bg_music = None
        self.timer = 0
        
        # Create menu button (always visible, top-left corner)
        self.menu_button = Button(
            text='MENU',
            size_hint=(None, None),
            size=(100, 50),
            pos_hint={'x': 0.01, 'top': 0.99},
            background_color=(0.8, 0.2, 0.2, 0.8)
        )
        self.menu_button.bind(on_press=self.back_to_menu)
        
        # Startup - assets loaded here, setup_game() called when game starts
        
          
    def on_enter(self):
        self.load_assets()
        self.setup_game()
    
    def setup_game(self):
        # Reset game state
        self.game_active = True
        self.timer = 0
        
        # Clear layout and add menu button
        self.layout.clear_widgets()
        self.layout.add_widget(self.menu_button)

        # Start background music
        if self.bg_music:
            self.bg_music.play()
    
        # Schedule game update loop
        Clock.schedule_interval(self._update_screen_timer, 1/60)  # 60 FPS
    
    def load_assets(self):
        asset_manager = AssetManager('cepillo_party')
        

    def _update_screen_timer(self, dt):
        self.timer -= 1

        if (self.timer <= 0):
            self.timeLabel.text = "TIEMPO"
            self.game_active = False
            # ADD HERE ENDING SEQUENCE
            game.sm.current = 'menu'

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.timeLabel.text = f"{mins:02d}:{secs:02d}"

class TUIOTooth(TUIOButton):
    def __init__(self, id=None, **kwargs):
        super().__init__(id=id, **kwargs)
        
        # Configuration
        self.id = id
        
        # State
        self.is_clean = True
        self.is_touched = False # Whether the tooth is currently being touched
        
        # Brush system
        self.brush_quota = 150 # Total points needed for a brush to count
        self.is_brushing = False # Whether the tooth is currently being brushed
        self.brushes_left = 3 # Number of times to be brushed before being cleaned
    
