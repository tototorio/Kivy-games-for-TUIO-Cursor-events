import sys
import os
from engine.core.commons import *
from engine.AppMenu import AppMenu
from cepilloParty.game_main import CepilloParty
from juegoComida.game_main import JuegoComida
from engine.core.AssetManager import AssetManager

# Add project root to Python path (enables imports from anywhere)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MainApp(App):
    assets = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_game = None
        self.scores = {}
        self._loaded_kv = set()  # track loaded files

    def build(self):
        # Load ALL KV files once at startup, not per game
        Builder.load_file('assets/cepillo_party/kv_lang/app_menu.kv')

        self.sm = ScreenManager()
        self.sm.add_widget(AppMenu(name='menu'))
        self.sm.current = 'menu'
        return self.sm

    def _load_kv(self, path):
        if path not in self._loaded_kv:
            Builder.load_file(path)
            self._loaded_kv.add(path)

    def start_cepillo_party(self):
        self.current_game = 'cepillo_party'
        self.assets = AssetManager(self.current_game)
        self._load_kv('assets/cepillo_party/kv_lang/hud.kv')
        self._load_kv('assets/cepillo_party/kv_lang/game.kv')
        self.sm.add_widget(CepilloParty(name='cepillo_party', assets=self.assets))
        self.sm.current = 'cepillo_party'
    
    def start_juego_comida(self):
        self.current_game = 'juego_comida'
        self.assets = AssetManager(self.current_game)
        
        self.sm.add_widget(JuegoComida(name='juego_comida', assets=self.assets))
        self.sm.current = 'juego_comida'

    def end_game(self, scores):
        self.scores[self.current_game] = scores
        old_game = self.current_game
        self.current_game = None
        self.sm.current = 'menu'                        # triggers on_leave
        self.sm.remove_widget(self.sm.get_screen(old_game))  # then destroy

if __name__ == '__main__':
    # Keep the __main__ block incredibly clean. 
    # Just instantiate and run.
    MainApp().run()