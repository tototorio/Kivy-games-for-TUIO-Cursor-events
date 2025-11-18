import os
import json
import random
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock
from kivy.config import Config

# TUIO Config
Config.set('input', 'tuio_listener', 'tuio,127.0.0.1:3333')


class Fps():
    """FPS counter"""
    def __init__(self):
        self.fps_label = Label(text='FPS: 0', size_hint=(None, None), size=(200, 50))
        # Position the label in the top-right corner
        self.fps_label.pos = (Window.width - self.fps_label.width, Window.height - self.fps_label.height)
        
        Clock.schedule_interval(self.update_fps, 1/2.0)  # Update every 0.5 seconds

    def update_fps(self, dt):
        self.fps_label.text = f'FPS: {int(Clock.get_fps())}'
        # Reposition if window size changes
        self.fps_label.pos = (Window.width - self.fps_label.width, Window.height - self.fps_label.height)


class TuioCursorImage(Widget):
    """Visualizes the toothbrush cursor for TUIO input"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursors = {}
        self.size_hint = (1, 1)
        self.pos = (0, 0)
        
        # Image definitions
        script_path = os.path.dirname(os.path.abspath(__file__))
        self.image_source = os.path.join(script_path, 'assets/cepilloConPasta.png')
        self.brushing_sound_source = os.path.join(script_path, 'sounds/brushing.mp3')
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

class RankingModalView(ModalView):
    
    def __init__(self, menu, **kwargs):
        super().__init__(**kwargs)
        
        self.menu = menu

        #Modal view config 
        self.size_hint = (0.5, 0.9)
        self.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.overlay_color = (0, 0, 0, 0.9)
        #self.auto_dismiss = False  # Prevent closing by clicking outside
        self.background = os.path.join(self.menu.assets_path, "ranking.png")

        # Load JSON configuration
        self.json_path = os.path.join(self.menu.script_path, 'config/ranking.json') 
        with open(self.json_path, 'r') as f:
            self.ranking = json.load(f)

        self.grid = GridLayout(
            cols=2, 
            spacing=[20, 10],
            size_hint=(0.8, 0.55),
        )

        self.highscores_label = []
        self.highscores = []

        for index, score_data in enumerate(self.ranking):
            
            score = score_data.get('score', 0)
            score_text = f"{index+1}.   {score}"
            name_text = score_data.get('name', '---')

            # Position label (left-aligned)
            label_score = Label(
                text=score_text,
                size_hint=(0.3, None),
                height=50,
                font_name = "fun_font",
                font_size='35sp',
                halign='left',
                valign='middle',
                color=(0, 0.29, 0.6785, 1)
            )
            label_score.bind(size=label_score.setter('text_size'))
            
            # Name label (right-aligned)
            label_name = Label(
                text=name_text,
                size_hint=(0.3, None),
                height=50,
                font_size='35sp',
                halign='right',
                valign='middle',
                color=(0, 0.29, 0.6785, 1)
            )
            label_name.bind(size=label_name.setter('text_size'))
            
            self.grid.add_widget(label_score)
            self.grid.add_widget(label_name)

            self.highscores_label.append([label_score, label_name])
            self.highscores.append([score, name_text])
        
        self.add_widget(self.grid)
        

    def update_score(self, new_score, name):
        with open(self.json_path, 'r') as f:
            self.ranking = json.load(f)
        
        for index, score_data in enumerate(self.ranking):
            player_score = int(score_data.get('score', 0))

            if new_score >= player_score:
                self.ranking.append({"score":new_score, "name":name})
                self.ranking.sort(
                    key=lambda item: int(item.get("score", 0)),
                    reverse=True
                )
                self.ranking = self.ranking[:10]

                with open(self.json_path, 'w') as f:
                    json.dump(self.ranking, f, indent=4)
                    print(f"Ranking actualizado. {name} añadió {new_score} puntos.")

                #Update graphics for score
                self.highscores.append([new_score, name])
                self.highscores.sort(key=lambda column: column[0], reverse=True)
                self.highscores = self.highscores[:10]
                for index, row in enumerate(self.highscores_label):
                    row[0].text = f"{index+1}. {self.highscores[index][0]}"
                    row[1].text = f"{self.highscores[index][1]}"
                break

    def close(self):
        self.dismiss()
            
        

class MenuModalView(ModalView):
    """
    Main menu overlay that pauses the game.
    Appears at app start, after game completion, or when menu button is pressed.
    """
    
    def __init__(self, game_screen, **kwargs):
        super().__init__(**kwargs)
        
        self.script_path = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(self.script_path, "assets")
        self.fonts_path = os.path.join(self.script_path, "fonts")

        self.game_screen = game_screen
        self.ranking_view = RankingModalView(self)
        
        # ModalView configuration
        self.size_hint = (1, 1)
        self.auto_dismiss = False  # Prevent closing by clicking outside
        self.background_color = (0, 0, 0, 0.85)  # Semi-transparent dark
        self.background_color = (0, 0, 0, 0.85)  # Semi-transparent dark background background
        self.background = os.path.join(self.assets_path, "menubackground.png")

        self.rows_ranking_label = []
        self.rows_ranking_data = []

        layout = FloatLayout()

        # Welcome/Title label
        self.title_label = Label(
            text="CEPILLO PARTY",
            font_size='40sp',
            size_hint=(1, 0.3),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            color=(1, 1, 1, 1)
        )
        layout.add_widget(self.title_label)
        
        # Play button (centered)
        play_button = Button(
            size_hint=(0.4, 0.5),
            pos_hint={'center_x': 0.5, 'center_y': 0.4},
            background_normal = os.path.join(self.assets_path, "start_icon.png"),
        )
        play_button.bind(on_press=self.start_game)
        layout.add_widget(play_button)
        
        # Ranking button (below play button)
        ranking_button = Button(
            size_hint=(0.18, 0.25),
            pos_hint={'center_x': 0.9, 'center_y': 0.85},
            background_normal = os.path.join(self.assets_path, "ranking_icon.png"),
        )
        ranking_button.bind(on_press=self.show_ranking)
        layout.add_widget(ranking_button)

        self.day_ranking_box = BoxLayout(
            orientation = 'vertical',
            size_hint = (0.2, 0.8),
            pos_hint = {'center_x':0.18, 'center_y': 0.7},
            spacing = 10,
            padding = 10
        )

        day_ranking_title = Label(
            text = "TOP DEL DIA",
            font_name = "fun_font",
            font_size = '40sp',
            height=60,
            size_hint = (0.8, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.9},
            color = (0.823, 0.9, 0.121, 1),
            bold = True
        )

        self.day_ranking_box.add_widget(day_ranking_title)


        self.day_ranking_grid = GridLayout(
            cols=2, 
            spacing=[20, 10], 
            size_hint=(1, None),
            height=250
        )

        for row in range(5):
            # Position label (left-aligned)
            label_score = Label(
                text=f"{row+1}. 0",
                size_hint=(0.3, None),
                height=50,
                font_name = "fun_font",
                font_size='28sp',
                halign='left',
                valign='middle',
                color=(1, 0.922, 0.6, 1)
            )
            label_score.bind(size=label_score.setter('text_size'))
            
            # Name label (right-aligned)
            label_name = Label(
                text="---",
                size_hint=(0.3, None),
                height=50,
                font_size='28sp',
                halign='right',
                valign='middle',
                color=(1, 0.922, 0.6, 1)
            )
            label_name.bind(size=label_name.setter('text_size'))
            
            self.day_ranking_grid.add_widget(label_score)
            self.day_ranking_grid.add_widget(label_name)
            
            self.rows_ranking_label.append([label_score, label_name])
            self.rows_ranking_data.append([0, "---"])
        
        self.day_ranking_box.add_widget(self.day_ranking_grid)

        layout.add_widget(self.day_ranking_box)
        
        self.add_widget(layout)
    
    def start_game(self, instance):
        """Closes menu and starts/restarts the game"""
        self.dismiss()
        self.game_screen.start_new_game()
    
    def show_ranking(self, instance):
        self.ranking_view.open()
    
    def update_title(self, text):
        """Updates the title label text (e.g., for win message)"""
        self.title_label.text = text

    def update_score(self, new_score, name):
        for index, row in enumerate((self.rows_ranking_label)):
            print(f"Comparando score con {self.rows_ranking_data[index][0]}")

            if self.rows_ranking_data[index][0] < new_score:
                self.rows_ranking_data.append([new_score, name])
                self.rows_ranking_data.sort(key=lambda column: column[0], reverse=True)
                self.rows_ranking_data = self.rows_ranking_data[:5]
                
                #Update score graphics
                for index, row in enumerate(self.rows_ranking_label):
                    row[0].text = f"{index+1}. {self.rows_ranking_data[index][0]}"
                    row[1].text = f"{self.rows_ranking_data[index][1]}"

                self.ranking_view.update_score(int(new_score), "LABAP")
                
                break


class GameScreen(FloatLayout):
    """Main game screen containing all game logic and visuals"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # File paths
        self.script_path = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(self.script_path, "assets")
        self.sounds_path = os.path.join(self.script_path, "sounds")
        self.fonts_path = os.path.join(self.script_path, "fonts")
        self.config_path = os.path.join(self.script_path, "config")


        # Game state
        self.game_active = True
        self.bg_music = None
        self.timer = 0
        
        # Initialize menu
        self.menu = MenuModalView(game_screen=self)
        
        # Background music
        bg_path = os.path.join(self.sounds_path, 'background.mp3')
        self.bg_music = SoundLoader.load(bg_path)
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.volume = 0.4
            self.bg_music.play()
        else:
            print("Background music couldn't be loaded")

        # Create menu button (always visible, top-left corner)
        self.menu_button = Button(
            text='MENU',
            size_hint=(None, None),
            size=(100, 50),
            pos_hint={'x': 0.01, 'top': 0.99},
            background_color=(0.8, 0.2, 0.2, 0.8)
        )
        self.menu_button.bind(on_press=self.open_menu)
        
        # Startup
        self.setup_game()
        Clock.unschedule(self.update_timer)
        Clock.schedule_once(lambda dt: self.menu.open(), 0.1)
    
    def start_new_game(self):
        """Initializes a new game session"""
        print("Starting new game...")
        
        # Clear previous game if exists
        self.clear_widgets()
        
        # Stop background music if playing
        #if self.bg_music:
            #self.bg_music.stop()
        
        # Setup new game
        
        self.setup_game()
        Clock.schedule_interval(self.update_timer, 1.0)
        self.game_active = True
    
    def setup_game(self):
        """Sets up all game elements"""
        
        # Score setup
        self.game_score = 0

        # Game data dictionaries
        self.teeth_logic_list = {}
        self.filth_visuals = {}
        self.foam_visuals = {}
        self.sparkle_visuals = {}

        # Load JSON configuration
        json_path = os.path.join(self.config_path, 'teethconfig.json') 
        with open(json_path, 'r') as f:
            teethConfig = json.load(f)

        # Select random teeth to clean
        teeth_id_list = list(teethConfig.keys())
        num_of_teeths_to_clean = 10
        teeths_to_clean = random.sample(teeth_id_list, num_of_teeths_to_clean)


        # Clean sound
        clean_sound_path = os.path.join(self.sounds_path, 'clean.mp3')
        self.clean_sound = SoundLoader.load(clean_sound_path)

        # Background image
        self.add_widget(Image(
            source=os.path.join(self.assets_path, 'Fondo.png'),
            allow_stretch=True,
            keep_ratio=False
        ))

        # Brush visualizer
        self.visualizador_cepillo = TuioCursorImage()
        
        # Create teeth
        for tooth_id in sorted(teethConfig.keys()):
            config = teethConfig[tooth_id]
            
            print(f"Loading tooth {tooth_id}...")
            
            is_clean = tooth_id not in teeths_to_clean
            
            # Get data from JSON
            normalized_coords = config['coords']
            center_x = sum(p[0] for p in normalized_coords) / len(normalized_coords)
            center_y = sum(p[1] for p in normalized_coords) / len(normalized_coords)
            
            # Manage dirty teeth
            if not is_clean:
                # Filth visual layer
                filth_layer_path = os.path.join(self.assets_path, config['filth_layer_path'])
                filth_layer = Image(
                    source=filth_layer_path, 
                    allow_stretch=True, 
                    keep_ratio=False
                )
                self.filth_visuals[tooth_id] = filth_layer
                self.add_widget(filth_layer)

                # Foam visual
                foam_visual = Image(
                    source=os.path.join(self.assets_path, 'espuma.gif'),
                    pos_hint={'center_x': center_x, 'center_y': center_y},
                    size_hint=(0.2, 0.2), 
                    keep_ratio=False,
                    anim_delay=-1,
                    opacity=0
                )
                self.foam_visuals[tooth_id] = foam_visual
                self.add_widget(foam_visual)

                # Layer cleaned animation
                clean_gif = Image(
                    source=os.path.join(self.assets_path, 'layercleaned.gif'),
                    size_hint=(0.3, 0.3), 
                    keep_ratio=False,
                    anim_delay=-1,
                    opacity=0,
                    pos_hint={'center_x': center_x, 'center_y': center_y},
                )
                self.sparkle_visuals[tooth_id] = clean_gif
                self.add_widget(clean_gif)

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
            self.add_widget(tooth_logic)

        # Skin overlay
        self.add_widget(Image(
            source=os.path.join(self.assets_path, 'Piel (caraserhumano).png'),
            allow_stretch=True,
            keep_ratio=False
        ))


        #Resets timer state
        Clock.unschedule(self.update_timer) 
        self.timer = 180
        
        # Timer
        self.timeLabel = Label(
            text=f"{self.timer// 60:02d}:{self.timer % 60:02d}",
            font_name = "fun_font",
            size_hint=(1, 0.1),
            pos_hint={'right': 1, 'top': 1},
            color=(1, 1, 1, 1), 
            font_size='20sp'
        )

        # Add brush visualizer
        self.add_widget(self.visualizador_cepillo)
        
        # Add menu button on top
        self.add_widget(self.menu_button)

        self.add_widget(self.timeLabel)

        
        
    def update_timer(self, dt):
        self.timer -= 1

        if (self.timer <= 0):
            self.timeLabel.text = "TIEMPO"
            self.game_active = False
            self.open_menu(None)

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
        
        # Update menu title for victory
        self.menu.update_title("Congratulations! All teeth are clean!")


        
        # Show menu after short delay
        Clock.schedule_once(lambda dt: self.menu.open(), 1.0)

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
    
    def open_menu(self, instance):
        """Opens the menu modal (pauses game)"""
        if self.game_active:
            # Pause game logic here if needed
            if self.bg_music:
                self.bg_music.volume = 0.2  # Lower volume when menu is open
    
        for tooth in self.teeth_logic_list.values():
            if not tooth.brush_visualizer.cursors:
                print(f"Active brush was found in tooth {tooth}, removing")
                tooth.brush_visualizer.remove_brush(tooth.cursor_inside)
            
            tooth_id = tooth.tooth_id
            if tooth_id in self.foam_visuals and self.foam_visuals[tooth_id].opacity == 1:
                print(f"Foam playing was found at tooth {tooth}, stopping")
                self.foam_visuals[tooth_id].opacity = 0
                self.foam_visuals[tooth_id].anim_delay = -1 

        self.game_score = int(round(self.game_score))
        
        self.menu.update_score(self.game_score, "LABAP")
        Clock.unschedule(self.update_timer)
        self.menu.open()


class TeethDemoApp(App):
    """Main application class"""
    def __init__(self, **kwargs):
       
        script_path = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_path, "fonts/mainfont.ttf")

        
        LabelBase.register(
            name="fun_font", 
            fn_regular=font_path
        )
        super().__init__(**kwargs)
    
    def build(self):
        return GameScreen()

if __name__ == '__main__':
    TeethDemoApp().run()
