
from engine.core.commons import *
from cepilloParty.hud import Menu
from engine.core.AssetManager import AssetManager
#from cepilloParty.managers.inputManager import InputManager



class CepilloParty(Screen):

    def __init__(self, assets : AssetManager, **kwargs):

        super().__init__(**kwargs)
        # Game state variables
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
        self.teeth_cleaned = 0
        
        

    def on_enter(self):  
        self._setup_game()

    def on_leave(self):
        """Cleanup when leaving the game screen"""
        
        self.game_active = False
        if self.bg_music:
            self.bg_music.stop()

        # Remove all active animation widgets and stop their audio
        for anims in self.active_animations.values():
            for anim in anims.values():
                anim.stop()
                self.remove_widget(anim)
        self.active_animations.clear()
        
        # Remove all tooth widgets and their related
        for tooth in self.teeth.values():
            if tooth.filth_layer:
                self.ids.teeth_filth_layout.remove_widget(tooth.filth_layer)
            if tooth.grace and tooth.grace.is_active():
                tooth.grace.cancel()          
            self.remove_widget(tooth)
        self.teeth.clear()

        self.assets.unload_assets() # Unload assets to free memory

    def _setup_game(self):
        """Called once to setup the game screen after assets are loaded"""
        
        # Game variables
        self.menu = Menu(self)
        self.game_active = False
        # Music
        self.bg_music = None
        #self.bg_music = self.assets.get_asset("background_music", "sound")
        #self.bg_music.volume = 0.3
        # Remove loading screen and show menu
        self.ids.loading_layout.opacity = 0
        self._load_teeth()
        self.menu.open() 

    def _start_game(self):
        """Starts or restarts the game logic"""
        self.teeth_cleaned = 0
        self.game_score = 0
        self._setup_teeth()
        
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.play()
        
        # Internal game timer
        self.timer = 180
        mins, secs = divmod(self.timer, 60)
        self.ids.timer_label.text = f"{mins:02d}:{secs:02d}"   # ← this line
        
        Clock.schedule_interval(self._update, 1/60)
        Clock.schedule_interval(self._update_screen_timer, 1.0)
        
        self.game_active = True
        self.menu.dismiss()
 
    def _end_game(self, won=False):
        """Finishes current game session"""
        Clock.unschedule(self._update)
        Clock.unschedule(self._update_screen_timer)
        self.game_active = False

        # Store score for ranking
        self.session_scores.append(self.game_score)
        self.session_scores.sort(reverse=True)
        self.menu.update_ranking(self.session_scores)
        
        self._show_score_popup(won)


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
            self.teeth[tooth_id].filth_layer = filth_layer

            # Animations for brushing feedbacK
            foam = AnimatedSprite(
                keys=[tooth_id, 'foam'],
                frames=self.assets.anim_frames['foam'],
                duration=0.2,
                persistent=True,
                #sound = self.assets.get_asset("brushing", "sound"),
                game=self,
                pos_hint = {'center_x': center_x, 'center_y': center_y},
                size_hint = (1.3, 1.3)
            )

            brush = Toothbrush(self.assets)
            self.add_widget(brush)
            tooth.toothbrush = brush

            tooth.start_foam_cb = foam.play
            tooth.stop_foam_cb = foam.stop
            tooth.layer_cleaned_cb = lambda tk=tooth_id, pos_hint = {'center_x': center_x, 'center_y': center_y}: \
                                    self.layer_cleared(tk,pos_hint)
            
    def _setup_teeth(self):
        """Randomly selects a set of teeth to be dirty at the start of the game"""

        teeth_ids = random.sample(list(self.teeth.keys()), self.max_dirty_teeth)

        for tooth_id in teeth_ids:
            self.teeth[tooth_id].make_dirty() # Mark as dirty and show filth layer
            
    def _update(self, dt):
        """Main update loop for the game, called every frame when active"""
        
        if not self.game_active:
            return
             
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
            self._end_game(won=False)

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.ids.timer_label.text = f"{mins:02d}:{secs:02d}"
    
    def layer_cleared(self, tooth_key, pos_hint=None):
        """Callback for tooth to do an effect when a layer is cleared"""
        # Increment score and check for win condition
        if self.teeth[tooth_key].layers_to_clean <= 0:
            self.game_score += TOOTH_BASE_POINTS + (self.timer * TOOTH_TIME_MULTIPLIER)
            self.teeth_cleaned += 1
            
            # Win condition
            if self.teeth_cleaned >= self.max_dirty_teeth:
                self.game_score += COMPLETION_BONUS
                self.game_score += self.timer * COMPLETION_TIME_MULTIPLIER
                self._end_game(won=True)
                return

        
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

    def _show_score_popup(self, won):
        """Shows a centered score popup, then opens the menu when done"""
        
        headline = "¡COMPLETADO!" if won else "¡SE ACABÓ EL TIEMPO!"
        
        popup = Label(
            text=f"{headline}\n\n{self.game_score} PUNTOS",
            font_size='80sp',
            bold=True,
            halign='center',
            color=(1, 1, 1, 0),  # start fully transparent
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            size_hint=(0.6, 0.4),
        )
        popup.bind(size=lambda inst, val: setattr(inst, 'text_size', val))  # wraps text
        self.add_widget(popup)
        
        # Animation: fade in (0.4s) → hold (1.8s) → fade out (0.6s) → open menu
        fade_in = Animation(color=(1, 1, 1, 1), duration=0.4)
        hold = Animation(color=(1, 1, 1, 1), duration=2.5)
        fade_out = Animation(color=(1, 1, 1, 0), duration=0.6)
        
        sequence = fade_in + hold + fade_out
        sequence.bind(on_complete=lambda *args: self._finish_popup(popup))
        sequence.start(popup)

    def _finish_popup(self, popup):
        """Called when popup animation finishes"""
        for tooth in self.teeth.values():
            tooth.reset_tooth()
        
        if self.bg_music:
            self.bg_music.stop()
            
        self.remove_widget(popup)
        
        self.menu.open()


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
        self.toothbrush: Optional[Toothbrush] = None # Reference to the toothbrush widget that interacts with this tooth
        self.quota_to_clean_layer = 650 # Total points needed for a brush to count
        self.layers_to_clean = 3 # Number of layers of filth to clean for this tooth
        self.brush_score = 0 # Accumulated score towards the next brush
        self._stillness_timer = None

        self.bind(on_cursor_enter=self._handle_enter) # type: ignore
        self.bind(on_cursor_move=self._handle_move) # type: ignore
        self.bind(on_cursor_leave=self._handle_leave) # type: ignore

        # Callbacks for animations and effects
        self.start_foam_cb: Optional[Callable[[], None]] = None
        self.stop_foam_cb: Optional[Callable[[], None]] = None
        self.layer_cleaned_cb: Optional[Callable[[], None]] = None

        
        

    def _handle_enter(self, instance, touch):
        if self.is_clean:
            return
        self.last_position = touch.pos
        if self.toothbrush:
            self.toothbrush.move_to(*touch.pos)
            self.toothbrush.show_paste()
            self.toothbrush.show()


    def _handle_move(self, instance, touch):
        delta_x = abs(touch.x - self.last_position[0])
        delta_y = abs(touch.y - self.last_position[1])
        movement = delta_x / 2 + delta_y / 2

        # Only register as brushing if there's actual displacement
        if movement > 0:
            self.brush_score += movement

            # Show foam on movement
            if self.start_foam_cb:
                self.start_foam_cb()
                if self.toothbrush:
                    self.toothbrush.move_to(*touch.pos) 
                    self.toothbrush.hide_paste() # Hide paste while moving
                    self.toothbrush.show()

            # Restart stillness timer
            self._reset_stillness_timer()

            if self.brush_score >= self.quota_to_clean_layer:
                self._clean_layer()

        self.last_position = touch.pos

    def _handle_leave(self, instance, touch=None):
        self.brush_score = 0
        self._cancel_stillness_timer()
        if self.stop_foam_cb:
            self.stop_foam_cb()
            if self.toothbrush:
                self.toothbrush.hide()

    def _reset_stillness_timer(self):
        """Restart the stillness countdown"""
        self._cancel_stillness_timer()
        self._stillness_timer = Clock.schedule_once(
            self._on_cursor_still, STILLNESS_THRESHOLD
        )

    def _cancel_stillness_timer(self):
        if self._stillness_timer:
            Clock.unschedule(self._stillness_timer)
            self._stillness_timer = None

    def _on_cursor_still(self, dt):
        """Fired when no movement has been detected for STILLNESS_THRESHOLD seconds"""
        self._stillness_timer = None
        if self.stop_foam_cb:
            self.stop_foam_cb()
            if self.toothbrush:
                self.toothbrush.show_paste()

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
        self.is_clean = True
        self.active = False
        self.owner_uid = None
        self.toothbrush.hide()
        if self.grace:
            self.grace.cancel()
        self._cancel_stillness_timer()
        self.stop_foam_cb()
        self.filth_layer.opacity = 0

    def make_dirty(self):
        self.is_clean = False
        self.active = True
        self.layers_to_clean = 3
        self.brush_score = 0
        self._cancel_stillness_timer()
        self.filth_layer.opacity = 1


class Toothbrush(Image):
    def __init__(self, assets: AssetManager, **kwargs):
        super().__init__(**kwargs)
        self.no_paste_texture = assets.get_asset("brush", "image").texture
        self.paste_texture = assets.get_asset("toothpaste_brush", "image").texture
        self.texture = self.no_paste_texture
        self.opacity = 0
        self.size_hint = (None, None)  # fixed size, not relative
        
        tex_w = self.texture.width
        tex_h = self.texture.height
        
        # Then scale to whatever display size you want
        display_width = Window.width * 0.5
        display_height = display_width * (tex_h / tex_w)  # ratio from actual texture

        self.size = (display_width, display_height)

        # Offset is now derived from the actual display dimensions
        self._offset_x = display_width * 0.67   # was 0.90 — bristles aren't that far right
        self._offset_y = display_height * 0.45

    
    def move_to(self, touch_x, touch_y):
        self.x = touch_x - self._offset_x
        self.y = touch_y - self._offset_y

    def show(self):
        self.opacity = 1

    def hide(self):
        self.opacity = 0

    def show_paste(self):
        self.texture = self.paste_texture

    def hide_paste(self):
        self.texture = self.no_paste_texture
