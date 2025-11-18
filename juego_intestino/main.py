import os
import json
import random
from kivy.config import Config

Config.set('graphics', 'fullscreen', 'auto')
Config.set('input', 'tuio_listener', 'tuio,127.0.0.1:3333')

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout

from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock



class Menu(ModalView):
    def __init__(self, game_screen, **kwargs):
        #Initial setup
        super().__init__(**kwargs)
        app = App.get_running_app()
        self.game_screen = game_screen
        
        #Menu config
        self.size_hint = (1, 1)
        self.auto_dismiss = False  # Prevent closing by clicking outside
        self.background_color = (0, 0, 0, 0.85)  # Semi-transparent dark
        self.background_color = (0, 0, 0, 0.85)  # Semi-transparent dark background background
        self.background = os.path.join(app.assets_path, "menubackground.png")
        #Visual setup
        layout = FloatLayout()
        title_label = Label(
            text="JUEGO INTESTINO",
            font_size='40sp',
            size_hint=(1, 0.3),
            pos_hint={'center_x': 0.5, 'center_y': 0.9},
            color=(1, 1, 1, 1)
        )
        layout.add_widget(title_label)

        play_button = Button(
            size_hint=(0.4, 0.5),
            pos_hint={'center_x': 0.5, 'center_y': 0.4},
            background_normal = os.path.join(app.assets_path, "start_icon.png"),
        )
        play_button.bind(on_press=self.start_game)
        layout.add_widget(play_button)
        self.add_widget(layout)


    def start_game (self):
        self.dismiss()
        self.game_screen.reset_game()


class GameScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()

        self.menu = Menu(game_screen=self)
        self.bad_cell_texture = CoreImage(os.path.join(app.assets_path, "bad_cell.png"), keep_data=False).texture
        self.good_cell_texture = CoreImage(os.path.join(app.assets_path, "good_cell.png"), keep_data=False).texture

        #Game background
        self.add_widget(Image(
            source=os.path.join(app.assets_path, 'gamebackground.png'),
            allow_stretch=True,
            keep_ratio=False
        ))

        Clock.schedule_interval(self.update_game, 1.0 / 60.0)
        Clock.schedule_interval(self.create_cell, 0.5)

        self.gameSpace = RelativeLayout(
            size_hint=(1, 0.663299664), 
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        with self.gameSpace.canvas.before:
             Color(0, 1, 0, 0.3) # Verde transparente

        self.add_widget(self.gameSpace)

    def update_game(self, dt):
        cells_to_delete = []
        
        for child in self.gameSpace.children:
            if isinstance(child, BloodCell):
                child.move()

                if (not child.is_alive):
                    cells_to_delete.append(child)
        
        for cell in cells_to_delete:
            self.gameSpace.remove_widget(cell)

    def create_cell(self, dt):
        delta = random.uniform(0, 1)

        if (delta < 0.85):
            self.gameSpace.add_widget(BloodCell(self.good_cell_texture, 'good'))
        else:
            self.gameSpace.add_widget(BloodCell(self.bad_cell_texture, 'bad'))

class BloodCell(Widget):
    def __init__(self, texture, type, **kwargs):
        super().__init__(**kwargs)
        #app = App.get_running_app()

        self.is_alive = True
        
        match type:
            case "good":
                self.type = 0
            case "bad":
                self.type = 1

        size_factor = random.uniform(0.05, 0.08)
        self.size_hint = (size_factor, size_factor*2.5)

        self.speed_x_factor = random.uniform(0.0015, 0.003)
        self.speed_y_factor = random.uniform(0.008, 0.01) 
        
        self.speed_x = 0
        self.speed_y = 0

        #Initial position definition
        x_side = random.choice(['left', 'right'])
        y_spawn = random.uniform(0.2, 0.8)
        if (x_side == 'left'):
            self.pos_hint = {'right': 0, 'y': y_spawn}
        else:
            self.pos_hint = {'x': 0.99, 'y': y_spawn}
            self.speed_x_factor  *= -1

        with self.canvas:

            Color(1, 1, 1, 1)
            self.rect = Rectangle(texture=texture, pos=self.pos, size=self.size)
        
        self.bind(pos=self.update_rect)
        self.bind(size=self.update_rect)

        #Allows the cell to move
        Clock.schedule_once(self.free_anchor, 0)

    def free_anchor(self, dt):
        self.pos_hint = {}
        
        self.speed_x = self.parent.width*self.speed_x_factor 
        self.speed_y = self.parent.height*self.speed_y_factor 

    def move(self):

        self.x += self.speed_x
        self.y += self.speed_y

        if self.right < 0 or self.x > self.parent.width:
            self.is_alive = False
        
        if self.y < 0 or self.top > self.parent.height:
            self.speed_y *= -1

    def on_touch_down(self, touch):
        if self.type == 1:
            if self.collide_point(*touch.pos):
                self.is_alive = False

        return super().on_touch_down(touch)
        
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    
    



class IntestineGame(App):       

    def build(self):
        self.script_path = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(self.script_path, "assets")
        self.sounds_path = os.path.join(self.script_path, "sounds")
        self.fonts_path = os.path.join(self.script_path, "fonts")
        self.config_path = os.path.join(self.script_path, "config")
        return GameScreen()


if __name__ == '__main__':
    IntestineGame().run()