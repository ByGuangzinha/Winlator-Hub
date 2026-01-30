from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image, AsyncImage
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.clock import Clock
from kivy.utils import platform
import webbrowser
import os
import json
import hashlib
import base64
import requests
import threading

from datetime import datetime
from functools import partial

FIREBASE_URL = "link to your database"


COR_FUNDO_APP = (0, 0, 0, 1)
COR_BTN_GAME = (0.12, 0.12, 0.16, 1)
COR_BTN_ROXO = (0.22, 0.08, 0.38, 1)
COR_TEXTO_ROXO = (0.6, 0.25, 0.9, 1)
COR_WIN_LUZ = (0.5, 0.3, 0.8, 1)
COR_SEARCH_BG = (0.1, 0.1, 0.12, 1)
COR_CHIP_OFF = (0.15, 0.15, 0.18, 1)
COR_VERDE = (0.2, 0.8, 0.4, 1)
COR_VERMELHO = (0.9, 0.2, 0.2, 1)
COR_AZUL = (0.2, 0.5, 0.9, 1)
COR_LARANJA = (0.9, 0.5, 0.1, 1)
COR_ROXO_MODERNO = (0.5, 0.2, 0.8, 1)
COR_ROXO_NOME = (0.65, 0.35, 0.95, 1)
COR_VERDE_NOME = (0.3, 0.9, 0.5, 1)
COR_CARD_COMMENT = (0.08, 0.08, 0.12, 1)
COR_CARD_REPLY = (0.06, 0.06, 0.09, 1)

ADMIN_KEY_ENCODED = "your own key"


