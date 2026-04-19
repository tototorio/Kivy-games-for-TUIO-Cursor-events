from .commons import *

class AppState(EventDispatcher):
    def __init__(self):
        
        self.current_game = None
        self.score = 0
        self.sm = ScreenManager() # Screen Manager
        
        self.register_event_type('on_game_requested')
        self.register_event_type('on_game_ended')
        self.register_event_type('on_return_to_menu')
    
    # Event handlers with actual logic (no binding needed!)
    def on_game_requested(self, game_name):
        """Handle game start request"""
        print(f"[GameState] Game requested: {game_name}")
        self.current_game = game_name
        self.score = 0
        
        screen = self.sm.get_screen(game_name)
        if hasattr(screen, '_on_game_start'):
            screen._on_game_start()
        
        self.sm.current = game_name
    
    def on_game_ended(self, game_name, score):
        """Handle game end"""
        print(f"[GameState] Game ended: {game_name} | Score: {score}")
        self.score = score
        self.current_game = None
        
        screen = self.sm.get_screen(game_name)
        if hasattr(screen, '_on_game_end'):
            screen._on_game_end()
        
        self.sm.current = 'menu'
    
    def on_return_to_menu(self):
        """Handle return to menu"""
        print("[GameState] Returning to menu")
        self.current_game = None
        
        if self.sm.current:
            screen = self.sm.get_screen(self.sm.current)
            if hasattr(screen, '_on_game_end'):
                screen._on_game_end()
        
        self.sm.current = 'menu'


app = AppState()