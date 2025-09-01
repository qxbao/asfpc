import tkinter as tk
import asyncio
import threading
from tkinter import messagebox

class DialogUtil:
  @staticmethod
  async def confirmation(
    title: str = "Confirmation",
    message: str = "Are you sure?"
  ) -> bool:
        
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    
    def show_dialog():
        root = tk.Tk()
        root.withdraw()
        root.lift()
        root.attributes("-topmost", True)
        root.update()
        
        try:
            result = messagebox.askyesno(title, message, parent=root)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        finally:
            root.destroy()
    
    thread = threading.Thread(target=show_dialog)
    thread.start()
    
    result = await future
    return result