# from droidbot.input_event import InputEvent

import droidbot_old.input_event
from droidbot_old.input_event import InputEvent

class ItemAction:
    def __init__(self, id: int, text: str, event: InputEvent):
        self.id = id
        self.text = text
        self.event = event

if __name__ == "main":
    print(ItemAction(0,"",None))        