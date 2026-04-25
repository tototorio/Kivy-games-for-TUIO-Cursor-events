import os
import sys
import json
import random
import re
from typing import Callable, Optional
from enum import Enum

from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
Config.set('input', 'tuio_listener', 'tuio,127.0.0.1:3333')

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.modalview import ModalView
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.image import Image as CoreImage
from kivy.cache import Cache
from kivy.atlas import Atlas
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.event import EventDispatcher



BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
ASSETS_PATH = os.path.join(BASE_PATH, "assets")
IMAGES_PATH = os.path.join(ASSETS_PATH, "images")
GIF_PATH = os.path.join(ASSETS_PATH, "gifs")
SOUNDS_PATH = os.path.join(ASSETS_PATH, "sounds")
FONTS_PATH = os.path.join(ASSETS_PATH, "fonts")
KV_LANG_PATH = os.path.join(ASSETS_PATH, "kv_lang")
CONFIG_PATH = os.path.join(BASE_PATH, "config")

# Common classes

class GracePeriodManager:
    """Manages grace period logic independently"""
    
    def __init__(self, duration=0.3):
        self.duration = duration
        self.pending_reset = None
    
    def is_active(self) -> bool:
        """Check if grace period is currently active"""
        return self.pending_reset is not None
    
    def start(self, on_expire_callback=None) -> None:
        """Start grace period. Calls callback when it expires."""
        
        if self.pending_reset:
            self.cancel()  # Cancel any existing grace
        
        self.pending_reset = Clock.schedule_once(
            lambda dt: self._on_expire(on_expire_callback),
            self.duration
        )
    
    def cancel(self) -> None:
        """Cancel active grace period"""
        if self.pending_reset:
            Clock.unschedule(self.pending_reset)
            self.pending_reset = None
    
    def _on_expire(self, callback):
        """Called when grace period expires"""
        self.pending_reset = None
        if callback:
            callback()

class TUIOButton(Widget):
    def __init__(self, normalized_coords, use_grace: bool, is_button_active: bool, **kwargs):
        
        # Configuration
        self.debug = True
        self.active = is_button_active
        self.norm_coords = normalized_coords

        # Grace system (extracted to manager)
        if use_grace:
            self.grace = GracePeriodManager(duration=0.3)
        else:
            self.grace = None
        
        # State
        self.owner_uid = None
        
        # Event dispatchers
        self.register_event_type('on_cursor_enter') #type: ignore
        self.register_event_type('on_cursor_move') #type: ignore
        self.register_event_type('on_cursor_leave') #type: ignore
        super().__init__(**kwargs)

        # Coordinates calculated after super
        self._pixel_coods = normalized_to_pixel_coords(self.norm_coords)

    # Since resolution won't change during gameplay, we can calculate polygon vertices in pixel coordinates once.
    #def _get_polygon_vertices_pixel_coords(self):
    #    """Gets polygon vertices in pixel coordinates"""
    #    return self._normalized_to_pixel_coords()

    def _is_cursor_inside(self, x, y):
        """
        Determines if a point (x, y) is inside the polygon using Ray Casting.
        
        Algorithm:
        - Casts a horizontal ray to the right from the point
        - Counts how many times it intersects with polygon edges
        - If number of intersections is odd → point INSIDE
        - If number is even → point OUTSIDE
        """
        polygon = self._pixel_coods
        n = len(polygon)
        
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside

    def on_touch_down(self, touch):
        """Handles when a TUIO cursor enters the screen"""
        
        if not self.active:
            return

        # Case: cursor that appeared is outside the button
        if not self._is_cursor_inside(touch.x, touch.y):
            return
        
        # Case: cursor that appeared is inside the button

        # Case: already an owner for this button
        if self.owner_uid is not None:
            # Case: grace being used and active for this button
            if self.grace and self.grace.is_active():
                self.grace.cancel()
                self.owner_uid = touch.uid 
                return
            # Case: grace not active or not used, ignore new touch
            else:
                return
    
        # Case: no owner for this button
        self.owner_uid = touch.uid

        self.dispatch('on_cursor_enter', touch)  # type: ignore
        return
    
    def on_touch_move(self, touch):
        """Called when a TUIO cursor MOVES"""
        
        if not self.active:
            return

        inside = self._is_cursor_inside(touch.x, touch.y)

        # Case: cursor that moved its outside
        if not inside:
            # Case: said cursor is owner of button
            if touch.uid == self.owner_uid:
                # Case: using grace and grace not active for this button yet
                if self.grace and not self.grace.is_active():
                    self.grace.start(on_expire_callback=self._on_grace_expire)
                    return
            #Case: said cursor is not owner of button
            else:
                return
        
        # Case: cursor that moved its inside
        
        # Case: no owner for button
        if self.owner_uid is None:
            self.owner_uid = touch.uid
            self.dispatch('on_cursor_enter', touch)  # type: ignore
            return

        # Case: said cursor is owner of button
        elif self.owner_uid == touch.uid:
            self.dispatch('on_cursor_move', touch)  # type: ignore
            return
        
        # Case: said cursor is not owner of button
        else:
            # Case: using grace and grace active for this button
            if self.grace and self.grace.is_active():
                self.grace.cancel()
                self.owner_uid = touch.uid
            # Case: no grace for this button
            else:
                return
    
    def on_touch_up(self, touch):
        """Called when a cursor LEAVES the screen"""
        
        if not self.active:
            return

        # Case: cursor that left is not owner of button
        if touch.uid != self.owner_uid:
            return
        
        # Case: cursor that left is owner of button

        # Case: using grace for this button
        if self.grace:
            self.grace.start(on_expire_callback=self._on_grace_expire)
            return
        # Case: no grace, reset immediately
        else:    
            self.dispatch('on_cursor_leave', touch)  # type: ignore
            self.owner_uid = None
            return
    
    def _on_grace_expire(self):
        """Called when grace period expires or is skipped"""
        if self.debug:
            print(f"[DEBUG] Grace period expired, resetting")
        
        self.owner_uid = None
        self.dispatch('on_cursor_leave')  # type: ignore

    def on_cursor_enter(self, touch = None):
        pass

    def on_cursor_leave(self, touch = None):
        pass

    def on_cursor_move(self, touch = None):
        pass

