
from engine.core.commons import *
from cepilloParty.hud import Menu
#from cepilloParty.managers.inputManager import InputManager



class CepilloParty(Screen):

    def __init__(self, assets, **kwargs):

        # Game state variables
        self.name = 'cepillo_party'
        self.game_active = False
        self.assets = assets 
        # Scores
        self.game_score = 0 # Current score for the ongoing game session
        self.session_scores = [] # List to store scores of each session for ranking purposes
        # Widget related
        self.timer = 0
        self.active_animations = {} # List of currently active animations
        self.menu_button: Button
        self.timerLabel: Label
        # Teeth management
        self.teeth = {}
        self.max_dirty_teeth = 10
        self.filth_layers = {} # Contains the images
        
        super().__init__(**kwargs)

    def on_enter(self):  
        self._setup_game()

    def on_leave(self):
        """Cleanup when leaving the game screen"""
        
        self.game_active = False
        if self.bg_music:
            self.bg_music.stop()

        self.assets.unload_assets() # Unload assets to free memory
    
    def _setup_game(self):
        """Called once to setup the game screen after assets are loaded"""
        
        # Game variables
        self.menu = Menu(self)
        self.game_active = False
        # Music
        self.bg_music = self.assets.get_asset("background_music", "sound")
        self.bg_music.volume = 0.3
        # Remove loading screen and show menu
        self.ids.loading_layout.opacity = 0
        self._load_teeth()
        self.menu.open() 

    def _start_game(self):
        """Starts or restarts the game logic"""
        
        # Setup teeth logic, with dirty teeth randomized each game
        self._setup_teeth()
        # Start background music
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.play()
        # Internal game timer
        self.timer = 300
        self.miliseconds = 0 
        Clock.schedule_interval(self._update, 1/60) # 60 FPS update loop
        
        self.game_active = True
        self.menu.dismiss()
 
    def _end_game(self):
        """Finishes current game session"""
        
        Clock.unschedule(self._update)
        self.game_active = False
        self.bg_music.volume = 0.3
        self.menu.open()

        for filth in self.filth_layers.values():
            self.ids.teeth_filth_layout.remove_widget(filth)
        self.filth_layers.clear()


    
    def _load_teeth(self):
        """Loads tooth configurations and initializes tooth widgets on the screen"""

        with open(self.assets.get_asset("teeth_config", "config"), 'r') as f:
            teeth_data = json.load(f)

        # Process of defining and adding tooth widgets to the game screen
        for tooth_id in sorted(teeth_data.keys()):
            
            # Store coordinates and config
            config = teeth_data[tooth_id]
            normalized_coords = config['coords']
            center_x = sum(p[0] for p in normalized_coords) / len(normalized_coords)
            center_y = sum(p[1] for p in normalized_coords) / len(normalized_coords)

            # Create tooth widget for logic
            tooth = TUIOTooth(
                id=tooth_id, 
                normalized_coords=normalized_coords,
                center_x=center_x,
                center_y=center_y,
                is_button_active=False,
                filth_layer=None
            )
            self.add_widget(tooth)
            self.teeth[tooth_id] = tooth
            
            # Add filth visual layer
            filth_key = f"{tooth_id}_filth_layer"
            filth_layer = Image(
                texture=self.assets.get_asset(filth_key, "image").texture,
                allow_stretch=True, 
                keep_ratio=False
            )
            self.ids.teeth_filth_layout.add_widget(filth_layer)
            filth_layer.opacity = 0 # Hide for now, will be shown when tooth is dirty
            self.filth_layers[tooth_id] = filth_layer
            self.teeth[tooth_id].filth_layer = filth_layer

            # Animations for brushing feedbacK
            foam = AnimatedSprite(
                keys=[tooth_id, 'foam'],
                frames=self.assets.anim_frames['foam'],
                duration=0.2,
                persistent=True,
                sound = self.assets.get_asset("brushing", "sound"),
                game=self,
                pos_hint = {'center_x': center_x, 'center_y': center_y},
                size_hint = (0.4, 0.4)
            )

            tooth.start_foam_cb = foam.play
            tooth.stop_foam_cb = foam.stop
            tooth.layer_cleaned_cb = lambda tk=tooth_id, pos_hint = {'center_x': center_x, 'center_y': center_y}: \
                                    self.layer_cleared_effect(tk,pos_hint)
            
    def _setup_teeth(self):
        """Randomly selects a set of teeth to be dirty at the start of the game"""
        
        all_teeth = list(self.teeth.keys())
        random.shuffle(all_teeth)
        dirty_teeth = all_teeth[:self.max_dirty_teeth]

        for tooth_id in all_teeth:
            tooth = self.teeth[tooth_id]
            is_dirty = tooth_id in dirty_teeth
            
            tooth.reset_tooth() # Reset state first
            if is_dirty:
                tooth.make_dirty() # Mark as dirty and show filth layer
            

    def _update(self, dt):
        """Main update loop for the game, called every frame when active"""
        
        if not self.game_active:
            return
        
        self.miliseconds += dt
        if self.miliseconds >= 60:
            self.miliseconds = 0
            self._update_screen_timer(1) 
        
        for tooth_key, anims in list(self.active_animations.items()):
            dead = [key for key, anim in anims.items() if not anim.step(dt)]
            for key in dead:
                self.remove_widget(anims[key])
                del anims[key]
        pass

    def _update_screen_timer(self, dt):
        """Updates the on screen timer and checks for timeout"""

        self.timer -= 1

        if (self.timer <= 0):
            self.ids.timer_label.text = "TIEMPO" # type: ignore
            # ADD HERE ENDING SEQUENCE
            self._end_game()

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.ids.timer_label.text = f"{mins:02d}:{secs:02d}"
    
    def layer_cleared_effect(self, tooth_key, pos_hint=None):
        """Callback for tooth to do an effect when a layer is cleared"""
        # Clear existing sparkle if there is one for this tooth to avoid duplicates
        if tooth_key in self.active_animations:
            if 'sparkle' in self.active_animations[tooth_key]:
                old = self.active_animations[tooth_key]['sparkle']
                self.remove_widget(old)
                del self.active_animations[tooth_key]['sparkle']
            
        sparkles = AnimatedSprite(
            keys =[tooth_key, 'sparkle'],
            frames=self.assets.anim_frames['sparkle'],
            duration=2,
            persistent=False,
            sound=self.assets.get_asset("clean", "sound"),
            game=self,
            pos_hint=pos_hint,
            size_hint=(0.3, 0.3)
        )
        sparkles.play()


