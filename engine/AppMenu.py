# menu_screen.py
from engine.core.commons import *
from cepilloParty.game_main import CepilloParty

class AppMenu(Screen):
    def __init__(self, **kwargs):
        
        self.name = 'menu'
        super().__init__(**kwargs)

    def play_teeth(self, instance=None):
        app = App.get_running_app()
        app.start_game('cepillo_party') # type: ignore
    
    def play_intestine(self, instance=None):
        app = App.get_running_app()
        app.start_game('intestine') # type: ignore