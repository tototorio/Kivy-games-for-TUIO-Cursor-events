#:kivy
from engine.core.commons import *
from engine.core.AssetManager import AssetManager
from cepilloParty.hud import Menu
#from cepilloParty.managers.inputManager import InputManager



class CepilloParty(Screen):
    
    def __init__(self, **kwargs):

        # Game main variables
        self.name = 'cepillo_party'
        self.assets_loaded = False
        self.asset_m: AssetManager
        self.teeth = {}
        
        # Dirty logic
        self.max_dirty_teeth = 10
        self.filth_layers = {} # Contains the images

        # Initialize variables ONLY (no widgets!)
        self.layout: FloatLayout | None = None
        self.game_active = False
        self.bg_music = None
        self.timer = 0
        self.menu_button: Button
        self.timerLabel: Label

        super().__init__(**kwargs)

    def on_enter(self):
        
        """Called when screen becomes active"""
        
        # Initialize Asset Manager and load assets
        self.asset_m = AssetManager(self.name)
        self.assets_loaded = True
        self._setup_game()

    def on_leave(self):
        """Cleanup when leaving the game screen"""
        self.game_active = False
        if self.bg_music:
            self.bg_music.stop()
        self.layout.clear_widgets() # Clear game widgets # type: ignore
        self.asset_m.unload_assets() # Unload assets to free memory
    
    def _setup_game(self):
        
        # Game variables
        self.menu = Menu(self)
        self.bg_music = self.asset_m.get_asset("background_music", "sound")

        # Mouth and teeth background
        self.ids.background_image.texture = self.asset_m.get_asset("game_background", "image").texture 
        
        # Lips and skin layer
        self.ids.lips_layer.texture = self.asset_m.get_asset("lips", "image").texture
        
        # Uncover game
        if self.ids.loading_layout:
            self.ids.loading_layout.opacity = 0
        
        

        self._open_menu()
    
    def _start_game(self):
        
        self._load_teeth()

        # Start background music
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.play()

        # Schedule game update loop
        try: 
            Clock.unschedule(self._update_screen_timer) # Ensure no duplicate schedules
        except Exception as e:
            print(f"Error unscheduling timer: {e}")   
    
    def _open_menu(self):
        """Pauses the game and opens the menu overlay"""
        self.game_active = False
        self.bg_music.stop() if self.bg_music else None
        # Startup - assets loaded here, setup_game() called when game starts
        self.menu.open()
    

    def _update_screen_timer(self, dt):
        self.timer -= 1

        if (self.timer <= 0):
            self.timerLabel.text = "TIEMPO" # type: ignore
            self.game_active = False
            # ADD HERE ENDING SEQUENCE
            self.menu.open()

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.timerLabel.text = f"{mins:02d}:{secs:02d}"

    def _load_teeth(self):
        
        self.teeth.clear() # Clear existing teeth before loading new ones
        self.filth_layers.clear() # Clear existing filth layers

        tooth_number = 1

        with open(self.asset_m.get_asset("teeth_config", "config"), 'r') as f:
            teeth_data = json.load(f)

        # Select random teeth to be dirty
        teeth_id_list = list (teeth_data.keys())
        dirty_teeth = random.sample(teeth_id_list, self.max_dirty_teeth)

        """Process of defining and adding tooth widgets to the game screen"""
        for tooth_id in sorted(teeth_data.keys()):
            
            is_dirty = tooth_id in dirty_teeth

            # Store coordinates and config
            config = teeth_data[tooth_id]
            normalized_coords = config['coords']
            center_x = sum(p[0] for p in normalized_coords) / len(normalized_coords)
            center_y = sum(p[1] for p in normalized_coords) / len(normalized_coords)

            # Create tooth widget and add to screen
            tooth = TUIOTooth(
                id=tooth_id, 
                normalized_coords=normalized_coords,
                center_x=center_x,
                center_y=center_y,
                is_dirty=is_dirty,
                filth_layer=None
            )
            self.add_widget(tooth)
            self.teeth[tooth_id] = tooth

            # Handle dirty tooth visual
            if is_dirty:
                filth_key = f"Diente{tooth_number}(sucio)"
                filth_layer = Image(
                    texture=self.asset_m.get_asset(filth_key, "image").texture,
                    allow_stretch=True, 
                    keep_ratio=False
                )
                self.ids.teeth_filth_layout.add_widget(filth_layer)

                self.filth_layers[tooth_id] = filth_layer
                self.teeth[tooth_id].filth_layer = filth_layer
            
            tooth_number += 1
            

        
# For tooth logic and management
class TUIOTooth(TUIOButton):
    def __init__(
            self, id=None, normalized_coords=None, 
            debug=True, center_x=None, center_y=None, 
            is_dirty=False, filth_layer=None, **kwargs
    ):
        super().__init__(normalized_coords, use_grace=True, **kwargs)
        
        # Configuration
        self.id = id
        
        # State
        self.is_clean = True
        self.is_touched = False # Whether the tooth is currently being touched
        self.filth_layer = filth_layer # Reference to the filth layer widget for this tooth
        
        # Brush system
        self.brush_quota = 150 # Total points needed for a brush to count
        self.is_brushing = False # Whether the tooth is currently being brushed
        self.brushes_left = 3 # Number of times to be brushed before being cleaned

        # Callbacks
        self.on_touch_down_callback = None # Called when a brush is completed
        self.on_touch_move_callback = None # Called on every touch move
        self.on_touch_up_callback = None # Called when touch is released
        self.on_reset_callback