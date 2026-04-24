import sys
import os
from engine.core.commons import *
from engine.AppMenu import AppMenu
from cepilloParty.game_main import CepilloParty
from engine.core.AssetManager import AssetManager

# Add project root to Python path (enables imports from anywhere)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MainApp(App):
    assets = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # - STATE -
        self.current_game = None
        self.scores = {}
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
        
        if game_name == 'cepillo_party':
            self._start_cepillo_party()
        else:
            print(f"[MainApp] Unknown game: {game_name}")

    def end_game(self, scores):
        print(f"[MainApp] Game ended. Score: {scores}")
        self.scores[self.current_game] = scores
        self.current_game = None
            
        self.sm.current = 'menu' # type: ignore

    def _start_cepillo_party(self):
        print(f"[MainApp] Starting Cepillo Party...")
        self.current_game = 'cepillo_party' 

        # Load assets for the game
        self.assets = AssetManager(self.current_game) 
        
        Builder.load_file('assets/cepillo_party/kv_lang/hud.kv')
        Builder.load_file('assets/cepillo_party/kv_lang/game.kv')

        self.sm.add_widget(CepilloParty(assets=self.assets)) # type: ignore
            
        self.sm.current = self.current_game #type: ignore

if __name__ == '__main__':
    # Keep the __main__ block incredibly clean. 
    # Just instantiate and run.
    MainApp().run()