# For tooth logic and management
class TUIOTooth(TUIOButton):
    def __init__(
            self, id=None, normalized_coords=None, 
            debug=True, center_x=None, center_y=None, 
            is_button_active=False, filth_layer=None, **kwargs
    ):
        super().__init__(normalized_coords, use_grace=True, is_button_active=is_button_active, **kwargs)
        
        # Configuration
        self.id = id
        self.filth_layer = filth_layer # Reference to the filth layer widget for this tooth
        self.debug = debug
        self.center_x = center_x
        self.center_y = center_y
        
        # State
        self.is_clean = True
        self.last_position = (0, 0) # Used to track movement for brushing logic
    
        # Brush system
        self.quota_to_clean_layer = 500 # Total points needed for a brush to count
        self.layers_to_clean = 3 # Number of layers of filth to clean for this tooth
        self.brush_score = 0 # Accumulated score towards the next brush

        self.bind(on_cursor_enter=self._handle_enter) # type: ignore
        self.bind(on_cursor_move=self._handle_move) # type: ignore
        self.bind(on_cursor_leave=self._handle_leave) # type: ignore

        # Callbacks for animations and effects
        self.start_foam_cb: Optional[Callable[[], None]] = None
        self.stop_foam_cb: Optional[Callable[[], None]] = None
        self.layer_cleaned_cb: Optional[Callable[[], None]] = None
        

    def _handle_enter(self, instance, touch):
        
        # Ignore if already clean
        if self.is_clean:
            return

        self.last_position = touch.pos
        
        # Start foam animation
        if self.start_foam_cb:
            self.start_foam_cb()
            
    def _handle_move(self, instance, touch):

        # Point system
        delta_x = abs(touch.x - self.last_position[0])
        delta_y = abs(touch.y - self.last_position[1])
        self.brush_score += delta_x/2 + delta_y/2
        
        if self.brush_score >= self.quota_to_clean_layer:
            self._clean_layer()
            
    def _handle_leave(self, instance, touch=None):
        self.brush_score = 0
        
        # Stop foam animation
        if self.stop_foam_cb:
            self.stop_foam_cb()

    def _clean_layer(self):
        """Removes one layer of filth from the tooth and updates visuals"""
        
        self.brush_score -= self.quota_to_clean_layer
        self.layers_to_clean -= 1
        print(f"Cleaned one layer, layers remaining {self.layers_to_clean}")  
        self.layer_cleaned_cb() # type: ignore

        if self.filth_layer:
            self.filth_layer.opacity = max(0, self.filth_layer.opacity - (1 / 3))
        
        if self.layers_to_clean <= 0:
            self.reset_tooth()
    
    def reset_tooth(self):
        """Resets tooth state for a new game session"""
        
        self.is_clean = True
        self.active = False # Disable touch handling

        self.stop_foam_cb() # type: ignore

        self.filth_layer.opacity = 0 # type: ignore
        
    def make_dirty(self):
        """Marks this tooth as dirty and ready for interaction"""
        
        self.is_clean = False
        self.active = True # Enable touch handling

        self.layers_to_clean = 3
        self.brush_score = 0
        
        self.stop_foam_cb() # type: ignore

        self.filth_layer.opacity = 1 # type: ignore