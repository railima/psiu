# Layout do .dmg para o dmgbuild: o app à esquerda, o atalho para Aplicativos à direita e uma seta no fundo.
# Uso: dmgbuild -s dmg_settings.py Psiu dist/Psiu.dmg
import os.path

app = "dist/Psiu.app"
appname = os.path.basename(app)

format = "UDZO"
files = [app]
symlinks = {"Applications": "/Applications"}
icon_locations = {appname: (170, 190), "Applications": (470, 190)}  # iguais a icon/make_dmg_background.py
background = "icon/dmg-background.tiff"
window_rect = ((200, 160), (640, 400))
default_view = "icon-view"
icon_size = 112
text_size = 13
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
