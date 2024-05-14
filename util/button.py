from discord.ui import View, Button

def url_button(label: str, url: str) -> View:
    view = View()
    view.add_item(Button(label=label, url=url))
    return view

def just_url_button(label: str, url) -> View:
    button = Button(label=label, url=url)
    return button