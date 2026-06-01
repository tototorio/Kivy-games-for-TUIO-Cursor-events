from engine.core.commons import *

class Menu(ModalView):
    """
    Main menu overlay that pauses the game.
    Appears at app start, after game completion, or when menu button is pressed.
    """
    def __init__(self, game, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.ranking_view = Ranking(self)

    def _show_ranking(self):
        self.ranking_view.open()

    def update_ranking(self, scores):
        """Updates the top-5 score labels in the menu.
        `scores` is expected to be a list sorted descending."""
        score_label_ids = ['score_1', 'score_2', 'score_3', 'score_4', 'score_5']

        for i, label_id in enumerate(score_label_ids):
            label = self.ids[label_id]
            if i < len(scores):
                label.text = f"{i + 1}. {scores[i]}"
            else:
                label.text = f"{i + 1}. ---"

class Ranking(ModalView):

    def __init__(self, menu: Menu, **kwargs):
        
        # Store game reference for KV access
        self.game = menu.game
        super().__init__(**kwargs)

        self.dismiss()

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
