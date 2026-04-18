from engine.core.commons import *
from engine.core.GameState import game



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
        self.load_assets()
          
    def load_assets(self):
        """Preloads all necessary assets for the game"""
        
        # Background image
        self.layout.add_widget(Image(
            source=os.path.join(IMAGES_PATH, 'Fondo.png'),
            allow_stretch=True,
            keep_ratio=False
        ))

        # Background music
        bg_path = os.path.join(SOUNDS_PATH, 'background.mp3')
        self.bg_music = SoundLoader.load(bg_path)
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.volume = 0.4
            self.bg_music.play()
        else:
            print("Background music couldn't be loaded")

        # Clean sound
        clean_sound_path = os.path.join(SOUNDS_PATH, 'clean.mp3')
        self.clean_sound = SoundLoader.load(clean_sound_path)

        # Fonts
        main_font_path = os.path.join(FONTS_PATH, "mainfont.ttf")

        
        LabelBase.register(
            name="main_font", 
            fn_regular=main_font_path
        )

        # Load JSON configuration
        json_path = os.path.join(KV_LANG_PATH, 'teethconfig.json') 
        with open(json_path, 'r') as f:
            self.teethConfig = json.load(f)

    def restart_game(self):
        """Initializes a new game session"""
        print("Starting new game...")
        
        # Clear previous game if exists
        self.clear_widgets()
        
        # Setup new game
        
        self.setup_game()
        Clock.schedule_interval(self.update_timer, 1.0)
        self.game_active = True
    
    def setup_game(self):
        """Sets up all game elements"""
        
        # Clock setup
        Clock.unschedule(self.update_timer)
        
        # Score setup
        game.score = 0

        # Game data dictionaries
        self.teeth_logic_list = {}
        self.filth_visuals = {}
        self.foam_visuals = {}
        self.sparkle_visuals = {}


        # Select random teeth to clean
        teeth_id_list = list(self.teethConfig.keys())
        num_of_teeths_to_clean = 10
        teeths_to_clean = random.sample(teeth_id_list, num_of_teeths_to_clean)
        

        # Brush visualizer
        self.visualizador_cepillo = TuioCursorImage()
        
        # Create teeth
        for tooth_id in sorted(self.teethConfig.keys()):
            config = self.teethConfig[tooth_id]
            
            print(f"Loading tooth {tooth_id}...")
            
            is_clean = tooth_id not in teeths_to_clean
            
            # Get data from JSON
            normalized_coords = config['coords']
            center_x = sum(p[0] for p in normalized_coords) / len(normalized_coords)
            center_y = sum(p[1] for p in normalized_coords) / len(normalized_coords)
            
            # Manage dirty teeth
            if not is_clean:
                # Filth visual layer
                filth_layer_path = os.path.join(IMAGES_PATH, config['filth_layer_path'])
                filth_layer = Image(
                    source=filth_layer_path, 
                    allow_stretch=True, 
                    keep_ratio=False
                )
                self.filth_visuals[tooth_id] = filth_layer
                self.layout.add_widget(filth_layer)

                # Foam visual
                foam_visual = Image(
                    source=os.path.join(IMAGES_PATH, 'espuma.gif'),
                    pos_hint={'center_x': center_x, 'center_y': center_y},
                    size_hint=(0.2, 0.2), 
                    keep_ratio=False,
                    anim_delay=-1,
                    opacity=0
                )
                self.foam_visuals[tooth_id] = foam_visual
                self.layout.add_widget(foam_visual)

                # Layer cleaned animation
                clean_gif = Image(
                    source=os.path.join(IMAGES_PATH, 'layercleaned.gif'),
                    size_hint=(0.3, 0.3), 
                    keep_ratio=False,
                    anim_delay=-1,
                    opacity=0,
                    pos_hint={'center_x': center_x, 'center_y': center_y},
                )
                self.sparkle_visuals[tooth_id] = clean_gif
                self.layout.add_widget(clean_gif)

            # Tooth logic widget
            tooth_logic = TUIOTooth(
                normalized_coords=normalized_coords,
                tooth_id=tooth_id,
                debug_draw=True,
                brush_visualizer=self.visualizador_cepillo,
                center_x=center_x,
                center_y=center_y,
                is_clean=is_clean
            )

            tooth_logic.on_brush_stroke = lambda tid=tooth_id: self.handle_brush_stroke(tid)
            tooth_logic.on_brush_start = lambda tid=tooth_id: self.start_foam_animation(tid)
            tooth_logic.on_brush_stop = lambda tid=tooth_id: self.stop_foam_animation(tid)
            
            self.teeth_logic_list[tooth_id] = tooth_logic
            self.layout.add_widget(tooth_logic)

        # Skin overlay
        self.layout.add_widget(Image(
            source=os.path.join(IMAGES_PATH, 'Piel (caraserhumano).png'),
            allow_stretch=True,
            keep_ratio=False
        ))


        #Resets timer state
        Clock.unschedule(self.update_timer) 
        self.timer = 180
        
        # Timer
        self.timeLabel = Label(
            text=f"{self.timer// 60:02d}:{self.timer % 60:02d}",
            font_name = "main_font",
            size_hint=(1, 0.1),
            pos_hint={'right': 1, 'top': 1},
            color=(1, 1, 1, 1), 
            font_size='20sp'
        )

        # Add brush visualizer
        self.layout.add_widget(self.visualizador_cepillo)
        
        # Add menu button on top
        self.layout.add_widget(self.menu_button)

        self.layout.add_widget(self.timeLabel)
             
    def update_timer(self, dt):
        self.timer -= 1

        if (self.timer <= 0):
            self.timeLabel.text = "TIEMPO"
            self.game_active = False
            # ADD HERE ENDING SEQUENCE
            game.sm.current = 'menu'

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.timeLabel.text = f"{mins:02d}:{secs:02d}"
        
    def handle_brush_stroke(self, tooth_id):
        """Called each time a brush stroke quota is completed"""
        if tooth_id not in self.teeth_logic_list:
            print(f"Tooth {tooth_id} not found")
            return
            
        tooth_logic = self.teeth_logic_list[tooth_id]
        filth_visual = self.filth_visuals[tooth_id]
        sparkle_visual = self.sparkle_visuals[tooth_id]

        #Visual and sound effect
        self.start_brushed_animation(sparkle_visual)
        self.clean_sound.play()

        print(f"Brushed {tooth_logic.tooth_id}. Remaining: {tooth_logic.brush_to_clean}")

        #Point handler
        self.game_score += (1000*(1+self.timer/150))

        if tooth_logic.brush_to_clean <= 0:
            filth_visual.opacity = 0
            self.stop_foam_animation(tooth_id)
            tooth_logic.brush_visualizer.remove_brush(tooth_logic.cursor_inside)
            tooth_logic.is_clean = True
            print(f"{tooth_logic.tooth_id} is now clean.")
        
        if tooth_logic.is_clean:
            self.check_for_win()
    
    def check_for_win(self):
        """Checks if all teeth are clean and shows victory screen"""
        for tooth in self.teeth_logic_list.values():
            if not tooth.is_clean:
                return

        #Extra points for timer
        self.game_score += self.timer*33
        print(f"Puntación final {self.game_score}")
        print("All teeth clean! Returning to menu.")
        self.game_active = False

        # ADD HERE ENDING SEQUENCE
        game.sm.current = 'menu'
        

    def start_brushed_animation(self, sparkle_animation):
        """Starts the sparkle animation when a layer is cleaned"""
        sparkle_animation.anim_delay = 0.05
        sparkle_animation.opacity = 1
        Clock.schedule_once(
            lambda dt: self.stop_brushed_animation(sparkle_animation), 
            1.8
        )

    def stop_brushed_animation(self, sparkle_animation):
        """Stops the sparkle animation"""
        sparkle_animation.anim_delay = -1
        sparkle_animation.opacity = 0

    def start_foam_animation(self, tooth_id):
        """Starts foam animation when brushing begins"""
        if tooth_id in self.foam_visuals:
            foam_visual = self.foam_visuals[tooth_id]
            foam_visual.opacity = 1
            foam_visual.anim_delay = 0.1
        else:
            print("ToothID not found for foam creation")

    def stop_foam_animation(self, tooth_id):
        """Stops foam animation when brushing ends"""
        if tooth_id in self.foam_visuals:
            foam_visual = self.foam_visuals[tooth_id]
            foam_visual.opacity = 0
            foam_visual.anim_delay = -1
        else:
            print("ToothID not found for foam removal")
    
    def back_to_menu(self, instance):
        """Returns to main menu"""

        self.game_active = False
        
        # Stop background music
        if self.bg_music:
            self.bg_music.stop()
            self.bg_music.unload()
        
        game.current_game = None
        game.sm.current = 'menu'

