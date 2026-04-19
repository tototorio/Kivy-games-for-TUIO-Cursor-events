#:kivy
from engine.core.commons import *
from engine.core.AppState import AppState
from engine.core.AssetManager import AssetManager
#from cepilloParty.managers.inputManager import InputManager



class CepilloParty(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Game main variables
        self.name = 'cepillo_party'
        self.asset_m: AssetManager

        # Initialize variables ONLY (no widgets!)
        self.layout = None
        self.game_active = False
        self.bg_music = None
        self.timer = 0
        self.menu_button = None
        self.timeLabel = None

    def on_enter(self):
        """Called when screen becomes active"""
        # NOW create and add widgets
        if self.layout is None:
            self.layout = FloatLayout()
            self.add_widget(self.layout)
        
        
        
        # Initialize Asset Manager and load assets
        self.asset_m = AssetManager(self.name)
        self._setup_game()

    def _open_menu(self, instance):
        """Pauses the game and opens the menu overlay"""
        self.game_active = False
        self.bg_music.stop() if self.bg_music else None
        # Startup - assets loaded here, setup_game() called when game starts

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

        # Clear layout and add menu button
        self.layout.clear_widgets() # type: ignore
        self._setup_visuals()
    
        # Schedule game update loop
        try: 
            Clock.unschedule(self._update_screen_timer) # Ensure no duplicate schedules
        except Exception as e:
            print(f"Error unscheduling timer: {e}")

        self._start_game()

    def _setup_visuals(self):
        # The layout and widgets are already created from the KV file

        self.layout = self.ids.game_layout  # Reference KV widgets
        self.timeLabel = self.ids.time_label
        self.menu_button = self.ids.menu_button
        self.menu_button.bind(on_press=self._open_menu)
    
    def _start_game(self):
        # Start background music
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.play()
    
    def _update_screen_timer(self, dt):
        self.timer -= 1

        if (self.timer <= 0):
            self.timeLabel.text = "TIEMPO" # type: ignore
            self.game_active = False
            # ADD HERE ENDING SEQUENCE
            AppState.get_app().sm.current = 'menu'

            return False # Stops the clock schedule
        
        mins, secs = divmod(self.timer, 60)
        self.timeLabel.text = f"{mins:02d}:{secs:02d}" # type: ignore
    
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
    
class Menu(ModalView):
    """
    Main menu overlay that pauses the game.
    Appears at app start, after game completion, or when menu button is pressed.
    """
    def __init__(self, game: CepilloParty, **kwargs):
        

        self.game_screen = game
        self.ranking_view = Ranking(self)
        
        # Set textures as properties (accessed in KV via root.*)
        self.bg_texture = game.asset_m.get_asset("menu_bg", "image").texture
        self.play_button_texture = game.asset_m.get_asset("play_button", "image").texture
        self.ranking_button_texture = game.asset_m.get_asset("ranking_button", "image").texture
        
        self.rows_ranking_label = []
        self.rows_ranking_data = []
        super().__init__(**kwargs)

    # After the KV is loaded, populate the grid programmatically
    def on_kv_post(self, base_widget):
        """Called after KV layout is created"""
        grid = self.ids.day_ranking_grid
        
        for row in range(5):
            # Create score label
            label_score = ScoreLabel(text=f"{row+1}. 0")
            
            # Create name label
            label_name = NameLabel(text="---")
            
            grid.add_widget(label_score)
            grid.add_widget(label_name)
            
            # Store references for later updates
            self.rows_ranking_label.append([label_score, label_name])
            self.rows_ranking_data.append([0, "---"])
    
    def _start_game(self, instance):
        """Closes menu and starts/restarts the game"""
        self.dismiss()
        self.game_screen._start_game()
    
    def _show_ranking(self, instance):
        self.ranking_view.open()
    
    def update_title(self, text):
        """Updates the title label text (e.g., for win message)"""
        self.title_label.text = text # type: ignore

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


class Ranking(ModalView):

    def __init__(self, menu: Menu, **kwargs):
    
        self.menu = menu
        game = menu.game_screen
        
        # Store game reference for KV access
        self.game = game
        
        # Load JSON configuration
        self.json_path = game.asset_m.get_asset("ranking", "config")
        with open(self.json_path, 'r') as f:
            self.ranking = json.load(f)
        
        self.highscores_label = []
        self.highscores = []

        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        """Called after KV layout is created - populate the grid"""
        # Set background texture from KV
        self.ids.ranking_bg.texture = self.game.asset_m.get_asset("ranking_bg", "image").texture
        
        # Get grid reference
        grid = self.ids.highscores_grid
        
        # Populate grid from JSON data
        for index, score_data in enumerate(self.ranking):
            score = score_data.get('score', 0)
            score_text = f"{index+1}.   {score}"
            name_text = score_data.get('name', '---')
            
            # Create labels using custom classes
            label_score = HighScoreLabel(text=score_text)
            label_name = HighNameLabel(text=name_text)
            
            grid.add_widget(label_score)
            grid.add_widget(label_name)
            
            self.highscores_label.append([label_score, label_name])
            self.highscores.append([score, name_text])

    def update_score(self, new_score, name):
        with open(self.json_path, 'r') as f:
            self.ranking = json.load(f)
        
        for index, score_data in enumerate(self.ranking):
            player_score = int(score_data.get('score', 0))

            if new_score >= player_score:
                self.ranking.append({"score": new_score, "name": name})
                self.ranking.sort(
                    key=lambda item: int(item.get("score", 0)),
                    reverse=True
                )
                self.ranking = self.ranking[:10]

                with open(self.json_path, 'w') as f:
                    json.dump(self.ranking, f, indent=4)
                    print(f"Ranking actualizado. {name} añadió {new_score} puntos.")

                # Update graphics
                self.highscores.append([new_score, name])
                self.highscores.sort(key=lambda column: column[0], reverse=True)
                self.highscores = self.highscores[:10]
                
                for index, row in enumerate(self.highscores_label):
                    row[0].text = f"{index+1}. {self.highscores[index][0]}"
                    row[1].text = f"{self.highscores[index][1]}"
                break

    def close(self):
        self.dismiss()

class ScoreLabel(Label):
    pass

class NameLabel(Label):
    pass

class HighScoreLabel(Label):
    pass

class HighNameLabel(Label):
    pass