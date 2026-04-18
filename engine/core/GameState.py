from .commons import *

class GameState():
    def __init__(self):
        
        self.current_game = None
        self.score = 0
        
        self.sm = ScreenManager() # Screen Manager
        self.cepillo_party_instance = None
        self.instentine_instance = None

        self.fonts = {}
        
        for font_file in os.listdir(FONTS_PATH):
            if font_file.endswith('.ttf'):
                font_name = os.path.splitext(font_file)[0]
                font_path = os.path.join(FONTS_PATH, font_file)
                LabelBase.register(name=font_name, fn_regular=font_path)
                self.fonts[font_name] = font_path

    
game = GameState()