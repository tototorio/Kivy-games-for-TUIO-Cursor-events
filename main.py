import sys
import os

# Add project root to Python path (enables imports from anywhere)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.core.commons import *

from engine.AppMenu import AppMenu
from cepilloParty.game_main import CepilloParty
from engine.core.AssetManager import AssetManager



class MainApp(App):
    assets = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # - STATE -
        self.current_game = None
        self.score = 0
        self.sm = None

    def build(self):
        # Load Kivy lang instructions
        Builder.load_file('assets/cepillo_party/kv_lang/app_menu.kv')
        

        # Initialize screen manager and add screens
        self.sm = ScreenManager()
        
        # Add screens to manager
        self.sm.add_widget(AppMenu(name='menu'))
        self.sm.current = 'menu'
        return self.sm

    # --- LOGIC ---
    def start_game(self, game_name):
        print(f"[MainApp] Starting game: {game_name}")
        self.current_game = game_name
        self.score = 0

        # Load assets for the game
        self.assets = AssetManager(game_name) 
        
        Builder.load_file('assets/cepillo_party/kv_lang/hud.kv')
        Builder.load_file('assets/cepillo_party/kv_lang/game.kv')

        self.sm.add_widget(CepilloParty()) # type: ignore
            
        self.sm.current = game_name #type: ignore

    def end_game(self, score):
        print(f"[MainApp] Game ended. Score: {score}")
        self.score = score
        self.current_game = None
            
        self.sm.current = 'menu' # type: ignore



if __name__ == '__main__':
    # Keep the __main__ block incredibly clean. 
    # Just instantiate and run.
    MainApp().run()