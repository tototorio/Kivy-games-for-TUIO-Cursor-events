from .commons import * # Assuming ASSETS_PATH is here

class AssetManager:
    def __init__(self, game_name):
        self.game_name = game_name
        self.assets_path = os.path.join(ASSETS_PATH, game_name)

        # 1. Unified Storage Dictionaries
        self.images = {}
        self.atlases = {} 
        self.sounds = {}
        self.configs = {}
        self.kv_lang = {}
        
        # 2. The Configuration Map 
        self._type_map = {
            'image':   {'folder': 'images',  'ext': '.png',   'store': self.images,   'loader': lambda p: Image(source=p)},
            'atlas':   {'folder': 'atlases', 'ext': '.atlas', 'store': self.atlases,  'loader': lambda p: Atlas(p)},
            'sound':   {'folder': 'sounds',  'ext': '.mp3',   'store': self.sounds,   'loader': SoundLoader.load},
            'config':  {'folder': 'config',  'ext': '.json',  'store': self.configs,  'loader': self._load_json},
            'kv_lang': {'folder': 'kv',      'ext': '.kv',    'store': self.kv_lang,  'loader': lambda p: p} # KV just stores the path
        }

        # 3. Load all assets at initialization
        self.load_all_assets('image')
        self.load_all_assets('atlas')
        self.load_all_assets('sound')
        self.load_all_assets('config')
        self.load_all_assets('kv_lang')

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
            if asset_type == 'atlas':
                # 'item' is the folder name (which is also our key)
                item_path = os.path.join(path_root, item)
                if os.path.isdir(item_path):
                    self.load_asset(item, asset_type)
            else:
                # Normal flat file handling
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
        # 1. Handle the nested folder structure for atlases
        if asset_type == 'atlas':
            # Builds: root_path / key / key.atlas
            path = os.path.join(self._get_asset_path(asset_type), key, f"{key}{config['ext']}")
        else:
            # Builds: root_path / key.png
            path = os.path.join(self._get_asset_path(asset_type), f"{key}{config['ext']}")
        
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Asset not found: {path}")
        
        # Call the specific loader function defined in the _type_map
        asset = config['loader'](path)
        
        # Store it in the appropriate dictionary
        config['store'][key] = asset
        return asset
    
    def unload_assets(self):
        for key in self.images:
            Cache.remove('kv.image', key)
            
        # Atlas resources naturally clear when dropped, but clear Cache just in case
        for key in self.atlases:
            Cache.remove('kv.atlas', key)

        for sound in self.sounds.values():
            if sound:
                sound.stop()
                sound.unload()
        
        # Clear all dicts easily by iterating over our map
        for config in self._type_map.values():
            config['store'].clear()
    