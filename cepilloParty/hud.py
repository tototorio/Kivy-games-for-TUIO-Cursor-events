from engine.core.commons import *

class Menu(ModalView):
    """
    Main menu overlay that pauses the game.
    Appears at app start, after game completion, or when menu button is pressed.
    """

    def __init__(self, game_screen, **kwargs):
        # 1. Initialize Kivy first so the KV file is read and IDs are created!
        super().__init__(**kwargs)
        
        # 2. Assign properties
        self.game_screen = game_screen 
        
        # 3. Setup Logic
        self.ranking_view = Ranking(self)
        

    # After the KV is loaded, populate the grid programmatically
    def on_kv_post(self, base_widget):
        """Called after KV layout is created"""
        grid = self.ids.day_ranking_grid
        self.rows_ranking_label = []
        self.rows_ranking_data = []

        for row in range(5):
            # Create score label
            label_score = Factory.ScoreLabel(text=f"{row+1}. 0")
            
            # Create name label
            label_name = Factory.NameLabel(text="---")
            
            grid.add_widget(label_score)
            grid.add_widget(label_name)
            
            # Store references for later updates
            self.rows_ranking_label.append([label_score, label_name])
            self.rows_ranking_data.append([0, "---"])
    
    def _start_game(self):
        """Closes menu and starts/restarts the game"""
        self.dismiss()
        self.game_screen._start_game()
    
    def _show_ranking(self):
        self.ranking_view.open()
    
    def update_title(self, text):
        """Updates the title label text (e.g., for win message)"""
        self.title_label.text = text # type: ignore

    def update_score(self, new_score, name):
        """Updates the ranking logic and the specific KV labels"""
        # Logic to update self.rows_ranking_data goes here...
        # ...

        # Update the specific labels using their IDs from KV
        for index in range(5):
            score_label = self.rows_ranking_label[index][0]
            name_label = self.rows_ranking_label[index][1]

            score_label.text = f"{index+1}. {self.rows_ranking_data[index][0]}"
            name_label.text = f"{self.rows_ranking_data[index][1]}"


class Ranking(ModalView):

    def __init__(self, menu: Menu, **kwargs):
        
        self.menu = menu
        
        # Store game reference for KV access
        self.game = menu.game_screen
        super().__init__(**kwargs)

        self.close()

    def on_kv_post(self, base_widget):
        
        

        # Load JSON configuration
        self.json_path = self.game.assets.get_asset("ranking", "config")
        with open(self.json_path, 'r') as f:
            self.ranking = json.load(f)
        
        self.highscores_label = []
        self.highscores = []

        # Get grid reference
        grid = self.ids.highscores_grid
        
        # Populate grid from JSON data
        for index, score_data in enumerate(self.ranking):
            score = score_data.get('score', 0)
            score_text = f"{index+1}.   {score}"
            name_text = score_data.get('name', '---')
            
            # Create labels using custom classes
            label_score = Factory.HighScoreLabel(text=score_text)
            label_name = Factory.HighNameLabel(text=name_text)
            
            grid.add_widget(label_score)
            grid.add_widget(label_name)
            
            self.highscores_label.append([label_score, label_name])
            self.highscores.append([score, name_text])

    def update_score(self, new_score, name):
        with open(self.json_path, 'r') as f:
            self.ranking = json.load(f)
        
        for index, score_data in enumerate(self.ranking):
            player_score = int(score_data.get('score', 0))

            if new_score >= player_score:
                self.ranking.append({"score": new_score, "name": name})
                self.ranking.sort(
                    key=lambda item: int(item.get("score", 0)),
                    reverse=True
                )
                self.ranking = self.ranking[:10]

                with open(self.json_path, 'w') as f:
                    json.dump(self.ranking, f, indent=4)
                    print(f"Ranking actualizado. {name} añadió {new_score} puntos.")

                # Update graphics
                self.highscores.append([new_score, name])
                self.highscores.sort(key=lambda column: column[0], reverse=True)
                self.highscores = self.highscores[:10]
                
                for index, row in enumerate(self.highscores_label):
                    row[0].text = f"{index+1}. {self.highscores[index][0]}"
                    row[1].text = f"{self.highscores[index][1]}"
                break

    def close(self):
        self.dismiss()
