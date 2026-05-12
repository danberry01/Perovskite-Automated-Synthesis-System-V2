import logging
import customtkinter as ctk
import os
import sys

from ...components.constants import *

# get current directory so we can import from outside guiFrames folder
pp=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(pp)
from drivers.procedure_file_driver import ProcedureFile


class ObstaclesFrame(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master=master, fg_color = FOREGROUND_COLOR ,corner_radius=0 )
        self.obstacle_entries = []
        self._load_obstacles()

        # save button
        self.save_button = ctk.CTkButton(master=self,
                                            text="Save",
                                            fg_color = PLAIN_TEXT_COLOR,
                                            hover_color = FOREGROUND_COLOR_TWO,
                                            corner_radius = 0,
                                            command=self._save_obstacles
                                        )
        self.save_button.grid(row=0, column=0, padx=5, pady=5, sticky="nw")

        # new entry button
        self.new_entry_button = ctk.CTkButton(
                                                master=self, 
                                                text="New Entry", 
                                                fg_color = PLAIN_TEXT_COLOR,
                                                hover_color = FOREGROUND_COLOR_TWO,
                                                corner_radius = 0,
                                                command=self._new_entry
                                            )
        self.new_entry_button.grid(row=0, column=1, padx=5, pady=5,sticky="nw")

    def _new_entry(self):
        entry = ObstacleEntry(master=self)
        entry.grid(row=len(self.obstacle_entries)+1, column=0, columnspan=2, padx=5, pady=5)
        self.obstacle_entries.append(entry)
        return entry

    def _save_obstacles(self):
        obs_data = []
        for e in self.obstacle_entries:
            ob = e.get_entry()
            if ob[0] != "":
                obs_data.append(ob)
        ProcedureFile().Save("persistant/obstacles", obs_data)

    def _load_obstacles(self):
        data = ProcedureFile().Open("persistant/obstacles.yml")
        if not data:
            return
        for ob in data:
            new_ob = self._new_entry()
            # expected format: [name,x1,y1,z1,x2,y2,z2]
            try:
                new_ob.load_entry(ob[0], ob[1], ob[2], ob[3], ob[4], ob[5], ob[6])
            except Exception:
                # try dict style
                if isinstance(ob, dict):
                    new_ob.load_entry(ob.get('name',''), ob.get('x1',0), ob.get('y1',0), ob.get('z1',0), ob.get('x2',0), ob.get('y2',0), ob.get('z2',0))


class ObstacleEntry(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master=master)

        self.name = ctk.CTkEntry(master=self, width = 100, placeholder_text="Name",corner_radius = 0)
        self.name.grid(row=0, column=0,padx=5,pady=5)

        self.x1 = ctk.CTkEntry(master=self, width=50, placeholder_text="X1",corner_radius = 0)
        self.x1.grid(row=0, column=1,padx=5,pady=5)

        self.y1 = ctk.CTkEntry(master=self,width=50,placeholder_text="Y1",corner_radius = 0)
        self.y1.grid(row=0, column=2,padx=5,pady=5)

        self.z1 = ctk.CTkEntry(master=self,width=50, placeholder_text="Z1",corner_radius = 0)
        self.z1.grid(row=0, column=3,padx=5,pady=5)

        self.x2 = ctk.CTkEntry(master=self, width=50, placeholder_text="X2",corner_radius = 0)
        self.x2.grid(row=0, column=4,padx=5,pady=5)

        self.y2 = ctk.CTkEntry(master=self,width=50,placeholder_text="Y2",corner_radius = 0)
        self.y2.grid(row=0, column=5,padx=5,pady=5)

        self.z2 = ctk.CTkEntry(master=self,width=50, placeholder_text="Z2",corner_radius = 0)
        self.z2.grid(row=0, column=6,padx=5,pady=5)

    def get_entry(self):
        name = self.name.get()
        x1 = self.x1.get() or 0
        y1 = self.y1.get() or 0
        z1 = self.z1.get() or 0
        x2 = self.x2.get() or 0
        y2 = self.y2.get() or 0
        z2 = self.z2.get() or 0
        try:
            return [name, float(x1), float(y1), float(z1), float(x2), float(y2), float(z2)]
        except Exception:
            return [name, x1, y1, z1, x2, y2, z2]

    def load_entry(self, name, x1, y1, z1, x2, y2, z2):
        self.name.insert(0, name)
        self.x1.insert(0, x1)
        self.y1.insert(0, y1)
        self.z1.insert(0, z1)
        self.x2.insert(0, x2)
        self.y2.insert(0, y2)
        self.z2.insert(0, z2)


if __name__ == "__main__":
    app = ctk.CTk()
    ctk.set_appearance_mode("dark")
    app.geometry("1200x1000")
    lf = ObstaclesFrame(app)
    lf.grid(row=0, column=0)
    app.mainloop()
