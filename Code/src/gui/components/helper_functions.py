import customtkinter as ctk

def is_overlapping(widget1, widget2):
    # Get bounding box for widget 1
    x1, y1 = widget1.winfo_x(), widget1.winfo_y()
    w1, h1 = widget1.winfo_width(), widget1.winfo_height()
    
    # Get bounding box for widget 2
    x2, y2 = widget2.winfo_x(), widget2.winfo_y()
    w2, h2 = widget2.winfo_width(), widget2.winfo_height()

    # Check if they do NOT overlap; if any of these are true, there is no overlap
    if (x1 + w1 < x2 or x2 + w2 < x1 or 
        y1 + h1 < y2 or y2 + h2 < y1):
        return False
    return True