class Database:
    def __init__(self):
        if platform == 'android':
            from android.storage import app_storage_path
            self.data_dir = app_storage_path()
        else:
            self.data_dir = os.path.dirname(os.path.abspath(__file__))
            if not self.data_dir:
                self.data_dir = '.'
        
        self.users_file = os.path.join(self.data_dir, "users_database.json")
        self.games_file = os.path.join(self.data_dir, "user_games.json")
        self.admin_file = os.path.join(self.data_dir, "admin_list.json")
        self.saved_login_file = os.path.join(self.data_dir, "saved_login.json")
        self.comments_file = os.path.join(self.data_dir, "comments.json")
        self.games_cache_file = os.path.join(self.data_dir, "games_cache.json")
        self._init_files()
    
    def _init_files(self):
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        if not os.path.exists(self.games_file):
            with open(self.games_file, 'w', encoding='utf-8') as f:
                json.dump({"global_games": []}, f)
        if not os.path.exists(self.admin_file):
            with open(self.admin_file, 'w', encoding='utf-8') as f:
                json.dump({"admins": []}, f)
        if not os.path.exists(self.comments_file):
            with open(self.comments_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        if not os.path.exists(self.games_cache_file):
            with open(self.games_cache_file, 'w', encoding='utf-8') as f:
                json.dump({"games": [], "last_update": ""}, f)
    
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def add_global_game(self, game_name, game_link, game_tags=None, game_desc="", game_image_url=""):
        try:
            existing_games = self.get_global_games()
            for g in existing_games:
                if g['nome'].lower() == game_name.lower():
                    return False, "Jogo ja existe no catalogo!"
            
            game = {
                "nome": game_name,
                "link": game_link,
                "tags": game_tags if game_tags else ["novo"],
                "desc": game_desc if game_desc else "Jogo adicionado pelo administrador.",
                "image": game_image_url,
                "added_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                 "admin_user": App.get_running_app().current_user
            }
            
            game_id = self._generate_game_id(game_name)
            
            response = requests.put(
                f"{FIREBASE_URL}games/{game_id}.json",
                json=game,
                timeout=15
            )
            
            if response.status_code == 200:
                self._update_local_cache()
                return True, "Jogo adicionado ao catalogo!"
            else:
                return False, f"Erro ao salvar: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "Sem conexão com a internet!"
        except requests.exceptions.Timeout:
            return False, "Tempo de conexão esgotado!"
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def get_global_games(self):
        try:
            response = requests.get(
                f"{FIREBASE_URL}games.json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    games = list(data.values())
                    self._save_cache(games)
                    return games
                return []
            return self._get_cached_games()
            
        except requests.exceptions.ConnectionError:
            return self._get_cached_games()
        except requests.exceptions.Timeout:
            return self._get_cached_games()
        except Exception:
            return self._get_cached_games()
    
    def delete_global_game(self, game_name):
        try:
            game_id = self._generate_game_id(game_name)
            
            response = requests.delete(
                f"{FIREBASE_URL}games/{game_id}.json",
                timeout=10
            )
            
            if response.status_code == 200:
                self._update_local_cache()
                return True
            return False
            
        except Exception:
            return False
    
    def _generate_game_id(self, game_name):
        game_id = game_name.lower()
        game_id = "".join(c if c.isalnum() else "_" for c in game_id)
        return game_id
    
    def _save_cache(self, games):
        try:
            cache_data = {
                "games": games,
                "last_update": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            with open(self.games_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
    
    def _get_cached_games(self):
        try:
            if os.path.exists(self.games_cache_file):
                with open(self.games_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("games", [])
            return []
        except Exception:
            return []
    
    def _update_local_cache(self):
        try:
            response = requests.get(
                f"{FIREBASE_URL}games.json",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    self._save_cache(list(data.values()))
        except Exception:
            pass
    
    def add_comment(self, game_name, username, comment_text):
        try:
            game_key = self._generate_game_id(game_name)
            
            new_comment = {
                "user": username,
                "text": comment_text,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "replies": []
            }
            
            response = requests.get(
                f"{FIREBASE_URL}comments/{game_key}.json",
                timeout=10
            )
            
            comments = []
            if response.status_code == 200 and response.json():
                comments = response.json()
                if not isinstance(comments, list):
                    comments = []
            
            comments.append(new_comment)
            
            response = requests.put(
                f"{FIREBASE_URL}comments/{game_key}.json",
                json=comments,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Comentario adicionado!"
            return False, "Erro ao salvar comentario!"
            
        except Exception:
            return self._add_comment_local(game_name, username, comment_text)
    
    def _add_comment_local(self, game_name, username, comment_text):
        try:
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
        except Exception:
            comments = {}
        
        game_key = game_name.lower().strip()
        if game_key not in comments:
            comments[game_key] = []
        
        new_comment = {
            "user": username,
            "text": comment_text,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "replies": []
        }
        comments[game_key].append(new_comment)
        
        with open(self.comments_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=4, ensure_ascii=False)
        return True, "Comentario adicionado!"
    
    def get_comments(self, game_name):
        try:
            game_key = self._generate_game_id(game_name)
            
            response = requests.get(
                f"{FIREBASE_URL}comments/{game_key}.json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    return data
            return self._get_comments_local(game_name)
            
        except Exception:
            return self._get_comments_local(game_name)
    
    def _get_comments_local(self, game_name):
        try:
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
            game_key = game_name.lower().strip()
            return comments.get(game_key, [])
        except Exception:
            return []
    
    def delete_comment(self, game_name, comment_index):
        try:
            game_key = self._generate_game_id(game_name)
            
            response = requests.get(
                f"{FIREBASE_URL}comments/{game_key}.json",
                timeout=10
            )
            
            if response.status_code == 200 and response.json():
                comments = response.json()
                if isinstance(comments, list) and 0 <= comment_index < len(comments):
                    comments.pop(comment_index)
                    
                    requests.put(
                        f"{FIREBASE_URL}comments/{game_key}.json",
                        json=comments,
                        timeout=10
                    )
                    return True
            return False
        except Exception:
            return self._delete_comment_local(game_name, comment_index)
    
    def _delete_comment_local(self, game_name, comment_index):
        try:
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
            game_key = game_name.lower().strip()
            if game_key in comments and 0 <= comment_index < len(comments[game_key]):
                comments[game_key].pop(comment_index)
                with open(self.comments_file, 'w', encoding='utf-8') as f:
                    json.dump(comments, f, indent=4, ensure_ascii=False)
                return True
            return False
        except Exception:
            return False
    
    def add_reply(self, game_name, comment_index, username, reply_text):
        try:
            game_key = self._generate_game_id(game_name)
            
            response = requests.get(
                f"{FIREBASE_URL}comments/{game_key}.json",
                timeout=10
            )
            
            if response.status_code == 200 and response.json():
                comments = response.json()
                if isinstance(comments, list) and 0 <= comment_index < len(comments):
                    if "replies" not in comments[comment_index]:
                        comments[comment_index]["replies"] = []
                    
                    new_reply = {
                        "user": username,
                        "text": reply_text,
                        "date": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    comments[comment_index]["replies"].append(new_reply)
                    
                    requests.put(
                        f"{FIREBASE_URL}comments/{game_key}.json",
                        json=comments,
                        timeout=10
                    )
                    return True, "Resposta adicionada!"
            return False, "Comentario não encontrado!"
        except Exception:
            return self._add_reply_local(game_name, comment_index, username, reply_text)
    
    def _add_reply_local(self, game_name, comment_index, username, reply_text):
        try:
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
        except Exception:
            comments = {}
        
        game_key = game_name.lower().strip()
        if game_key not in comments:
            return False, "Comentario não encontrado!"
        if comment_index < 0 or comment_index >= len(comments[game_key]):
            return False, "Comentario não encontrado!"
        
        if "replies" not in comments[game_key][comment_index]:
            comments[game_key][comment_index]["replies"] = []
        
        new_reply = {
            "user": username,
            "text": reply_text,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        comments[game_key][comment_index]["replies"].append(new_reply)
        
        with open(self.comments_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=4, ensure_ascii=False)
        return True, "Resposta adicionada!"
    
    def delete_reply(self, game_name, comment_index, reply_index):
        try:
            game_key = self._generate_game_id(game_name)
            
            response = requests.get(
                f"{FIREBASE_URL}comments/{game_key}.json",
                timeout=10
            )
            
            if response.status_code == 200 and response.json():
                comments = response.json()
                if isinstance(comments, list):
                    if 0 <= comment_index < len(comments):
                        if "replies" in comments[comment_index]:
                            if 0 <= reply_index < len(comments[comment_index]["replies"]):
                                comments[comment_index]["replies"].pop(reply_index)
                                requests.put(
                                    f"{FIREBASE_URL}comments/{game_key}.json",
                                    json=comments,
                                    timeout=10
                                )
                                return True
            return False
        except Exception:
            return self._delete_reply_local(game_name, comment_index, reply_index)
    
    def _delete_reply_local(self, game_name, comment_index, reply_index):
        try:
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
            game_key = game_name.lower().strip()
            if game_key in comments:
                if 0 <= comment_index < len(comments[game_key]):
                    if "replies" in comments[game_key][comment_index]:
                        if 0 <= reply_index < len(comments[game_key][comment_index]["replies"]):
                            comments[game_key][comment_index]["replies"].pop(reply_index)
                            with open(self.comments_file, 'w', encoding='utf-8') as f:
                                json.dump(comments, f, indent=4, ensure_ascii=False)
                            return True
            return False
        except Exception:
            return False
    
    def save_login(self, username, password):
        try:
            data = {"username": username, "password": password, "saved": True}
            with open(self.saved_login_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def get_saved_login(self):
        try:
            if os.path.exists(self.saved_login_file):
                with open(self.saved_login_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("saved", False):
                    return data.get("username", ""), data.get("password", "")
            return None, None
        except Exception:
            return None, None
    
    def clear_saved_login(self):
        try:
            if os.path.exists(self.saved_login_file):
                os.remove(self.saved_login_file)
            return True
        except Exception:
            return False
    
    def is_admin(self, username):
        try:
            with open(self.admin_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return username.lower() in [a.lower() for a in data.get("admins", [])]
        except Exception:
            return False
    
    def make_admin(self, username, secret_key):
        try:
            decoded_key = base64.b64decode(ADMIN_KEY_ENCODED).decode('utf-8')
        except Exception:
            decoded_key = ""
        
        if secret_key != decoded_key:
            return False, "Senha admin incorreta!"
        
        try:
            with open(self.admin_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {"admins": []}
        
        if username.lower() in [a.lower() for a in data.get("admins", [])]:
            return False, "Usuario ja é um administrador!"
        
        data["admins"].append(username)
        with open(self.admin_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True, "Você agora é um administrador!"
    
    def remove_admin(self, username):
        try:
            with open(self.admin_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["admins"] = [a for a in data["admins"] if a.lower() != username.lower()]
            with open(self.admin_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def register_user(self, username, password):
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception:
            users = {}
        
        if username.lower() in [u.lower() for u in users.keys()]:
            return False, "Usuario ja existe!"
        if len(username) < 3:
            return False, "Usuario deve ter pelo menos 3 caracteres!"
        if len(password) < 4:
            return False, "Senha deve ter pelo menos 4 caracteres!"
        
        users[username] = {
            "password": self._hash_password(password),
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True, "Conta criada com sucesso!"
    
    def login_user(self, username, password):
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception:
            return False, "Erro ao acessar banco de dados!"
        
        real_username = None
        for u in users.keys():
            if u.lower() == username.lower():
                real_username = u
                break
        
        if not real_username:
            return False, "Usuario não encontrado!"
        if users[real_username]["password"] != self._hash_password(password):
            return False, "Senha incorreta!"
        return True, real_username


db = Database()


class MenuButton(Button):
    def __init__(self, **kwargs):
        super(MenuButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15,])


class BackButton(Button):
    def __init__(self, **kwargs):
        super(BackButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])


class PurpleButton(Button):
    def __init__(self, **kwargs):
        super(PurpleButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COR_BTN_ROXO)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12,])


class GreenButton(Button):
    def __init__(self, **kwargs):
        super(GreenButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COR_VERDE)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12,])


class RedButton(Button):
    def __init__(self, **kwargs):
        super(RedButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COR_VERMELHO)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12,])


class BlueButton(Button):
    def __init__(self, **kwargs):
        super(BlueButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COR_AZUL)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12,])


class OrangeButton(Button):
    def __init__(self, **kwargs):
        super(OrangeButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COR_LARANJA)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12,])


class DeleteGameButton(Button):
    def __init__(self, **kwargs):
        super(DeleteGameButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.text = ''
        self.bind(pos=self.draw_button, size=self.draw_button)
    
    def draw_button(self, *args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        
        with self.canvas.before:
            Color(0.06, 0.06, 0.08, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[18,])
            Color(0.15, 0.15, 0.18, 1)
            RoundedRectangle(pos=(self.pos[0]+2, self.pos[1]+2), size=(self.width-4, self.height-4), radius=[16,])
            Color(0.05, 0.05, 0.07, 1)
            RoundedRectangle(pos=(self.pos[0]+3, self.pos[1]+3), size=(self.width-6, self.height-6), radius=[15,])
        
        with self.canvas.after:
            Color(0.95, 0.15, 0.15, 1)
            cx = self.center_x
            cy = self.center_y
            tamanho = min(self.width, self.height) * 0.22
            
            Line(
                points=[cx - tamanho, cy - tamanho, cx + tamanho, cy + tamanho],
                width=2.8,
                cap='round'
            )
            Line(
                points=[cx - tamanho, cy + tamanho, cx + tamanho, cy - tamanho],
                width=2.8,
                cap='round'
            )


class ModernPurpleButton(Button):
    def __init__(self, **kwargs):
        super(ModernPurpleButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = 'Roboto'
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.3, 0.1, 0.5, 0.3)
            RoundedRectangle(pos=(self.pos[0] + 2, self.pos[1] - 2), size=self.size, radius=[18,])
            Color(*COR_ROXO_MODERNO)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[18,])


class HamburgerMenuButton(Button):
    def __init__(self, **kwargs):
        super(HamburgerMenuButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.text = ''
        self.bind(pos=self.draw_icon, size=self.draw_icon)
    
    def draw_icon(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 1)
            line_width = 24
            line_height = 3
            spacing = 6
            start_x = self.center_x - line_width / 2
            center_y = self.center_y
            
            RoundedRectangle(pos=(start_x, center_y + spacing + 2), size=(line_width, line_height), radius=[2,])
            RoundedRectangle(pos=(start_x, center_y - line_height / 2), size=(line_width, line_height), radius=[2,])
            RoundedRectangle(pos=(start_x, center_y - spacing - line_height - 2), size=(line_width, line_height), radius=[2,])


class CloseMenuButton(Button):
    def __init__(self, **kwargs):
        super(CloseMenuButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.text = ''
        self.bind(pos=self.draw_icon, size=self.draw_icon)
    
    def draw_icon(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 1)
            line_length = 20
            line_width = 3
            cx = self.center_x
            cy = self.center_y
            
            Line(points=[cx - line_length/2, cy - line_length/2, cx + line_length/2, cy + line_length/2], width=line_width/2, cap='round')
            Line(points=[cx - line_length/2, cy + line_length/2, cx + line_length/2, cy - line_length/2], width=line_width/2, cap='round')


class GameImagePlaceholder(BoxLayout):
    def __init__(self, game_name="", **kwargs):
        super(GameImagePlaceholder, self).__init__(**kwargs)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.game_name = game_name
        
        initial = game_name[0].upper() if game_name else "?"
        self.label = Label(
            text=initial,
            font_size=60,
            font_name='Roboto',
            bold=True,
            color=(0.6, 0.3, 0.9, 1)
        )
        self.add_widget(self.label)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.15, 0.1, 0.2, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[20,])
            Color(0.3, 0.15, 0.5, 0.5)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[20,])


class GameCardWithImage(BoxLayout):
    def __init__(self, game_data, on_click, comments_count=0, **kwargs):
        super(GameCardWithImage, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 160
        self.spacing = 18
        self.padding = [15, 12, 18, 12]
        self.game_data = game_data
        self.on_click = on_click
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
        img_container = BoxLayout(size_hint_x=None, width=130)
        
        image_url = game_data.get('image', '')
        if image_url and image_url.startswith('http'):
            game_img = AsyncImage(
                source=image_url,
                allow_stretch=True,
                keep_ratio=True
            )
            img_container.add_widget(game_img)
        elif image_url and os.path.exists(image_url):
            game_img = Image(
                source=image_url,
                allow_stretch=True,
                keep_ratio=True
            )
            img_container.add_widget(game_img)
        else:
            placeholder = GameImagePlaceholder(game_name=game_data['nome'])
            img_container.add_widget(placeholder)
        
        info_container = BoxLayout(orientation='vertical', spacing=10, padding=[0, 10, 0, 10])
        
        nome_label = Label(
            text=game_data['nome'],
            font_size=25,
            font_name='Roboto',
            bold=True,
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle',
            size_hint_y=0.5
        )
        nome_label.bind(size=nome_label.setter('text_size'))
        
        comments_text = f" [{comments_count}]" if comments_count > 0 else ""
        info_label = Label(
            text=f"PC Game{comments_text}",
            font_size=17,
            font_name='Roboto',
            color=(0.5, 0.5, 0.6, 1),
            halign='left',
            valign='middle',
            size_hint_y=0.25
        )
        info_label.bind(size=info_label.setter('text_size'))
        
        tags_box = BoxLayout(size_hint_y=0.25, spacing=8)
        tags = game_data.get('tags', [])[:3]
        for tag in tags:
            if tag == 'novo':
                tag_color = (0.3, 0.8, 0.3, 1)
            elif tag == 'top':
                tag_color = (1, 0.8, 0, 1)
            else:
                tag_color = (0.6, 0.6, 0.7, 1)
            
            tag_label = Label(
                text=tag.upper(),
                font_size=16,
                font_name='Roboto',
                bold=True,
                color=tag_color,
                size_hint_x=None,
                width=70
            )
            tags_box.add_widget(tag_label)
        
        info_container.add_widget(nome_label)
        info_container.add_widget(info_label)
        info_container.add_widget(tags_box)
        
        self.add_widget(img_container)
        self.add_widget(info_container)
        
        self.bind(on_touch_down=self.on_touch_handler)
    
    def on_touch_handler(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.on_click(self.game_data)
            return True
        return False
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.3)
            RoundedRectangle(
                pos=(self.pos[0] + 3, self.pos[1] - 3),
                size=self.size,
                radius=[24,]
            )
            Color(*COR_BTN_GAME)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[24,])


class AdminGameCardWithImage(BoxLayout):
    def __init__(self, game_data, on_open, on_delete, comments_count=0, **kwargs):
        super(AdminGameCardWithImage, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 160
        self.spacing = 12
        self.padding = [0, 0, 8, 0]
        
        game_card = GameCardWithImage(
            game_data=game_data,
            on_click=on_open,
            comments_count=comments_count,
            size_hint_x=0.82
        )
        
        del_btn = DeleteGameButton(
            size_hint=(None, None),
            size=(58, 58),
            pos_hint={'center_y': 0.5}
        )
        del_btn.bind(on_release=lambda x: on_delete(game_data['nome']))
        
        btn_container = BoxLayout(
            size_hint_x=0.18,
            orientation='vertical'
        )
        btn_container.add_widget(Label(size_hint_y=0.3))
        
        btn_holder = BoxLayout(size_hint_y=0.4)
        btn_holder.add_widget(Label(size_hint_x=0.1))
        btn_holder.add_widget(del_btn)
        btn_holder.add_widget(Label(size_hint_x=0.1))
        
        btn_container.add_widget(btn_holder)
        btn_container.add_widget(Label(size_hint_y=0.3))
        
        self.add_widget(game_card)
        self.add_widget(btn_container)


class AlphabetHeader(BoxLayout):
    def __init__(self, letter, **kwargs):
        super(AlphabetHeader, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 43
        self.padding = [dp(12), dp(12), dp(12), dp(12)]
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
        self.letter_label = Label(
            text=letter.upper(),
            font_size=20,
            font_name='Roboto',
            bold=True,
            color=COR_TEXTO_ROXO,
            size_hint_x=None,
            width=50,
            halign='center',
            valign='middle'
        )
        self.letter_label.bind(size=self.letter_label.setter('text_size'))
        
        self.add_widget(self.letter_label)
        self.add_widget(BoxLayout())
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.12, 0.1, 0.15, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12,])
            Color(0.4, 0.2, 0.6, 0.6)
            Rectangle(pos=(self.pos[0] + 60, self.pos[1] + self.height/2 - 1), size=(self.width - 70, 2))


class ReplyCard(BoxLayout):
    def __init__(self, reply_data, comment_index, reply_index, game_name, is_admin, on_delete, **kwargs):
        super(ReplyCard, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 85
        self.padding = [18, 8, 15, 8]
        self.spacing = 4
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
        top_spacer = BoxLayout(size_hint_y=None, height=5)
        self.add_widget(top_spacer)
        
        header = BoxLayout(size_hint_y=None, height=22, spacing=10)
        
        user_label = Label(
            text=f"[b]{reply_data['user']}[/b]",
            markup=True,
            font_size=14,
            font_name='Roboto',
            color=COR_VERDE_NOME,
            halign='left',
            valign='middle',
            size_hint_x=0.6
        )
        user_label.bind(size=user_label.setter('text_size'))
        
        date_label = Label(
            text=reply_data['date'],
            font_size=11,
            font_name='Roboto',
            color=(0.45, 0.45, 0.5, 1),
            halign='right',
            valign='middle',
            size_hint_x=0.4
        )
        date_label.bind(size=date_label.setter('text_size'))
        
        header.add_widget(user_label)
        header.add_widget(date_label)
        
        reply_box = BoxLayout(size_hint_y=None, height=38)
        
        reply_label = Label(
            text=reply_data['text'],
            font_size=14,
            font_name='Roboto',
            color=(0.85, 0.85, 0.88, 1),
            halign='left',
            valign='top',
            size_hint_x=0.92 if is_admin else 1
        )
        reply_label.bind(size=reply_label.setter('text_size'))
        reply_box.add_widget(reply_label)
        
        if is_admin:
            del_btn = Button(
                text='x',
                size_hint=(None, None),
                size=(30, 30),
                background_normal='',
                background_color=(0, 0, 0, 0),
                font_size=15,
                font_name='Roboto',
                bold=True,
                color=(1, 0.4, 0.4, 1)
            )
            del_btn.bind(pos=self._update_del_btn, size=self._update_del_btn)
            del_btn.bind(on_release=lambda x: on_delete(game_name, comment_index, reply_index))
            self._del_btn = del_btn
            reply_box.add_widget(del_btn)
        
        self.add_widget(header)
        self.add_widget(reply_box)
    
    def _update_del_btn(self, *args):
        if hasattr(self, '_del_btn'):
            self._del_btn.canvas.before.clear()
            with self._del_btn.canvas.before:
                Color(0.5, 0.15, 0.15, 0.8)
                RoundedRectangle(pos=self._del_btn.pos, size=self._del_btn.size, radius=[15,])
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.2, 0.6, 0.4, 0.4)
            RoundedRectangle(pos=(self.pos[0], self.pos[1]), size=(4, self.height), radius=[2,])
            Color(*COR_CARD_REPLY)
            RoundedRectangle(pos=(self.pos[0] + 6, self.pos[1]), size=(self.width - 6, self.height), radius=[16,])


class CommentCard(BoxLayout):
    def __init__(self, comment_data, index, game_name, is_admin, on_delete, on_reply, on_delete_reply, **kwargs):
        super(CommentCard, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = [15, 10, 15, 10]
        self.spacing = 6
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
        replies = comment_data.get('replies', [])
        base_height = 130
        replies_height = len(replies) * 95
        self.height = base_height + replies_height
        
        top_spacer = BoxLayout(size_hint_y=None, height=8)
        self.add_widget(top_spacer)
        
        header = BoxLayout(size_hint_y=None, height=28, spacing=10)
        
        user_label = Label(
            text=f"[b]{comment_data['user']}[/b]",
            markup=True,
            font_size=16,
            font_name='Roboto',
            color=COR_ROXO_NOME,
            halign='left',
            valign='middle',
            size_hint_x=0.6
        )
        user_label.bind(size=user_label.setter('text_size'))
        
        date_label = Label(
            text=comment_data['date'],
            font_size=12,
            font_name='Roboto',
            color=(0.5, 0.5, 0.55, 1),
            halign='right',
            valign='middle',
            size_hint_x=0.4
        )
        date_label.bind(size=date_label.setter('text_size'))
        
        header.add_widget(user_label)
        header.add_widget(date_label)
        
        comment_label = Label(
            text=comment_data['text'],
            font_size=15,
            font_name='Roboto',
            color=(0.92, 0.92, 0.95, 1),
            halign='left',
            valign='top',
            size_hint_y=None,
            height=40
        )
        comment_label.bind(size=comment_label.setter('text_size'))
        
        actions_box = BoxLayout(size_hint_y=None, height=36, spacing=12)
        
        reply_btn = Button(
            text='Responder',
            size_hint_x=0.45,
            background_normal='',
            background_color=(0, 0, 0, 0),
            font_size=13,
            font_name='Roboto',
            bold=True,
            color=(1, 1, 1, 1)
        )
        reply_btn.bind(pos=self._update_reply_btn, size=self._update_reply_btn)
        reply_btn.bind(on_release=lambda x: on_reply(game_name, index, comment_data['user']))
        self._reply_btn = reply_btn
        actions_box.add_widget(reply_btn)
        
        replies_count = len(replies)
        replies_text = f"{replies_count} resposta(s)" if replies_count > 0 else ""
        
        replies_label = Label(
            text=replies_text,
            font_size=13,
            font_name='Roboto',
            color=(0.55, 0.55, 0.6, 1),
            halign='center',
            size_hint_x=0.25
        )
        actions_box.add_widget(replies_label)
        
        if is_admin:
            del_btn = Button(
                text='Deletar',
                size_hint_x=0.3,
                background_normal='',
                background_color=(0, 0, 0, 0),
                font_size=12,
                font_name='Roboto',
                bold=True,
                color=(1, 0.9, 0.9, 1)
            )
            del_btn.bind(pos=self._update_del_btn, size=self._update_del_btn)
            del_btn.bind(on_release=lambda x: on_delete(game_name, index))
            self._del_btn = del_btn
            actions_box.add_widget(del_btn)
        else:
            actions_box.add_widget(Label(size_hint_x=0.3))
        
        self.add_widget(header)
        self.add_widget(comment_label)
        self.add_widget(actions_box)
        
        if replies:
            separator = BoxLayout(size_hint_y=None, height=8)
            self.add_widget(separator)
            
            for reply_idx, reply in enumerate(replies):
                reply_card = ReplyCard(
                    reply_data=reply,
                    comment_index=index,
                    reply_index=reply_idx,
                    game_name=game_name,
                    is_admin=is_admin,
                    on_delete=on_delete_reply
                )
                self.add_widget(reply_card)
    
    def _update_reply_btn(self, *args):
        if hasattr(self, '_reply_btn'):
            self._reply_btn.canvas.before.clear()
            with self._reply_btn.canvas.before:
                Color(0.3, 0.1, 0.5, 0.3)
                RoundedRectangle(pos=(self._reply_btn.pos[0] + 1, self._reply_btn.pos[1] - 1), size=self._reply_btn.size, radius=[18,])
                Color(*COR_ROXO_MODERNO)
                RoundedRectangle(pos=self._reply_btn.pos, size=self._reply_btn.size, radius=[18,])
    
    def _update_del_btn(self, *args):
        if hasattr(self, '_del_btn'):
            self._del_btn.canvas.before.clear()
            with self._del_btn.canvas.before:
                Color(0.6, 0.15, 0.15, 0.9)
                RoundedRectangle(pos=self._del_btn.pos, size=self._del_btn.size, radius=[18,])
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.05, 0.05, 0.08, 0.5)
            RoundedRectangle(pos=(self.pos[0] + 2, self.pos[1] - 3), size=self.size, radius=[20,])
            Color(0.5, 0.2, 0.8, 0.6)
            RoundedRectangle(pos=(self.pos[0], self.pos[1]), size=(5, self.height), radius=[3,])
            Color(*COR_CARD_COMMENT)
            RoundedRectangle(pos=(self.pos[0] + 3, self.pos[1]), size=(self.width - 3, self.height), radius=[20,])


class ModernCommentInput(BoxLayout):
    def __init__(self, **kwargs):
        super(ModernCommentInput, self).__init__(**kwargs)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.1, 0.1, 0.13, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[20,])


class SearchContainer(BoxLayout):
    def __init__(self, **kwargs):
        super(SearchContainer, self).__init__(**kwargs)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COR_SEARCH_BG)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[28,])


class CategoryChip(Button):
    def __init__(self, color_bg=COR_CHIP_OFF, **kwargs):
        super(CategoryChip, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.font_size = 16
        self.font_name = 'Roboto'
        self.bold = True
        self.color_bg = color_bg
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_color(self, new_color):
        self.color_bg = new_color
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.color_bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[22,])


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        
        with self.canvas.before:
            Color(*COR_FUNDO_APP)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        main_layout = BoxLayout(orientation='vertical', padding=[40, 50, 40, 40], spacing=0)
        
        header_space = BoxLayout(size_hint_y=0.08)
        main_layout.add_widget(header_space)
        
        logo_container = BoxLayout(orientation='vertical', size_hint_y=None, height=160, spacing=8)
        
        logo_box = BoxLayout(size_hint=(None, None), size=(80, 80), pos_hint={'center_x': 0.5})
        self.logo_widget = Label(size_hint=(1, 1))
        logo_box.add_widget(self.logo_widget)
        logo_box.bind(pos=self.draw_logo, size=self.draw_logo)
        
        app_name = Label(
            text='WINLATOR HUB',
            font_size=28,
            font_name='Roboto',
            bold=True,
            color=(0.75, 0.45, 1, 1),
            size_hint_y=None,
            height=45
        )
        
        app_subtitle = Label(
            text='Sua biblioteca de jogos',
            font_size=14,
            font_name='Roboto',
            color=(0.5, 0.5, 0.6, 1),
            size_hint_y=None,
            height=25
        )
        
        logo_container.add_widget(logo_box)
        logo_container.add_widget(app_name)
        logo_container.add_widget(app_subtitle)
        main_layout.add_widget(logo_container)
        
        main_layout.add_widget(BoxLayout(size_hint_y=0.06))
        
        form_card = BoxLayout(orientation='vertical', size_hint_y=None, height=380, padding=[25, 30, 25, 25], spacing=12)
        form_card.bind(pos=self.update_form_card, size=self.update_form_card)
        self.form_card = form_card
        
        form_title = Label(
            text='Acesse sua conta',
            font_size=20,
            font_name='Roboto',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=35,
            halign='left'
        )
        form_title.bind(size=form_title.setter('text_size'))
        form_card.add_widget(form_title)
        
        form_card.add_widget(BoxLayout(size_hint_y=None, height=10))
        
        user_label = Label(
            text='USUARIO',
            font_size=11,
            font_name='Roboto',
            bold=True,
            color=(0.6, 0.6, 0.7, 1),
            size_hint_y=None,
            height=20,
            halign='left'
        )
        user_label.bind(size=user_label.setter('text_size'))
        form_card.add_widget(user_label)
        
        self.input_username = TextInput(
            hint_text='Digite seu usuario',
            size_hint_y=None,
            height=48,
            multiline=False,
            font_size=16,
            font_name='Roboto',
            padding=[18, 14, 18, 14],
            background_normal='',
            background_active='',
            background_color=(0.12, 0.12, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.4, 0.4, 0.5, 1),
            cursor_color=(0.75, 0.45, 1, 1)
        )
        form_card.add_widget(self.input_username)
        
        form_card.add_widget(BoxLayout(size_hint_y=None, height=8))
        
        pass_label = Label(
            text='SENHA',
            font_size=11,
            font_name='Roboto',
            bold=True,
            color=(0.6, 0.6, 0.7, 1),
            size_hint_y=None,
            height=20,
            halign='left'
        )
        pass_label.bind(size=pass_label.setter('text_size'))
        form_card.add_widget(pass_label)
        
        self.input_password = TextInput(
            hint_text='Digite sua senha',
            password=True,
            size_hint_y=None,
            height=48,
            multiline=False,
            font_size=16,
            font_name='Roboto',
            padding=[18, 14, 18, 14],
            background_normal='',
            background_active='',
            background_color=(0.12, 0.12, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.4, 0.4, 0.5, 1),
            cursor_color=(0.75, 0.45, 1, 1)
        )
        form_card.add_widget(self.input_password)
        
        save_box = BoxLayout(size_hint_y=None, height=35, spacing=8, padding=[0, 5, 0, 0])
        
        self.save_checkbox = CheckBox(
            size_hint_x=None,
            width=28,
            active=False,
            color=(0.75, 0.45, 1, 1)
        )
        
        save_label = Label(
            text='Salvar login',
            font_size=13,
            font_name='Roboto',
            color=(0.6, 0.6, 0.7, 1),
            halign='left'
        )
        save_label.bind(size=save_label.setter('text_size'))
        
        save_box.add_widget(self.save_checkbox)
        save_box.add_widget(save_label)
        form_card.add_widget(save_box)
        
        self.lbl_message = Label(
            text='',
            font_size=13,
            font_name='Roboto',
            color=(1, 0.4, 0.4, 1),
            size_hint_y=None,
            height=22,
            halign='center'
        )
        form_card.add_widget(self.lbl_message)
        
        main_layout.add_widget(form_card)
        
        main_layout.add_widget(BoxLayout(size_hint_y=None, height=20))
        
        buttons_container = BoxLayout(orientation='vertical', size_hint_y=None, height=125, spacing=12)
        
        self.btn_login = Button(
            text='ENTRAR',
            size_hint_y=None,
            height=52,
            font_size=16,
            font_name='Roboto',
            bold=True,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1)
        )
        self.btn_login.bind(pos=self.update_login_btn, size=self.update_login_btn)
        self.btn_login.bind(on_release=self.do_login)
        buttons_container.add_widget(self.btn_login)
        
        self.btn_register = Button(
            text='CRIAR NOVA CONTA',
            size_hint_y=None,
            height=52,
            font_size=14,
            font_name='Roboto',
            bold=True,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0.75, 0.45, 1, 1)
        )
        self.btn_register.bind(pos=self.update_register_btn, size=self.update_register_btn)
        self.btn_register.bind(on_release=self.do_register)
        buttons_container.add_widget(self.btn_register)
        
        main_layout.add_widget(buttons_container)
        
        main_layout.add_widget(BoxLayout(size_hint_y=0.1))
        
        version_label = Label(
            text='Versão pre alpha',
            font_size=11,
            font_name='Roboto',
            color=(0.35, 0.35, 0.4, 1),
            size_hint_y=None,
            height=25
        )
        main_layout.add_widget(version_label)
        
        self.add_widget(main_layout)
    
    def draw_logo(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.5, 0.25, 0.8, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[16])
            Color(0.15, 0.1, 0.2, 1)
            RoundedRectangle(
                pos=(instance.pos[0] + 3, instance.pos[1] + 3),
                size=(instance.size[0] - 6, instance.size[1] - 6),
                radius=[14]
            )
            Color(0.6, 0.35, 0.9, 1)
            margin = 12
            gap = 6
            pane_w = (instance.width - margin * 2 - gap) / 2
            pane_h = (instance.height - margin * 2 - gap) / 2
            bx, by = instance.pos[0] + margin, instance.pos[1] + margin
            
            RoundedRectangle(pos=(bx, by), size=(pane_w, pane_h), radius=[4])
            RoundedRectangle(pos=(bx + pane_w + gap, by), size=(pane_w, pane_h), radius=[4])
            RoundedRectangle(pos=(bx, by + pane_h + gap), size=(pane_w, pane_h), radius=[4])
            RoundedRectangle(pos=(bx + pane_w + gap, by + pane_h + gap), size=(pane_w, pane_h), radius=[4])
    
    def update_form_card(self, *args):
        self.form_card.canvas.before.clear()
        with self.form_card.canvas.before:
            Color(0, 0, 0, 0.3)
            RoundedRectangle(
                pos=(self.form_card.pos[0] + 2, self.form_card.pos[1] - 3),
                size=self.form_card.size,
                radius=[20]
            )
            Color(0.08, 0.08, 0.1, 1)
            RoundedRectangle(pos=self.form_card.pos, size=self.form_card.size, radius=[20])
            Color(0.18, 0.18, 0.22, 1)
            Line(
                rounded_rectangle=(
                    self.form_card.pos[0], self.form_card.pos[1],
                    self.form_card.width, self.form_card.height,
                    20
                ),
                width=1
            )
    
    def update_login_btn(self, *args):
        self.btn_login.canvas.before.clear()
        with self.btn_login.canvas.before:
            Color(0.4, 0.15, 0.6, 0.4)
            RoundedRectangle(
                pos=(self.btn_login.pos[0] + 2, self.btn_login.pos[1] - 2),
                size=self.btn_login.size,
                radius=[12]
            )
            Color(0.55, 0.25, 0.85, 1)
            RoundedRectangle(pos=self.btn_login.pos, size=self.btn_login.size, radius=[12])
    
    def update_register_btn(self, *args):
        self.btn_register.canvas.before.clear()
        with self.btn_register.canvas.before:
            Color(0.2, 0.1, 0.3, 0.3)
            RoundedRectangle(pos=self.btn_register.pos, size=self.btn_register.size, radius=[12])
            Color(0.55, 0.25, 0.85, 1)
            Line(
                rounded_rectangle=(
                    self.btn_register.pos[0], self.btn_register.pos[1],
                    self.btn_register.width, self.btn_register.height,
                    12
                ),
                width=1.5
            )
    
    def on_enter(self):
        Clock.schedule_once(self.check_saved_login, 0.3)
    
    def check_saved_login(self, dt):
        saved_user, saved_pass = db.get_saved_login()
        if saved_user and saved_pass:
            success, result = db.login_user(saved_user, saved_pass)
            if success:
                app = App.get_running_app()
                app.current_user = result
                main_screen = self.manager.get_screen('main')
                main_screen.set_user(result)
                self.manager.current = 'main'
    
    def do_login(self, instance):
        username = self.input_username.text.strip().replace('\n', '')
        password = self.input_password.text.strip().replace('\n', '')
        
        if not username or not password:
            self.lbl_message.text = "Preencha todos os campos"
            self.lbl_message.color = (1, 0.6, 0.3, 1)
            return
        
        success, result = db.login_user(username, password)
        if success:
            self.lbl_message.text = ""
            if self.save_checkbox.active:
                db.save_login(username, password)
            
            app = App.get_running_app()
            app.current_user = result
            main_screen = self.manager.get_screen('main')
            main_screen.set_user(result)
            self.input_username.text = ""
            self.input_password.text = ""
            self.manager.current = 'main'
        else:
            self.lbl_message.text = result
            self.lbl_message.color = (1, 0.4, 0.4, 1)
    
    def do_register(self, instance):
        username = self.input_username.text.strip().replace('\n', '')
        password = self.input_password.text.strip().replace('\n', '')
        
        if not username or not password:
            self.lbl_message.text = "Preencha todos os campos"
            self.lbl_message.color = (1, 0.6, 0.3, 1)
            return
        
        success, message = db.register_user(username, password)
        if success:
            self.lbl_message.text = "Conta criada com sucesso!"
            self.lbl_message.color = (0.4, 1, 0.6, 1)
            if self.save_checkbox.active:
                db.save_login(username, password)
        else:
            self.lbl_message.text = message
            self.lbl_message.color = (1, 0.4, 0.4, 1)
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class GameDetailsScreen(Screen):
    def __init__(self, **kwargs):
        super(GameDetailsScreen, self).__init__(**kwargs)
        self.current_game = None
        self.current_user = None
        self.is_admin = False
        
        with self.canvas.before:
            Color(*COR_FUNDO_APP)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        self.layout = BoxLayout(orientation='vertical', padding=18, spacing=12)
        
        self.header_box = BoxLayout(size_hint_y=None, height=130, spacing=18)
        
        self.img_container = BoxLayout(size_hint_x=None, width=110)
        self.header_box.add_widget(self.img_container)
        
        info_box = BoxLayout(orientation='vertical', spacing=6)
        
        self.lbl_titulo = Label(
            text="NOME",
            font_size=24,
            font_name='Roboto',
            bold=True,
            color=COR_TEXTO_ROXO,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle'
        )
        self.lbl_titulo.bind(size=self.lbl_titulo.setter('text_size'))
        
        self.lbl_info = Label(
            text="Plataforma: PC Windows",
            font_size=15,
            font_name='Roboto',
            color=(0.5, 0.5, 0.6, 1),
            size_hint_y=None,
            height=22,
            halign='left'
        )
        self.lbl_info.bind(size=self.lbl_info.setter('text_size'))
        
        self.tags_scroll = ScrollView(size_hint_y=None, height=32, do_scroll_x=True, do_scroll_y=False, bar_width=0)
        self.tags_layout = BoxLayout(orientation='horizontal', spacing=8, size_hint_x=None)
        self.tags_layout.bind(minimum_width=self.tags_layout.setter('width'))
        self.tags_scroll.add_widget(self.tags_layout)
        
        info_box.add_widget(self.lbl_titulo)
        info_box.add_widget(self.lbl_info)
        info_box.add_widget(self.tags_scroll)
        info_box.add_widget(Label())
        
        self.header_box.add_widget(info_box)
        
        self.main_scroll = ScrollView(size_hint_y=1)
        self.scroll_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=18, padding=[0, 12, 0, 12])
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))
        
        lbl_desc_title = Label(
            text="[b]DESCRIÇÃO[/b]",
            markup=True,
            font_size=18,
            font_name='Roboto',
            color=(0.7, 0.7, 0.8, 1),
            size_hint_y=None,
            height=35,
            halign='left'
        )
        lbl_desc_title.bind(size=lbl_desc_title.setter('text_size'))
        
        self.lbl_desc = Label(
            text="...",
            font_size=16,
            font_name='Roboto',
            color=(0.85, 0.85, 0.85, 1),
            size_hint_y=None,
            halign='left',
            valign='top',
            line_height=1.4
        )
        self.lbl_desc.bind(width=lambda *x: setattr(self.lbl_desc, 'text_size', (self.lbl_desc.width - 10, None)))
        self.lbl_desc.bind(texture_size=lambda *x: setattr(self.lbl_desc, 'height', self.lbl_desc.texture_size[1] + 10))
        
        separator1 = Label(size_hint_y=None, height=18)
        
        self.lbl_comments_title = Label(
            text="[b]COMENTARIOS[/b]",
            markup=True,
            font_size=18,
            font_name='Roboto',
            color=(0.7, 0.7, 0.8, 1),
            size_hint_y=None,
            height=35,
            halign='left'
        )
        self.lbl_comments_title.bind(size=self.lbl_comments_title.setter('text_size'))
        
        self.comment_input_box = ModernCommentInput(size_hint_y=None, height=65, spacing=14, padding=[14, 12, 14, 12])
        
        self.comment_input = TextInput(
            hint_text='Escreva um comentario...',
            size_hint_x=0.72,
            multiline=True,
            font_size=15,
            font_name='Roboto',
            padding=[16, 14, 16, 14],
            background_normal='',
            background_active='',
            background_color=(0.12, 0.12, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.45, 0.45, 0.5, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        
        self.btn_send_comment = Button(
            text='Enviar',
            size_hint_x=0.28,
            background_normal='',
            background_color=(0, 0, 0, 0),
            font_size=15,
            font_name='Roboto',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.btn_send_comment.bind(pos=self._update_send_btn, size=self._update_send_btn)
        self.btn_send_comment.bind(on_release=self.send_comment)
        
        self.comment_input_box.add_widget(self.comment_input)
        self.comment_input_box.add_widget(self.btn_send_comment)
        
        self.comments_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=14)
        self.comments_layout.bind(minimum_height=self.comments_layout.setter('height'))
        
        self.scroll_content.add_widget(lbl_desc_title)
        self.scroll_content.add_widget(self.lbl_desc)
        self.scroll_content.add_widget(separator1)
        self.scroll_content.add_widget(self.lbl_comments_title)
        self.scroll_content.add_widget(self.comment_input_box)
        self.scroll_content.add_widget(self.comments_layout)
        
        self.main_scroll.add_widget(self.scroll_content)
        
        self.btn_download = MenuButton(text="BAIXAR JOGO", size_hint_y=None, height=70, font_size=22, bold=True)
        btn_voltar = BackButton(text="VOLTAR", size_hint_y=None, height=55, font_size=18)
        btn_voltar.bind(on_release=self.voltar)
        
        self.layout.add_widget(self.header_box)
        self.layout.add_widget(self.main_scroll)
        self.layout.add_widget(self.btn_download)
        self.layout.add_widget(btn_voltar)
        
        self.add_widget(self.layout)
        self.current_link = ""
    
    def _update_send_btn(self, *args):
        self.btn_send_comment.canvas.before.clear()
        with self.btn_send_comment.canvas.before:
            Color(0.3, 0.1, 0.5, 0.4)
            RoundedRectangle(pos=(self.btn_send_comment.pos[0] + 2, self.btn_send_comment.pos[1] - 2), size=self.btn_send_comment.size, radius=[22,])
            Color(*COR_ROXO_MODERNO)
            RoundedRectangle(pos=self.btn_send_comment.pos, size=self.btn_send_comment.size, radius=[22,])
    
    def definir_jogo(self, dados_jogo):
        self.current_game = dados_jogo['nome']
        self.lbl_titulo.text = dados_jogo['nome'].upper()
        self.lbl_desc.text = dados_jogo.get('desc', "Sinopse indisponivel.")
        self.current_link = dados_jogo['link']
        
        self.img_container.clear_widgets()
        image_url = dados_jogo.get('image', '')
        
        if image_url and image_url.startswith('http'):
            game_img = AsyncImage(source=image_url, allow_stretch=True, keep_ratio=True)
            self.img_container.add_widget(game_img)
        elif image_url and os.path.exists(image_url):
            game_img = Image(source=image_url, allow_stretch=True, keep_ratio=True)
            self.img_container.add_widget(game_img)
        else:
            placeholder = GameImagePlaceholder(game_name=dados_jogo['nome'])
            self.img_container.add_widget(placeholder)
        
        app = App.get_running_app()
        self.current_user = app.current_user
        self.is_admin = db.is_admin(self.current_user) if self.current_user else False
        
        self.tags_layout.clear_widgets()
        for tag in dados_jogo.get('tags', []):
            if tag == 'novo':
                cor = (0.3, 0.8, 0.3, 1)
            elif tag == 'top':
                cor = (1, 0.8, 0, 1)
            else:
                cor = COR_CHIP_OFF
            texto = tag.upper() if tag in ['top', 'novo'] else tag
            chip = CategoryChip(text=texto, size_hint=(None, None), size=(len(texto)*12 + 24, 30), color_bg=cor)
            self.tags_layout.add_widget(chip)
        
        comments = db.get_comments(self.current_game)
        total_replies = sum(len(c.get('replies', [])) for c in comments)
        self.lbl_comments_title.text = f"[b]COMENTARIOS ({len(comments)}) - RESPOSTAS ({total_replies})[/b]"
        self.load_comments()
        
        self.btn_download.unbind(on_release=self.abrir_link)
        self.btn_download.bind(on_release=self.abrir_link)
    
    def load_comments(self):
        self.comments_layout.clear_widgets()
        comments = db.get_comments(self.current_game)
        
        if not comments:
            no_comments = Label(
                text="Nenhum comentario ainda. Seja o primeiro!",
                font_size=15,
                font_name='Roboto',
                color=(0.5, 0.5, 0.55, 1),
                size_hint_y=None,
                height=55,
                halign='center'
            )
            no_comments.bind(size=no_comments.setter('text_size'))
            self.comments_layout.add_widget(no_comments)
        else:
            for i, comment in enumerate(reversed(comments)):
                real_index = len(comments) - 1 - i
                card = CommentCard(
                    comment_data=comment,
                    index=real_index,
                    game_name=self.current_game,
                    is_admin=self.is_admin,
                    on_delete=self.delete_comment,
                    on_reply=self.show_reply_popup,
                    on_delete_reply=self.delete_reply
                )
                self.comments_layout.add_widget(card)
    
    def send_comment(self, instance):
        comment_text = self.comment_input.text.strip().replace('\n', ' ')
        if not comment_text:
            return
        
        if not self.current_user:
            self.show_message("Você precisa estar logado para comentar!")
            return
        
        if len(comment_text) < 3:
            self.show_message("Comentario muito curto!")
            return
        
        if len(comment_text) > 500:
            self.show_message("Comentario muito longo (max 500 caracteres)!")
            return
        
        success, message = db.add_comment(self.current_game, self.current_user, comment_text)
        if success:
            self.comment_input.text = ""
            self.load_comments()
            self.update_comments_count()
    
    def show_reply_popup(self, game_name, comment_index, original_user):
        if not self.current_user:
            self.show_message("Você precisa estar logado para responder!")
            return
        
        content = BoxLayout(orientation='vertical', spacing=20, padding=28)
        
        lbl_title = Label(
            text=f'Responder a [color=4DFF7A]{original_user}[/color]',
            markup=True,
            font_size=19,
            font_name='Roboto',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=45
        )
        content.add_widget(lbl_title)
        
        reply_input = TextInput(
            hint_text='Escreva sua resposta...',
            size_hint_y=None,
            height=100,
            multiline=True,
            font_size=15,
            font_name='Roboto',
            padding=[16, 14, 16, 14],
            background_normal='',
            background_active='',
            background_color=(0.12, 0.12, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.45, 0.45, 0.5, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        content.add_widget(reply_input)
        
        popup = Popup(
            title='',
            content=content,
            size_hint=(0.92, 0.48),
            background_color=(0.05, 0.05, 0.08, 1),
            separator_height=0
        )
        
        btn_box = BoxLayout(size_hint_y=None, height=55, spacing=14)
        
        btn_cancel = BackButton(text='Cancelar', font_size=15)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def send_reply(inst):
            reply_text = reply_input.text.strip().replace('\n', ' ')
            if not reply_text:
                return
            if len(reply_text) < 2:
                self.show_message("Resposta muito curta!")
                return
            if len(reply_text) > 300:
                self.show_message("Resposta muito longa (max 300 caracteres)!")
                return
            
            success, message = db.add_reply(game_name, comment_index, self.current_user, reply_text)
            if success:
                popup.dismiss()
                self.load_comments()
                self.update_comments_count()
        
        btn_send = ModernPurpleButton(text='Responder', font_size=15, bold=True)
        btn_send.bind(on_release=send_reply)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_send)
        content.add_widget(btn_box)
        
        popup.open()
    
    def delete_comment(self, game_name, index):
        if not self.is_admin:
            return
        
        content = BoxLayout(orientation='vertical', spacing=18, padding=22)
        lbl = Label(
            text='Deseja deletar este comentario\ne todas as respostas?',
            font_size=16,
            font_name='Roboto',
            halign='center',
            color=(1, 1, 1, 1)
        )
        content.add_widget(lbl)
        
        popup = Popup(
            title='Confirmar Exclusão',
            content=content,
            size_hint=(0.88, 0.40),
            background_color=(0.08, 0.08, 0.12, 1)
        )
        
        btn_box = BoxLayout(size_hint_y=None, height=55, spacing=14)
        
        btn_cancel = BackButton(text='Cancelar', font_size=15)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def confirm_delete(inst):
            db.delete_comment(game_name, index)
            popup.dismiss()
            self.load_comments()
            self.update_comments_count()
        
        btn_delete = RedButton(text='Deletar', font_size=15, bold=True)
        btn_delete.bind(on_release=confirm_delete)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        
        popup.open()
    
    def delete_reply(self, game_name, comment_index, reply_index):
        if not self.is_admin:
            return
        
        content = BoxLayout(orientation='vertical', spacing=18, padding=22)
        lbl = Label(
            text='Deseja deletar esta resposta?',
            font_size=16,
            font_name='Roboto',
            halign='center',
            color=(1, 1, 1, 1)
        )
        content.add_widget(lbl)
        
        popup = Popup(
            title='Confirmar Exclusão',
            content=content,
            size_hint=(0.82, 0.35),
            background_color=(0.08, 0.08, 0.12, 1)
        )
        
        btn_box = BoxLayout(size_hint_y=None, height=55, spacing=14)
        
        btn_cancel = BackButton(text='Cancelar', font_size=15)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def confirm_delete(inst):
            db.delete_reply(game_name, comment_index, reply_index)
            popup.dismiss()
            self.load_comments()
            self.update_comments_count()
        
        btn_delete = RedButton(text='Deletar', font_size=15, bold=True)
        btn_delete.bind(on_release=confirm_delete)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        
        popup.open()
    
    def update_comments_count(self):
        comments = db.get_comments(self.current_game)
        total_replies = sum(len(c.get('replies', [])) for c in comments)
        self.lbl_comments_title.text = f"[b]COMENTARIOS ({len(comments)}) - RESPOSTAS ({total_replies})[/b]"
    
    def show_message(self, message):
        content = BoxLayout(orientation='vertical', spacing=18, padding=22)
        lbl = Label(text=message, font_size=16, font_name='Roboto', halign='center', color=(1, 1, 1, 1))
        content.add_widget(lbl)
        
        popup = Popup(title='Aviso', content=content, size_hint=(0.82, 0.30), background_color=(0.08, 0.08, 0.12, 1))
        btn_ok = PurpleButton(text='OK', size_hint_y=None, height=50, font_size=16)
        btn_ok.bind(on_release=popup.dismiss)
        content.add_widget(btn_ok)
        popup.open()
    
    def abrir_link(self, *args):
        webbrowser.open(self.current_link)
    
    def voltar(self, *args):
        self.manager.current = 'main'
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class MainScreen(Screen):
    ja_carregou = False
    
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.current_user = None
        self.is_admin = False
        self.is_loading = False
        self.jogos_pendentes = []
        self.letra_separadora_atual = ""
        self._search_event = None
        
        self.main_container = FloatLayout(size_hint=(1, 1))
        with self.main_container.canvas.before:
            Color(*COR_FUNDO_APP)
            self.bg_rect = Rectangle(pos=self.main_container.pos, size=self.main_container.size)
        self.main_container.bind(pos=self.update_bg, size=self.update_bg)
        
        self.content_layout = BoxLayout(orientation='vertical', padding=[22, 12, 22, 22], spacing=18, size_hint=(1, 1))
        
        header = BoxLayout(size_hint_y=None, height=95)
        titles_box = BoxLayout(orientation='vertical', spacing=4)
        
        self.lbl_main = Label(
            text='WINLATOR HUB',
            font_size=30,
            font_name='Roboto',
            bold=True,
            color=COR_TEXTO_ROXO,
            halign='left'
        )
        self.lbl_main.bind(size=self.lbl_main.setter('text_size'))
        
        self.lbl_sub = Label(
            text='Biblioteca de Jogos',
            font_size=20,
            font_name='Roboto',
            color=(0.7, 0.7, 0.8, 1),
            halign='left'
        )
        self.lbl_sub.bind(size=self.lbl_sub.setter('text_size'))
        
        titles_box.add_widget(self.lbl_main)
        titles_box.add_widget(self.lbl_sub)
        
        self.menu_btn = HamburgerMenuButton(
            size_hint_x=None,
            width=55,
            pos_hint={'center_y': 0.6}
        )
        self.menu_btn.bind(on_release=self.toggle_menu)
        
        header.add_widget(titles_box)
        header.add_widget(self.menu_btn)
        self.content_layout.add_widget(header)
        
        self.user_info_box = BoxLayout(size_hint_y=None, height=55, spacing=12)
        
        self.lbl_user_info = Label(
            text='Não logado',
            font_size=16,
            font_name='Roboto',
            color=(0.5, 0.8, 0.5, 1),
            halign='left',
            size_hint_x=0.7,
            markup=True
        )
        self.lbl_user_info.bind(size=self.lbl_user_info.setter('text_size'))
        
        self.btn_add_game = Button(
            text='',
            size_hint=(None, None),
            size=(65, 65),
            background_normal='',
            background_color=(0, 0, 0, 0)
        )
        
        with self.btn_add_game.canvas.before:
            Color(0.6, 0.25, 0.9, 1)
            self.add_circle = RoundedRectangle(pos=self.btn_add_game.pos, size=self.btn_add_game.size, radius=[32.5])
            Color(1, 1, 1, 1)
            self.plus_h = Rectangle(pos=(0, 0), size=(30, 5))
            self.plus_v = Rectangle(pos=(0, 0), size=(5, 30))
        
        def atualizar_desenho_mais(instance, value):
            self.add_circle.pos = instance.pos
            self.plus_h.pos = (instance.center_x - 15, instance.center_y - 2.5)
            self.plus_v.pos = (instance.center_x - 2.5, instance.center_y - 15)
        
        self.btn_add_game.bind(pos=atualizar_desenho_mais, size=atualizar_desenho_mais)
        self.btn_add_game.bind(on_release=self.show_add_game_popup)
        self.btn_add_game.opacity = 0
        self.btn_add_game.disabled = True
        
        self.user_info_box.add_widget(self.lbl_user_info)
        self.user_info_box.add_widget(self.btn_add_game)
        self.content_layout.add_widget(self.user_info_box)
        
        search_box = SearchContainer(size_hint_y=None, height=69, padding=[22, 8, 22, 8])
        self.search_input = TextInput(
            hint_text='Procurar jogo...',
            multiline=False,
            background_normal='',
            background_active='',
            background_color=(0, 0, 0, 0),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=COR_TEXTO_ROXO,
            font_size=20,
            font_name='Roboto',
            padding=[12, 14, 12, 14]
        )
        self.search_input.bind(text=self.filtrar_jogos)
        search_box.add_widget(self.search_input)
        self.content_layout.add_widget(search_box)
        
        scroll_cat = ScrollView(size_hint_y=None, height=55, do_scroll_x=True, do_scroll_y=False, bar_width=0)
        self.cat_layout = BoxLayout(orientation='horizontal', spacing=12, size_hint_x=None)
        self.cat_layout.bind(minimum_width=self.cat_layout.setter('width'))
        
        self.botoes_categoria = {}
        categorias = ["Todos", "Aventura", "Ação", "RPG", "FPS", "Luta", "Corrida", "Simulação", "Terror", "Esporte"]
        
        for cat in categorias:
            cor = COR_BTN_ROXO if cat == "Todos" else COR_CHIP_OFF
            btn_cat = CategoryChip(text=cat, size_hint=(None, None), size=(120, 50), color_bg=cor)
            btn_cat.bind(on_release=partial(self.filtrar_por_categoria, cat))
            self.cat_layout.add_widget(btn_cat)
            self.botoes_categoria[cat] = btn_cat
        
        scroll_cat.add_widget(self.cat_layout)
        self.content_layout.add_widget(scroll_cat)
        
        self.loading_label = Label(
            text='Carregando jogos...',
            font_size=16,
            font_name='Roboto',
            color=(0.6, 0.6, 0.7, 1),
            size_hint_y=None,
            height=40
        )
        self.content_layout.add_widget(self.loading_label)
        self.loading_label.opacity = 0
        
        self.banco_de_jogos = []
        self.lista_atual = []
        
        self.scroll = ScrollView(bar_width=5, bar_color=COR_TEXTO_ROXO)
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=14, padding=[0, 12, 0, 0])
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        self.content_layout.add_widget(self.scroll)
        self.main_container.add_widget(self.content_layout)
        
        self.side_menu = BoxLayout(orientation='vertical', size_hint=(0.85, 1), pos_hint={'right': 1, 'y': 0}, spacing=0, padding=0)
        with self.side_menu.canvas.before:
            Color(0, 0, 0, 1)
            self.menu_bg = Rectangle(pos=self.side_menu.pos, size=self.side_menu.size)
        self.side_menu.bind(pos=self.update_menu_bg, size=self.update_menu_bg)
        
        menu_header = BoxLayout(size_hint_y=None, height=145, padding=[28, 35], spacing=22)
        
        self.winlator_icon = Label(size_hint_x=None, width=70)
        self.winlator_icon.bind(pos=lambda instance, val: self.draw_winlator_icon(instance))
        
        self.welcome_txt = Label(
            text="Olá, [b]Usuario[/b]",
            markup=True,
            font_size=26,
            font_name='Roboto',
            halign='left',
            valign='middle'
        )
        self.welcome_txt.bind(size=self.welcome_txt.setter('text_size'))
        
        close_btn = CloseMenuButton(
            size_hint_x=None,
            width=55
        )
        close_btn.bind(on_release=self.toggle_menu)
        
        menu_header.add_widget(self.winlator_icon)
        menu_header.add_widget(self.welcome_txt)
        menu_header.add_widget(close_btn)
        self.side_menu.add_widget(menu_header)
        
        menu_items_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=18, padding=[22, 0])
        menu_items_box.bind(minimum_height=menu_items_box.setter('height'))
        
        opcoes = [
            ('Inicio', 'home'),
            ('Top Games', 'top'),
            ('Atualizar', 'refresh'),
            ('Tornar Admin', 'make_admin'),
            ('Creditos', 'credits'),
            ('Sair', 'logout')
        ]
        
        for texto, acao in opcoes:
            btn = MenuButton(text=f"    {texto}", size_hint_y=None, height=75, halign='left', valign='middle', font_size=20, bold=True)
            btn.bind(size=lambda instance, val: setattr(instance, 'text_size', (instance.width - 30, None)))
            btn.bind(on_release=lambda x, a=acao: self.selecionar_opcao(a))
            menu_items_box.add_widget(btn)
        
        self.side_menu.add_widget(menu_items_box)
        self.side_menu.add_widget(Label())
        self.side_menu.add_widget(Label(text="pre alpha", size_hint_y=None, height=45, font_size=14, font_name='Roboto', color=(0.5, 0.5, 0.5, 1)))
        
        self.add_widget(self.main_container)
    
    def on_enter(self):
        if not MainScreen.ja_carregou or not self.list_layout.children:
            Clock.schedule_once(lambda dt: self.refresh_games_list(), 0.5)
            MainScreen.ja_carregou = True
    
    def set_user(self, username):
        self.current_user = username
        self.is_admin = db.is_admin(username)
        
        admin_text = " [color=FFD700][ADMIN][/color]" if self.is_admin else ""
        self.lbl_user_info.text = f'Logado: [b]{username}[/b]{admin_text}'
        self.welcome_txt.text = f"Olá, [b]{username}[/b]!"
        
        if self.is_admin:
            self.btn_add_game.opacity = 1
            self.btn_add_game.disabled = False
        else:
            self.btn_add_game.opacity = 0
            self.btn_add_game.disabled = True
        
        self.refresh_games_list()
    
    def refresh_games_list(self):
        if self.is_loading:
            return
        
        self.is_loading = True
        self.loading_label.opacity = 1
        
        def fetch_data_thread():
            games = db.get_global_games()
            for jogo in games:
                db.get_comments(jogo['nome'])
            Clock.schedule_once(lambda dt: self.update_games_ui(games), 0)
        
        threading.Thread(target=fetch_data_thread, daemon=True).start()
    
    def update_games_ui(self, games):
        self.lista_atual = self.banco_de_jogos + games
        self.atualizar_lista(self.lista_atual)
        self.loading_label.opacity = 0
        self.is_loading = False
    
    def show_add_game_popup(self, instance):
        if not self.current_user:
            self.show_message_popup("Erro", "Você precisa estar logado!")
            return
        
        if not self.is_admin:
            self.show_message_popup("Erro", "Apenas administradores podem adicionar jogos!")
            return
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=18)
        
        lbl_title = Label(
            text='ADICIONAR JOGO',
            font_size=22,
            font_name='Roboto',
            bold=True,
            color=COR_VERDE,
            size_hint_y=None,
            height=45
        )
        content.add_widget(lbl_title)
        
        lbl_name = Label(text='Nome do Jogo:', font_size=15, font_name='Roboto', size_hint_y=None, height=25, halign='left', color=(1, 1, 1, 1))
        lbl_name.bind(size=lbl_name.setter('text_size'))
        content.add_widget(lbl_name)
        
        input_name = TextInput(
            hint_text='Ex: GTA V, Minecraft...',
            size_hint_y=None,
            height=48,
            multiline=False,
            font_size=16,
            font_name='Roboto',
            padding=[12, 12, 12, 12],
            background_normal='',
            background_active='',
            background_color=(0.2, 0.2, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        content.add_widget(input_name)
        
        lbl_link = Label(text='Link do Jogo:', font_size=15, font_name='Roboto', size_hint_y=None, height=25, halign='left', color=(1, 1, 1, 1))
        lbl_link.bind(size=lbl_link.setter('text_size'))
        content.add_widget(lbl_link)
        
        input_link = TextInput(
            hint_text='https://...',
            size_hint_y=None,
            height=48,
            multiline=False,
            font_size=16,
            font_name='Roboto',
            padding=[12, 12, 12, 12],
            background_normal='',
            background_active='',
            background_color=(0.2, 0.2, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        content.add_widget(input_link)
        
        lbl_tags = Label(text='Tags (separadas por virgula):', font_size=15, font_name='Roboto', size_hint_y=None, height=25, halign='left', color=(1, 1, 1, 1))
        lbl_tags.bind(size=lbl_tags.setter('text_size'))
        content.add_widget(lbl_tags)
        
        input_tags = TextInput(
            hint_text='Ação, Aventura, RPG...',
            size_hint_y=None,
            height=48,
            multiline=False,
            font_size=16,
            font_name='Roboto',
            padding=[12, 12, 12, 12],
            background_normal='',
            background_active='',
            background_color=(0.2, 0.2, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        content.add_widget(input_tags)
        
        lbl_desc = Label(text='Descrição:', font_size=15, font_name='Roboto', size_hint_y=None, height=25, halign='left', color=(1, 1, 1, 1))
        lbl_desc.bind(size=lbl_desc.setter('text_size'))
        content.add_widget(lbl_desc)
        
        input_desc = TextInput(
            hint_text='Descrição do jogo...',
            multiline=True,
            size_hint_y=None,
            height=70,
            font_size=16,
            font_name='Roboto',
            padding=[12, 12, 12, 12],
            background_normal='',
            background_active='',
            background_color=(0.2, 0.2, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        content.add_widget(input_desc)
        
        lbl_image = Label(
            text='URL da Imagem (capa do jogo):',
            font_size=15,
            font_name='Roboto',
            size_hint_y=None,
            height=25,
            halign='left',
            color=(1, 1, 1, 1)
        )
        lbl_image.bind(size=lbl_image.setter('text_size'))
        content.add_widget(lbl_image)
        
        input_image_url = TextInput(
            hint_text='https://exemplo.com/imagem.jpg',
            size_hint_y=None,
            height=48,
            multiline=False,
            font_size=14,
            font_name='Roboto',
            padding=[12, 12, 12, 12],
            background_normal='',
            background_active='',
            background_color=(0.15, 0.2, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.2, 0.6, 0.9, 1)
        )
        content.add_widget(input_image_url)
        
        lbl_dica = Label(
            text='Dica: Use URLs de imagens do Imgur, Discord, etc.',
            font_size=12,
            font_name='Roboto',
            size_hint_y=None,
            height=20,
            halign='left',
            color=(0.5, 0.7, 0.9, 1)
        )
        lbl_dica.bind(size=lbl_dica.setter('text_size'))
        content.add_widget(lbl_dica)
        
        btn_box = BoxLayout(size_hint_y=None, height=55, spacing=12)
        
        popup = Popup(
            title='',
            content=content,
            size_hint=(0.95, 0.95),
            background_color=(0.08, 0.08, 0.1, 1),
            separator_height=0
        )
        
        btn_cancel = RedButton(text='CANCELAR', font_size=16, bold=True)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def save_game(inst):
            name = input_name.text.strip().replace('\n', '')
            link = input_link.text.strip().replace('\n', '')
            tags_text = input_tags.text.strip().replace('\n', '')
            desc = input_desc.text.strip()
            image_url = input_image_url.text.strip().replace('\n', '')
            
            if not name or not link:
                self.show_message_popup("Erro", "Nome e Link são obrigatorios!")
                return
            
            if image_url and not image_url.startswith('http'):
                self.show_message_popup("Erro", "URL da imagem invalida! Deve começar com http:// ou https://")
                return
            
            tags = ["novo"]
            if tags_text:
                tags += [t.strip() for t in tags_text.split(',') if t.strip()]
            
            btn_save = inst
            btn_save.text = "SALVANDO..."
            btn_save.disabled = True
            
            def do_save():
                success, message = db.add_global_game(name, link, tags, desc, image_url)
                
                def update_ui(dt):
                    if success:
                        popup.dismiss()
                        self.show_message_popup("Sucesso", f"'{name}' adicionado ao catalogo!\n\nTodos os usuarios poderão ver este jogo.")
                        self.refresh_games_list()
                    else:
                        btn_save.text = "SALVAR"
                        btn_save.disabled = False
                        self.show_message_popup("Erro", message)
                
                Clock.schedule_once(update_ui, 0)
            
            thread = threading.Thread(target=do_save)
            thread.daemon = True
            thread.start()
        
        btn_save = GreenButton(text='SALVAR NO FIREBASE', font_size=16, bold=True, color=(0, 0, 0, 1))
        btn_save.bind(on_release=save_game)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_save)
        content.add_widget(btn_box)
        
        popup.open()
    
    def show_make_admin_popup(self):
        content = BoxLayout(orientation='vertical', spacing=18, padding=22)
        
        lbl_title = Label(
            text='TORNAR ADMINISTRADOR',
            font_size=20,
            font_name='Roboto',
            bold=True,
            color=COR_TEXTO_ROXO,
            size_hint_y=None,
            height=45
        )
        content.add_widget(lbl_title)
        
        lbl_info = Label(
            text='Digite a senha para\nse tornar administrador:',
            font_size=16,
            font_name='Roboto',
            size_hint_y=None,
            height=55,
            halign='center',
            color=(1, 1, 1, 1)
        )
        content.add_widget(lbl_info)
        
        input_key = TextInput(
            hint_text='Senha Admin...',
            password=True,
            size_hint_y=None,
            height=60,
            multiline=False,
            font_size=20,
            font_name='Roboto',
            padding=[18, 16, 18, 16],
            background_normal='',
            background_active='',
            background_color=(0.2, 0.2, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.25, 0.9, 1)
        )
        content.add_widget(input_key)
        
        popup = Popup(
            title='',
            content=content,
            size_hint=(0.88, 0.48),
            background_color=(0.08, 0.08, 0.1, 1),
            separator_height=0
        )
        
        btn_box = BoxLayout(size_hint_y=None, height=55, spacing=12)
        
        btn_cancel = BackButton(text='CANCELAR', font_size=15)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def confirm_admin(inst):
            key = input_key.text.strip().replace('\n', '')
            success, message = db.make_admin(self.current_user, key)
            popup.dismiss()
            
            if success:
                self.is_admin = True
                self.set_user(self.current_user)
                self.show_message_popup("Sucesso", message)
            else:
                self.show_message_popup("Erro", message)
        
        btn_confirm = PurpleButton(text='CONFIRMAR', font_size=15, bold=True)
        btn_confirm.bind(on_release=confirm_admin)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_confirm)
        content.add_widget(btn_box)
        
        popup.open()
    
    def show_message_popup(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=18, padding=22)
        lbl = Label(text=message, font_size=17, font_name='Roboto', halign='center', color=(1, 1, 1, 1))
        content.add_widget(lbl)
        
        popup = Popup(title=title, content=content, size_hint=(0.85, 0.38), background_color=(0.08, 0.08, 0.12, 1))
        btn_ok = PurpleButton(text='OK', size_hint_y=None, height=50, font_size=17)
        btn_ok.bind(on_release=popup.dismiss)
        content.add_widget(btn_ok)
        popup.open()
    
    def delete_admin_game(self, game_name):
        if not self.is_admin:
            return
        
        content = BoxLayout(orientation='vertical', spacing=18, padding=22)
        lbl = Label(
            text=f'Deseja deletar "{game_name}"?\n\nIsso removera o jogo para todos os usuarios.',
            font_size=17,
            font_name='Roboto',
            halign='center',
            color=(1, 1, 1, 1)
        )
        content.add_widget(lbl)
        
        popup = Popup(title='Confirmar Exclusão', content=content, size_hint=(0.85, 0.42), background_color=(0.08, 0.08, 0.12, 1))
        
        btn_box = BoxLayout(size_hint_y=None, height=55, spacing=12)
        
        btn_cancel = BackButton(text='CANCELAR', font_size=15)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def confirm_delete(inst):
            def do_delete():
                db.delete_global_game(game_name)
                Clock.schedule_once(lambda dt: self.on_delete_complete(popup), 0)
            
            thread = threading.Thread(target=do_delete)
            thread.daemon = True
            thread.start()
        
        btn_delete = RedButton(text='DELETAR', font_size=15, bold=True)
        btn_delete.bind(on_release=confirm_delete)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        
        popup.open()
    
    def on_delete_complete(self, popup):
        popup.dismiss()
        self.refresh_games_list()
        self.show_message_popup("Sucesso", "Jogo deletado do Firebase!")
    
    def filtrar_por_categoria(self, categoria, instance):
        for nome, btn in self.botoes_categoria.items():
            btn.update_color(COR_BTN_ROXO if nome == categoria else COR_CHIP_OFF)
        
        def thread_de_processamento():
            global_games = db.get_global_games()
            todos_jogos = self.banco_de_jogos + global_games
            
            if categoria == "Todos":
                filtrados = todos_jogos
            else:
                filtrados = [j for j in todos_jogos if categoria in j.get('tags', [])]
            
            Clock.schedule_once(lambda dt: self.atualizar_lista(filtrados), 0)
        
        threading.Thread(target=thread_de_processamento, daemon=True).start()
    
    def draw_winlator_icon(self, instance):
        instance.canvas.clear()
        bx, by = instance.x, instance.y + 10
        size = 70
        
        with instance.canvas:
            Color(0.5, 0.25, 0.8, 1)
            RoundedRectangle(pos=(bx, by), size=(size, size), radius=[16])
            Color(0.15, 0.1, 0.2, 1)
            RoundedRectangle(
                pos=(bx + 3, by + 3),
                size=(size - 6, size - 6),
                radius=[14]
            )
            Color(0.6, 0.35, 0.9, 1)
            margin = 12
            gap = 6
            pane_w = (size - margin * 2 - gap) / 2
            pane_h = (size - margin * 2 - gap) / 2
            
            RoundedRectangle(pos=(bx + margin, by + margin), size=(pane_w, pane_h), radius=[4])
            RoundedRectangle(pos=(bx + margin + pane_w + gap, by + margin), size=(pane_w, pane_h), radius=[4])
            RoundedRectangle(pos=(bx + margin, by + margin + pane_h + gap), size=(pane_w, pane_h), radius=[4])
            RoundedRectangle(pos=(bx + margin + pane_w + gap, by + margin + pane_h + gap), size=(pane_w, pane_h), radius=[4])
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.main_container.pos
        self.bg_rect.size = self.main_container.size
    
    def update_menu_bg(self, *args):
        self.menu_bg.pos = self.side_menu.pos
        self.menu_bg.size = self.side_menu.size
    
    def toggle_menu(self, *args):
        if self.side_menu.parent:
            self.main_container.remove_widget(self.side_menu)
        else:
            self.main_container.add_widget(self.side_menu)
            self.draw_winlator_icon(self.winlator_icon)
    
    def selecionar_opcao(self, acao):
        self.toggle_menu()
        
        if acao == 'logout':
            self.current_user = None
            self.is_admin = False
            db.clear_saved_login()
            self.manager.current = 'login'
        elif acao == 'credits':
            self.manager.current = 'credits'
        elif acao == 'make_admin':
            self.show_make_admin_popup()
        elif acao == 'refresh':
            self.refresh_games_list()
            self.show_message_popup("Atualizado", "Lista de jogos atualizada do Firebase!")
        else:
            def thread_opcao():
                global_games = db.get_global_games()
                todos_jogos = self.banco_de_jogos + global_games
                
                if acao == 'home':
                    lista = todos_jogos
                    titulo = "WINLATOR HUB"
                    cor = COR_TEXTO_ROXO
                elif acao == 'top':
                    lista = [jogo for jogo in todos_jogos if 'top' in jogo.get('tags', [])]
                    titulo = "TOP GAMES"
                    cor = (1, 0.8, 0, 1)
                elif acao == 'novo':
                    lista = [jogo for jogo in todos_jogos if 'novo' in jogo.get('tags', [])]
                    titulo = "ATUALIZACOES"
                    cor = (0, 0.8, 1, 1)
                else:
                    lista = todos_jogos
                    titulo = "WINLATOR HUB"
                    cor = COR_TEXTO_ROXO
                
                def update_ui(dt):
                    self.lbl_main.text = titulo
                    self.lbl_main.color = cor
                    self.atualizar_lista(lista)
                
                Clock.schedule_once(update_ui, 0)
            
            threading.Thread(target=thread_opcao, daemon=True).start()
    
    def atualizar_lista(self, lista_de_jogos):
        self.list_layout.clear_widgets()
        self.letra_separadora_atual = ""
        
        if not lista_de_jogos:
            empty_label = Label(text='Nenhum jogo encontrado.', font_size=16, size_hint_y=None, height=150)
            self.list_layout.add_widget(empty_label)
            return
        
        self.jogos_pendentes = lista_de_jogos[5:]
        self.renderizar_jogos(lista_de_jogos[:5])
        
        if self.jogos_pendentes:
            Clock.schedule_once(self.carregar_proximo_lote, 0.05)
    
    def carregar_proximo_lote(self, dt):
        if not self.jogos_pendentes:
            return
        lote = self.jogos_pendentes[:5]
        self.jogos_pendentes = self.jogos_pendentes[5:]
        self.renderizar_jogos(lote)
        if self.jogos_pendentes:
            Clock.schedule_once(self.carregar_proximo_lote, 0.05)
    
    def renderizar_jogos(self, lista_de_jogos):
        jogos_ordenados = sorted(lista_de_jogos, key=lambda x: x['nome'].upper())
        
        for jogo in jogos_ordenados:
            primeira_letra = jogo['nome'][0].upper()
            if not primeira_letra.isalpha():
                primeira_letra = '#'
            
            if primeira_letra != self.letra_separadora_atual:
                self.letra_separadora_atual = primeira_letra
                header = AlphabetHeader(letter=self.letra_separadora_atual)
                self.list_layout.add_widget(header)
            
            if self.is_admin:
                card = AdminGameCardWithImage(
                    game_data=jogo,
                    on_open=self.abrir_detalhes,
                    on_delete=self.delete_admin_game,
                    comments_count=0
                )
            else:
                card = GameCardWithImage(game_data=jogo, on_click=self.abrir_detalhes)
            
            self.list_layout.add_widget(card)
    
    def abrir_detalhes(self, dados_jogo):
        self.jogos_pendentes = []
        
        try:
            details_screen = self.manager.get_screen('details')
            details_screen.definir_jogo(dados_jogo)
            self.manager.transition.direction = 'left'
            self.manager.current = 'details'
        except Exception as e:
            print(f"Erro ao abrir detalhes: {e}")
    
    def filtrar_jogos(self, instance, valor):
        if self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda dt: self.executar_busca(valor), 0.5)
    
    def executar_busca(self, valor):
        busca = valor.lower().strip()
        
        def thread_busca():
            global_games = db.get_global_games()
            todos_jogos = self.banco_de_jogos + global_games
            filtrados = [j for j in todos_jogos if busca in j['nome'].lower()]
            Clock.schedule_once(lambda dt: self.atualizar_lista(filtrados), 0)
        
        threading.Thread(target=thread_busca, daemon=True).start()


class CreditsScreen(Screen):
    def __init__(self, **kwargs):
        super(CreditsScreen, self).__init__(**kwargs)
        
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        layout = BoxLayout(orientation='vertical', padding=45, spacing=28)
        
        layout.add_widget(Label(
            text='SOBRE O APP',
            font_size=32,
            font_name='Roboto',
            bold=True,
            color=COR_TEXTO_ROXO
        ))
        
        info = Label(
            text="App Desenvolvido por [b]Rafaela[/b]\n\n"
                 "Este app foi criado para baixar jogos de PC",
            halign='center',
            font_size=18,
            font_name='Roboto',
            markup=True,
            color=(1, 1, 1, 1)
        )
        layout.add_widget(info)
        
        versao_lbl = Label(
            text="Versão pre alpha",
            font_size=16,
            font_name='Roboto',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height=35
        )
        layout.add_widget(versao_lbl)
        
        voltar_btn = BackButton(text='VOLTAR', size_hint_y=None, height=85, font_size=22, bold=True)
        voltar_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'main'))
        layout.add_widget(voltar_btn)
        
        self.add_widget(layout)
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class WinlatorApp(App):
    current_user = None
    
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(GameDetailsScreen(name='details'))
        sm.add_widget(CreditsScreen(name='credits'))
        return sm


if __name__ == '__main__':
    WinlatorApp().run()
