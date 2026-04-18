import sys
import os

# Add project root to Python path (enables imports from anywhere)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.core.commons import *
from engine.core.GameState import game

from engine.MainMenu import MenuScreen
from engine.CepilloParty import CepilloParty

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class MainApp(App):
        def build(self):
            return game.sm

if __name__ == '__main__':
    
    # Add screens to the screen manager
    game.sm.add_widget(MenuScreen())
    game.sm.add_widget(CepilloParty())
    
    # Initialize the game state and screen manager
    game.sm.current = 'menu'  # Start with the menu screen
    
    
    # Start the app 
    MainApp().run()