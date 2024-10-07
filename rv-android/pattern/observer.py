class Observer:
    def update(self, subject, event=None):
        # Implementa a lógica a ser executada quando o sujeito é atualizado
        # TODO abstract
        pass
        #print(f"O estado do sujeito foi alterado para: {subject.state}")


# observable
class Observable:
    def __init__(self):
        self._observers = []

    def add_observer(self, observer):
        self._observers.append(observer)

    def remove_observer(self, observer):
        self._observers.remove(observer)

    def notify_observers(self):
        self.notify_observers_with_event(None)

    def notify_observers_with_event(self, event):
        for observer in self._observers:
            observer.update(self, event)
