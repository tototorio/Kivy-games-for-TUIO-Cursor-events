import sys
import os

# Add project root to Python path (enables imports from anywhere)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.core.commons import *
from engine.core.AppState import app

from engine.MainMenu import MenuScreen
from cepilloParty.game_main import CepilloParty

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class MainApp(App):
        def build(self):
            # Load KV lang instructions
            Builder.load_file('assets/cepillo_party/kv_lang/hud.kv')
            Builder.load_file('assets/cepillo_party/kv_lang/game.kv')
            

            return app.sm

if __name__ == '__main__':
    
    # Add screens to the screen manager
    app.sm.add_widget(MenuScreen())
    app.sm.add_widget(CepilloParty())
    
    # Initialize the game state and screen manager
    app.sm.current = 'menu'  # Start with the menu screen
    
    
    # Start the app 
    MainApp().run()