class AnimatedSprite(Image):
    def __init__(self, keys: list, frames, duration=1.0, persistent=False, sound=None, game=None, **kwargs):
        super().__init__(**kwargs)

        self.frames = frames
        self.total_duration = duration
        self.persistent = persistent
        self.sfx = sound

        self._elapsed = 0.0
        self._playing = False
        self.opacity = 0 

        if self.frames == None :
            raise ValueError("AnimatedSprite requires a list of frames to function")
        if game == None:
            raise ValueError("AnimatedSprite requires a reference to the game instance for animation management")       
        if keys == None or len(keys) != 2:
            raise ValueError("AnimatedSprite requires 'keys' argument with format [tooth_key, anim_key] for animation management")
        
        self.texture = self.frames[0]

        game.add_widget(self) 

        if keys[0] in game.active_animations:
            game.active_animations[keys[0]][keys[1]] = self 
        else:
            game.active_animations[keys[0]] = {keys[1]: self}

    def play(self):
        """Resume from wherever it stopped"""
        self._playing = True
        self.opacity = 1
        if self.sfx:
            self.sfx.play()

    def stop(self):
        """Freeze on current frame, stay quiet"""
        self._playing = False
        self.opacity = 0
        if self.sfx:
            self.sfx.stop()

    def reset(self):
        """Rewind to frame 0 without affecting play state"""
        self._elapsed = 0.0
        if self.frames:
            self.texture = self.frames[0]

    def step(self, dt) -> bool:
        """
        Advance the animation by dt seconds.
        Returns True if the sprite should stay alive, False if it should be removed.
        """
        if not self._playing:
            return True  # paused but alive

        self._elapsed += dt
        progress = min(self._elapsed / self.total_duration, 1.0)
        idx = min(int(progress * len(self.frames)), len(self.frames) - 1)

        if progress >= 1.0:
            if self.persistent:
                self._elapsed = self._elapsed % self.total_duration  # wrap cleanly
            else:
                return False

        self.texture = self.frames[idx]
        return True
    
# Common functions

def normalized_to_pixel_coords(norm_coords: tuple):
        return tuple(
            (x * Window.width, y * Window.height)
            for x, y in norm_coords
        )
