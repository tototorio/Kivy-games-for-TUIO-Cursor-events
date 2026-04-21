import os
import sys
import json
import random
import re
from enum import Enum
from kivy.config import Config
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
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
from kivy.event import EventDispatcher


Config.set('input', 'tuio_listener', 'tuio,127.0.0.1:3333')

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
    def __init__(self, normalized_coords, use_grace: bool, **kwargs):
        
        
        
        # Configuration
        self.coords = normalized_coords
        self.debug = True
        self.use_grace = use_grace
        
        # Grace system (extracted to manager)
        self.grace = GracePeriodManager(duration=0.3)
        
        # State
        self.cursor_inside = None
        
        # Callbacks
        self.on_touch_down_callback = None
        self.on_touch_move_callback = None
        self.on_touch_up_callback = None
        self.on_reset_callback = None

        super().__init__(**kwargs)

        
    def _normalized_to_pixels(self, x_norm, y_norm):
        """Converts normalized coordinates (0.0-1.0) to pixels"""
        return (x_norm * Window.width, y_norm * Window.height)

    def _get_polygon_vertices_pixel_coords(self):
        """Gets polygon vertices in pixel coordinates"""
        return [self._normalized_to_pixels(x, y) for x, y in self.coords]

    def _point_inside_polygon(self, x, y):
        """
        Determines if a point (x, y) is inside the polygon using Ray Casting.
        
        Algorithm:
        - Casts a horizontal ray to the right from the point
        - Counts how many times it intersects with polygon edges
        - If number of intersections is odd → point INSIDE
        - If number is even → point OUTSIDE
        """
        polygon = self._get_polygon_vertices_pixel_coords()
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
        
        # Ignore if not inside
        if not self._point_inside_polygon(touch.x, touch.y):
            return
        
        # If new cursor, check for grace period
        if self.cursor_inside != None and self.cursor_inside != touch.uid:
            if self.use_grace and self.grace.is_active():
                return
            
        # Cancel grace if re-entering during grace period
        if self.grace.is_active():
            self.grace.cancel()
            if self.debug:
                print(f"[DEBUG] Cursor {touch.uid} re-entered, grace canceled")
        
        was_empty = self.cursor_inside is None
        self.cursor_inside = touch.uid
        
        if self.debug and was_empty:
            print(f"[DEBUG] Cursor {touch.uid} registered (first touch)")
        
        if self.on_touch_down_callback:
            try:
                self.on_touch_down_callback(touch)
            except Exception as e:
                print(f"[ERROR] on_touch_down_callback failed: {e}")
        
        return
    
    def on_touch_move(self, touch):
        """Called when a TUIO cursor MOVES"""
        
        # If there is a cursor insode and it's not the same one, check grace
        if self.cursor_inside != None and self.cursor_inside != touch.uid:
            if self.use_grace and self.grace.is_active():
                return
        
        # Check if cursor is inside polygon
        if not self._point_inside_polygon(touch.x, touch.y):
            if self.cursor_inside == touch.uid:
                # Cursor just left the polygon
                self.cursor_inside = None
                
                if self.use_grace:
                    self.grace.start(on_expire_callback=self._on_grace_expire)

                    if self.debug:
                        print(f"[DEBUG] Cursor {touch.uid} left polygon, grace period starting")
                
                if self.on_touch_up_callback:
                    try:
                        self.on_touch_up_callback(touch)
                    except Exception as e:
                        print(f"[ERROR] on_touch_up_callback failed: {e}")
            
            return
        
        self.cursor_inside = touch.uid
        
        if self.on_touch_move_callback:
            try:
                self.on_touch_move_callback(touch)
            except Exception as e:
                print(f"[ERROR] on_touch_move_callback failed: {e}")
        
        return
    
    def on_touch_up(self, touch):
        """Called when a cursor LEAVES the screen"""
        
        if touch.uid != self.cursor_inside:
            return
        
        if self.debug:
            print(f"[DEBUG] Cursor {touch.uid} left screen")
        
        # Handle cursor leaving screen
        if self.use_grace:
            # Start grace period, reset when it expires
            self.grace.start(on_expire_callback=self._on_grace_expire)
        else:
            # Grace disabled, reset immediately
            self._on_grace_expire()
        
        if self.on_touch_up_callback:
            try:
                self.on_touch_up_callback(touch)
            except Exception as e:
                print(f"[ERROR] on_touch_up_callback failed: {e}")
        
        return
    
    def _on_grace_expire(self):
        """Called when grace period expires or is skipped"""
        if self.debug:
            print(f"[DEBUG] Grace period expired, resetting")
        
        self.cursor_inside = None
        
        if self.on_reset_callback:
            try:
                self.on_reset_callback()
            except Exception as e:
                print(f"[ERROR] on_reset_callback failed: {e}")