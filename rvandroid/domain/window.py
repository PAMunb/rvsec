# rvandroid/domain/window.py
class Window:
    def __init__(self, id):
        self.id = id

    def __str__(self):
        return f"Window={self.id}"
