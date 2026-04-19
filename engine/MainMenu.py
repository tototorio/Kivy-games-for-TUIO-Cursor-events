# menu_screen.py
from engine.core.commons import *
from engine.core.AppState import app
from cepilloParty.game_main import CepilloParty

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        
        
        self.name = 'menu'
        
        super().__init__(**kwargs)
        
        # Main container
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # ============================================================
        # HEADER / TITLE SECTION
        # ============================================================
        title_layout = BoxLayout(size_hint_y=0.25, padding=10)
        
        title = Label(
            text='Piso Interactivo',
            font_size='50sp',
            bold=True,
            color=(0.2, 0.6, 1, 1)  # Nice blue
        )
        title_layout.add_widget(title)
        main_layout.add_widget(title_layout)
        
        # ============================================================
        # BUTTONS SECTION (Grid for nice alignment)
        # ============================================================
        buttons_layout = GridLayout(
            cols=1,
            spacing=30,
            size_hint_y=0.6,
            padding=50
        )
        
        # Button 1: Teeth Game
        btn_teeth = Button(
            text='CEPILLO PARTY',
            size_hint_y=None,
            height=100,
            background_color=(0.3, 0.7, 0.3, 1),  # Green
            font_size='28sp'
        )
        btn_teeth.bind(on_press=self.play_teeth) # type: ignore
        buttons_layout.add_widget(btn_teeth)
        
        # Button 2: Intestine Game
        btn_intestine = Button(
            text='GLOBULOS AL RESCATE',
            size_hint_y=None,
            height=100,
            background_color=(0.7, 0.3, 0.3, 1),  # Red
            font_size='28sp'
        )
        btn_intestine.bind(on_press=self.play_intestine) # type: ignore
        buttons_layout.add_widget(btn_intestine)
        
        main_layout.add_widget(buttons_layout)
        
        # ============================================================
        # FOOTER SECTION
        # ============================================================
        footer_layout = BoxLayout(size_hint_y=0.15)
        
        footer_text = Label(
            text='Select a game to start',
            font_size='16sp',
            color=(0.7, 0.7, 0.7, 1),
            italic=True
        )
        footer_layout.add_widget(footer_text)
        main_layout.add_widget(footer_layout)
        
        # Add main layout to screen
        self.add_widget(main_layout)

        
    
    def play_teeth(self, instance):
        app.dispatch('on_game_requested', 'cepillo_party')
        print("[MenuScreen] Starting Cepillo Party Game")
    
    def play_intestine(self, instance):
        """Switch to intestine game
        game.active_game = 'intestine'
        self.manager.current = 'intestine_game'
        game.instentine_instance = self.manager.get_screen('intestine_game')
        game.instentine_instance.setup_game() 
        print("[MenuScreen] Starting Intestine Game")
        """