class TuioCursorImage(Widget):
    """Visualizes the toothbrush cursor for TUIO input"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursors = {}
        self.size_hint = (1, 1)
        self.pos = (0, 0)
        
        # Image definitions
        self.image_source = os.path.join(IMAGES_PATH, 'cepilloConPasta.png')
        self.brushing_sound_source = os.path.join(SOUNDS_PATH, 'brushing.mp3')
        self.brushing_sound = SoundLoader.load(self.brushing_sound_source)
        self.brushing_sound.loop = True
        self.brushing_sound.volume = 0.5

        self.image_aspect_ratio = 1.0 / 3.47  # 519 / 1800
        self.relative_width = 0.5  # Brush width relative to screen
        self.image_anchor_offset_relative = (0.90, 0.5)

    def _calculate_pos_size(self, touch):
        # 1. Calculate actual brush size in pixels
        actual_width = self.width * self.relative_width 
        actual_height = actual_width * self.image_aspect_ratio
        
        # 2. Calculate anchor offset in pixels
        offset_x = actual_width * self.image_anchor_offset_relative[0]
        offset_y = actual_height * self.image_anchor_offset_relative[1]
        
        # 3. Calculate position (bottom-left corner) of rectangle
        pos_x = touch.x - offset_x
        pos_y = touch.y - offset_y
            
        return (pos_x, pos_y), (actual_width, actual_height)

    def draw_brush(self, touch):
        """Creates a new brush cursor"""
        if touch.uid in self.cursors:
            print(f"Brush {touch.uid} already created")
            return

        pos, size = self._calculate_pos_size(touch)
        self.brushing_sound.play()

        with self.canvas:
            Color(1, 1, 1, 1)
            rect = Rectangle(
                source=self.image_source,
                pos=pos,  
                size=size  
            )
        
        self.cursors[touch.uid] = rect

    def move_brush(self, touch):
        """Updates brush cursor position"""
        if touch.uid in self.cursors:
            pos, size = self._calculate_pos_size(touch)
            self.cursors[touch.uid].pos = pos
            self.cursors[touch.uid].size = size
        else:
            self.draw_brush(touch)

    def remove_brush(self, uid):
        """Removes a brush cursor"""
        self.brushing_sound.stop()
        self.brushing_sound.unload()
        cursor_rect = self.cursors.pop(uid, None) 
        if cursor_rect:
            self.canvas.remove(cursor_rect)
        
class TUIOTooth(Widget):
    """
    Widget that defines an interactive tooth zone with four normalized coordinates
    and responds to TUIO cursors using Ray Casting algorithm for hit detection.
    """
    
    def __init__(self, normalized_coords, center_x, center_y, is_clean, tooth_id=None, 
                 debug_draw=False, brush_visualizer=None, **kwargs):
        """
        Args:
            normalized_coords: List of 4 tuples with normalized coordinates (points should be ordered)
            center_x: Normalized X coordinate of tooth center
            center_y: Normalized Y coordinate of tooth center
            is_clean: Boolean indicating if tooth starts clean
            tooth_id: Unique tooth identifier (string)
            debug_draw: If True, draws trigger boundaries on screen
            brush_visualizer: Reference to TuioCursorImage instance
        """
        super().__init__(**kwargs)
        
        # Configuration storage
        self.normalized_coords = normalized_coords
        self.tooth_id = tooth_id
        self.debug_draw = debug_draw
        self.brush_visualizer = brush_visualizer
        self.center_x = center_x
        self.center_y = center_y
        self.is_clean = is_clean
        
        # Cursor state handling
        self.cursor_inside = None
        self.is_being_touched = False
        self.grace_period = 0.3
        self.pending_reset = None
        self.dt = None
        
        # Brush logic
        self.brush_to_clean = 3
        self.brush_score = 0.0
        self.last_pos = (0, 0)
        self.brush_quota = 150  # Points needed for 1 brush stroke
        self.is_brushing = False
        
        # Configurable bias for movement detection
        self.y_weight = 0.5  # Vertical movement counts DOUBLE
        self.x_weight = 0.5  # Horizontal movement counts HALF

        # Customizable callbacks
        self.on_tooth_touch_down = lambda touch: None
        self.on_tooth_touch_move = lambda touch: None
        self.on_tooth_touch_up = lambda touch, duration: None
        self.on_brush_stroke = lambda: None
        self.on_brush_start = lambda: None
        self.on_brush_stop = lambda: None
        
        # Widget configuration - full screen size
        self.size_hint = (1, 1)
        self.pos = (0, 0)
        self.points_pixels = []

        # Initialize points
        self.points_pixels = self._get_polygon_points_pixels()

        # Debug drawing
        if self.debug_draw:
            self._draw_polygon()       
        
        # Bind to redraw if window resizes
        Window.bind(on_resize=self._update_pixel_coordinates)
    
    # =========================================================================
    # COORDINATE CONVERSION
    # =========================================================================
    
    def _normalized_to_pixels(self, x_norm, y_norm):
        """Converts normalized coordinates (0.0-1.0) to pixels"""
        return (x_norm * Window.width, y_norm * Window.height)
    
    def _get_polygon_points_pixels(self):
        """Gets polygon points in pixel coordinates"""
        return [self._normalized_to_pixels(x, y) for x, y in self.normalized_coords]
    
    # =========================================================================
    # RAY CASTING ALGORITHM
    # =========================================================================
    
    def point_inside_polygon(self, x, y):
        """
        Determines if a point (x, y) is inside the polygon using Ray Casting.
        
        Algorithm:
        - Casts a horizontal ray to the right from the point
        - Counts how many times it intersects with polygon edges
        - If number of intersections is odd → point INSIDE
        - If number is even → point OUTSIDE
        """
        polygon = self.points_pixels
        n = len(polygon)
        
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    # =========================================================================
    # KIVY TOUCH EVENTS
    # =========================================================================
    
    def on_touch_down(self, touch):
        """Handles when a TUIO cursor touches the screen"""
        if self.point_inside_polygon(touch.x, touch.y):
            if self.is_clean:
                print("Trying to clean an already clean tooth")
            elif self.pending_reset is not None:
                print(f"Cursor recovered!")
                self._start_brushing(touch)
            elif self.cursor_inside is None:
                self._start_brushing(touch)
            else:
                print(f"Touch rejected, cursor {self.cursor_inside} already inside")
        
        return False
    
    def on_touch_move(self, touch):
        """Called when a TUIO cursor MOVES"""
        is_inside = self.point_inside_polygon(touch.x, touch.y)

        # Register that a cursor entered from outside
        if self.cursor_inside is None and is_inside:
            self._start_brushing(touch)

        elif touch.uid == self.cursor_inside:
            if is_inside:
                if not self.is_clean:
                    if self.brush_visualizer:
                        self.brush_visualizer.move_brush(touch)

                    # Point system
                    delta_x = abs(touch.x - self.last_pos[0])
                    delta_y = abs(touch.y - self.last_pos[1])
                    weighted_distance = (delta_x * self.x_weight) + (delta_y * self.y_weight)
                    self.brush_score += weighted_distance
                    
                    if self.brush_score >= self.brush_quota:
                        self.brush_score -= self.brush_quota
                        self.brush_to_clean -= 1
                        print(f"Cleaned one layer, brushes remaining {self.brush_to_clean}")
                        self.on_brush_stroke()
                        
                self.last_pos = touch.pos
            else:
                # Reset only if tracked cursor leaves the area
                print(f"Cursor {touch.uid} left tooth {self.tooth_id}")
                self._reset_state(self.dt) 
            
        return False
    
    def on_touch_up(self, touch):
        """Called when a cursor is lifted"""
        if touch.uid != self.cursor_inside:
            return False
        
        self.pending_reset = Clock.schedule_once(self._reset_state, self.grace_period)
        
        print(f"[TUIOTooth {self.tooth_id}] Touch UP - Cursor {touch.uid}")
        print(f"Remaining brushes: {self.brush_to_clean}")
        print(f"Score for brush count: {self.brush_score}")
        
        return True
    
    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================

    def _start_brushing(self, touch):
        """Initializes the brushing state"""
        if self.is_clean:
            return False 

        if self.pending_reset is not None:
            self.brush_visualizer.remove_brush(self.cursor_inside)
            Clock.unschedule(self.pending_reset)
            self.pending_reset = None
            print(f"Successfully restored a cursor!")
        
        self.cursor_inside = touch.uid
        self.is_being_touched = True
        self.brush_score = 0.0
        self.last_pos = touch.pos

        if self.brush_visualizer:
            self.brush_visualizer.draw_brush(touch)

        self.on_brush_start()

    def _reset_state(self, dt):
        """Resets widget to initial state when touch cancels or ends"""
        if self.brush_visualizer:
            self.brush_visualizer.remove_brush(self.cursor_inside)

        self.cursor_inside = None
        self.touch_start_time = None
        self.is_being_touched = False
        self.pending_reset = None
        self.on_brush_stop()
    
    # =========================================================================
    # VISUALIZATION (DEBUG)
    # =========================================================================
    
    def _draw_polygon(self):
        """Draws polygon on canvas for debug visualization"""
        with self.canvas:
            Color(0, 1, 0, 0.3)  # Green with alpha=0.3
            
            points_px = self._get_polygon_points_pixels()
            
            flat_points = []
            for x, y in points_px:
                flat_points.extend([x, y])
            
            Line(points=flat_points, close=True, width=2)
    
    def _update_pixel_coordinates(self, window, width, height):
        """Callback when window resizes - redraws polygon with new dimensions"""
        self.points_pixels = self._get_polygon_points_pixels()
        if self.debug_draw:
            self.canvas.clear()
            self._draw_polygon()
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_center_point(self):
        """Calculates approximate center of polygon (average of vertices)"""
        points_px = self._get_polygon_points_pixels()
        x_avg = sum(p[0] for p in points_px) / len(points_px)
        y_avg = sum(p[1] for p in points_px) / len(points_px)
        return (x_avg, y_avg)
    
    def get_info(self):
        """Returns widget information for debugging"""
        return {
            'tooth_id': self.tooth_id,
            'is_being_touched': self.is_being_touched,
            'cursor_inside': self.cursor_inside,
            'normalized_coords': self.normalized_coords, 
            'points_pixels': self._get_polygon_points_pixels(),
            'center': self.get_center_point()
        }
    
