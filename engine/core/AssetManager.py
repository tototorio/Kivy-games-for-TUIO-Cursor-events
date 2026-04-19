from .commons import * # Assuming ASSETS_PATH is here

class AssetManager:
    def __init__(self, game_name):
        self.game_name = game_name
        self.assets_path = os.path.join(ASSETS_PATH, game_name)

        # 1. Unified Storage Dictionaries
        self.images = {}
        self.sounds = {}
        self.configs = {}
        self.kv_lang = {}
        self.fonts = {}
        self.atlas = None
        
        # 2. The Configuration Map 
        self._type_map = {
            'image':   {'folder': 'images',  'ext': '.png',   'store': self.images,   'loader': lambda p: CoreImage(p)},
            'sound':   {'folder': 'sounds',  'ext': '.mp3',   'store': self.sounds,   'loader': SoundLoader.load},
            'config':  {'folder': 'config',  'ext': '.json',  'store': self.configs,  'loader': lambda p: p}, # Config just stores the path, we load it on demand
            'kv_lang': {'folder': 'kv_lang',      'ext': '.kv',    'store': self.kv_lang,  'loader': lambda p: p}, # KV just stores the path
            'font':    {'folder': 'fonts',   'ext': '.ttf',   'store': self.fonts,    'loader': lambda p: self._register_font(p)}
        }

        # 3. Load all assets at initialization
        self.load_all_assets('image')
        self.load_all_assets('sound')
        self.load_all_assets('config')
        self.load_all_assets('kv_lang')
        self.load_all_assets('font')
        self._load_atlas()

    def _load_json(self, path):
        """Helper for JSON loading"""
        with open(path, 'r') as f:
            return json.load(f)

    def _get_asset_path(self, asset_type):
        """Build the folder path for a given asset type"""
        if asset_type not in self._type_map:
            raise ValueError(f"Unknown asset type: {asset_type}")
        return os.path.join(self.assets_path, self._type_map[asset_type]['folder'])
    
    def load_all_assets(self, asset_type):
        """Load all assets of a given type from the game asset folder"""
        if asset_type not in self._type_map:
            raise ValueError(f"Unknown asset type: {asset_type}")
            
        path_root = self._get_asset_path(asset_type)
        if not os.path.isdir(path_root):
            raise FileNotFoundError(f"Asset directory not found: {path_root}")
        
        extension = self._type_map[asset_type]['ext']
        
        for item in os.listdir(path_root):
            if item.endswith(extension):
                    key = os.path.splitext(item)[0]
                    self.load_asset(key, asset_type)
    
    def get_asset(self, key, asset_type):
        if asset_type not in self._type_map:
            raise ValueError(f"Unknown asset type: {asset_type}")
        return self._type_map[asset_type]['store'].get(key)
    
    def load_asset(self, key, asset_type):
        if asset_type not in self._type_map:
            raise ValueError(f"Unknown asset type: {asset_type}")
            
        config = self._type_map[asset_type]
        path = os.path.join(self._get_asset_path(asset_type), f"{key}{config['ext']}")
        
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Asset not found: {path}")
        
        # Call the specific loader function defined in the _type_map
        asset = config['loader'](path)
        
        # Store it in the appropriate dictionary
        config['store'][key] = asset
        return asset
    
    def unload_assets(self):
        for image in self.images.values():
            image.release()  # Release texture memory

        for sound in self.sounds.values():
            if sound:
                sound.stop()
                sound.unload()
        
        # Clear all dicts easily by iterating over our map
        for config in self._type_map.values():
            config['store'].clear()
    
    def _register_font(self, path):
        """Helper to register a font with Kivy"""
        font_name = os.path.splitext(os.path.basename(path))[0]
        LabelBase.register(name=font_name, fn_regular=path)
        return path

    def _load_atlas(self):
        """Load the atlas configuration if it exists"""
        atlas_path = os.path.join(self.assets_path, "atlas/animations.atlas")
        if os.path.isfile(atlas_path):
            self.atlas = Atlas(atlas_path)