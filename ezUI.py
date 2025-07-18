#!/usr/bin/env python3

import curses as cu
import tkinter as tk
import sys
import math
import time

class ezUI:
    VERSION = "0.0.5"
    # Mode constants for GUI and TUI
    class mode:
        GUI = 0
        TUI = 1

    # Virtual DOM element node
    class Element:
        def __init__(self, tag, attributes=None, parent=None, canvas=None):
            self.tag = tag
            self.attributes = attributes or {}
            self.visibility = (attributes or {}).get("visibility", "visible").lower()
            self.size = {
            "width": int(attributes.get("width", -1)) if attributes and "width" in attributes else -1,
            "height": int(attributes.get("height", -1)) if attributes and "height" in attributes else -1,
        }
            self.parent = parent
            self.canvas = canvas
            self.children = []
            self.widget = None
            self._var = None  # Holds StringVar if bound
            self.layout = {
                "side": (attributes or {}).get("pack", "top").lower(),
                "padx": int(attributes.get("padx", 0)) if attributes else 0,
                "pady": int(attributes.get("pady", 0)) if attributes else 0,
            }

        def add_child(self, child):
            child.parent = self
            self.children.append(child)

    # Data store for reactive binding
    class DataModel:
        def __init__(self):
            self.data = {}
            self._bindings = {}

        def bind(self, key, value):
            self.data[key] = value

        def update(self, key, value):
            self.data[key] = value
            if key in self._bindings:
                binding = self._bindings[key]
                if callable(binding):     # For dropdowns or custom objects
                    binding(value)
                else:
                    binding.set(value)   # For StringVar
                    
        def get(self, key, default=None):
            return self.data.get(key, default)
            
    #app options
    class Options:
        DEFAULTS = {
            "show_title_bar": True,
            "show_exit_button": True,
            "title": "ezUI App",
            "full_screen" : False,
            "window_width": 800,
            "window_height": 600
        }

        def __init__(self, user_options=None):
            self._options = self.DEFAULTS.copy()
            if user_options:
                self._options.update(user_options)

        def get(self, key, default=None):
            return self._options.get(key, default)

        def set(self, key, value):
            self._options[key] = value

        def all(self):
            return self._options

    # Shared controller for all interfaces (GUI/TUI)
    class UIApp:
        def __init__(self, root_element, data_model, opts):
            self.root_element = root_element
            self.data = data_model
            self.options = opts
            self.named_elements = {}  # Lookup table for named elements

        def register_element(self, element):
            name = element.attributes.get("name")
            if name:
                self.named_elements[name] = element
        
        def bind_var(self, key, var):
            self.data._bindings[key] = var

        def bind_updater(self, key, callback):
            self.data._bindings[key] = callback
        
        class system:
            def __init__(self, app):
                self.app = app
                self.options = app.options  # Allow direct access: system.options.get(...)
            
            def get_element_by_name(self, name):
                return self.app.named_elements.get(name)
            
            def get_version(self):
                print("Version: {}".format(ezUI.VERSION))
                return ezUI.VERSION
                
            def get_option(self, key, default=None):
                return self.app.options.get(key, default)

            def set_option(self, key, value):
                self.app.options.set(key, value)
                
            def exit(self):                
                print("Releasing the mouse:")
                sys.stdout.write("\033[?1000l") # Disable mouse move tracking
                sys.stdout.flush()
                print(" ")
                print("Exiting app...")
                    
                if hasattr(self.app, 'cleanup') and callable(self.app.cleanup):
                    self.app.cleanup()
                sys.exit(0)

    # GUI renderer using tkinter
    class GUI:
        def __init__(self, root_element, data_model, opts, user_function=None, user_loop=None):
            options = opts
            self.user_loop = user_loop
            self.app = ezUI.UIApp(root_element, data_model, options)
            self.root = tk.Tk()

            title = self.app.options.get("title", "ezUI App")
            show_title_bar = self.app.options.get("show_title_bar", True)
            full_screen = self.app.options.get("full_screen", False)
            
            # Set title and full_screen behavior
            self.root.title(title)
            self.root.attributes('-fullscreen', full_screen)

            # Determine if we need to fake a title bar
            use_custom_title_bar = full_screen and show_title_bar

            if use_custom_title_bar:
                self.root.overrideredirect(True)  # Remove native border
                self.title_frame = tk.Frame(self.root, bg="#dfffff", relief="raised", bd=0)
                self.title_frame.pack(fill="x", side="top")

                self.title_label = tk.Label(self.title_frame, text=title, fg="black", bg="#dfffff", anchor="w", padx=10)
                self.title_label.pack(side="left", fill="x", expand=True)

                if self.app.options.get("show_exit_button", True):
                    exit_button = tk.Button(self.title_frame, text="✕", bg="#dfffff", fg="black", border=0,
                                            command=self.root.destroy)
                    exit_button.pack(side="right", padx=10)

                # Optional: support dragging the window
                def start_move(event):
                    self._drag_start_x = event.x
                    self._drag_start_y = event.y

                def do_move(event):
                    x = self.root.winfo_pointerx() - self._drag_start_x
                    y = self.root.winfo_pointery() - self._drag_start_y
                    self.root.geometry(f"+{x}+{y}")

                self.title_frame.bind("<Button-1>", start_move)
                self.title_frame.bind("<B1-Motion>", do_move)

            else:
                if not show_title_bar:
                    self.root.overrideredirect(True)
                elif not self.app.options.get("show_exit_button", True):
                    self.root.protocol("WM_DELETE_WINDOW", lambda: None)

            if not full_screen:
                width = self.app.options.get("window_width", 800)
                height = self.app.options.get("window_height", 600)
                self.root.geometry(f"{width}x{height}")

            # TUI-style outer border in full_screen
            if full_screen:
                self.border_frame = tk.Frame(self.root, background="#0000cc")
                self.border_frame.pack(fill="both", expand=True, padx=1, pady=1)
                self.full_screen_parent = self.border_frame
                parent_for_build = self.border_frame
            else:
                self.full_screen_parent = self.root
                parent_for_build = self.root

            self.build(parent_for_build, root_element)
            print("GUI started")
            self.app.cleanup = self.root.destroy  # Clean exit for tkinter

            if callable(user_function):
                user_function(self.app.system(self.app), self.app.data)
            if callable(self.user_loop):
                self._start_loop()

            self.root.mainloop()

        def _start_loop(self):
            def loop():
                self.user_loop(self.app.system(self.app), self.app.data)
                self.root.after(16, loop)  # ~60 FPS
            loop()

        def build(self, parent, element):
            if element.visibility == "collapsed":
                return  # skip entirely

            tag = element.tag.lower()
            widget_class = getattr(tk, tag.capitalize(), None)
            widget = None

            widget_args = {
                k: int(v) if k in ("width", "height") and int(v) > 0 else v
                for k, v in element.attributes.items()
                if not k.startswith("ez") and k not in ["name", "pack", "padx", "pady", "x", "y"]
            }

            if "width" in element.attributes and int(element.attributes["width"]) > 0:
                widget_args["width"] = int(element.attributes["width"])
            if "height" in element.attributes and int(element.attributes["height"]) > 0:
                widget_args["height"] = int(element.attributes["height"])

            if tag == 'window':
                widget = parent
                
                # --- Modal Enforcement Begins Here ---
                modal = None
                for child in element.children:
                    if child.tag.lower() == "frame" and child.attributes.get("visibility", "visible") != "collapsed":
                        modal_type = child.attributes.get("ezModal", "None")
                        if modal_type in ["Clear", "Opaque"]:
                            modal = child
                            self.active_modal_element = child
                            break

                if modal:
                    # Destroy all existing widgets except root
                    for el in self.app.elements.values():
                        w = el.widget
                        if w and w != self.full_screen_parent:
                            w.destroy()
                    self.app.elements = {}

                    # Optional: draw gray overlay
                    if modal.attributes.get("ezModal") == "Opaque":
                        backdrop = tk.Frame(widget, bg="#333333")
                        backdrop.place(x=0, y=0, relwidth=1, relheight=1)
                        self.modal_backdrop = backdrop

                    # Build modal subtree only
                    self.build(widget, modal)
                    return  # stop here; modal handles layout
                else:
                    self.active_modal_element = None

            elif tag == 'frame':
                overflow = element.attributes.get("overflow", "visible").lower()
                border = element.attributes.get("border", "true").lower() != "false"
                scroll_x = int(element.attributes.get("scrollLeft", 0))
                scroll_y = int(element.attributes.get("scrollTop", 0))

                if overflow == "hidden":
                    canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=1 if border else 0, highlightbackground="black")
                    inner = tk.Frame(canvas)
                    canvas.create_window((0, 0), window=inner, anchor='nw')
                    
                    def update_scroll_region(event):
                        canvas.configure(scrollregion=canvas.bbox("all"))
                        
                    inner.bind("<Configure>", update_scroll_region)

                    canvas.pack(fill='both', expand=True)
                    canvas.update_idletasks()
                    canvas.xview_moveto(scroll_x / 100.0 if scroll_x else 0)
                    canvas.yview_moveto(scroll_y / 100.0 if scroll_y else 0)

                    widget = inner
                    if parent == self.full_screen_parent:
                        if not any(k in element.attributes for k in ("width", "height", "x", "y")):
                            widget.pack(fill='both', expand=True)
                        if not any(k in element.attributes for k in ("background", "bg")):
                            widget.config(background="#0000cc")
                else:
                    widget = tk.Frame(parent)
                    if border:
                        widget.config(highlightthickness=1, highlightbackground="black")
                        
                    if parent == self.full_screen_parent:
                        if not any(k in element.attributes for k in ("width", "height", "x", "y")):
                            widget.pack(fill='both', expand=True)
                        if not any(k in element.attributes for k in ("background", "bg")):
                            widget.config(background="#0000cc")

            elif tag == 'textbox':
                height = int(widget_args.get("height", 5))
                width = int(widget_args.get("width", 40))
                widget = tk.Text(parent, height=height, width=width)
                if 'ezBind' in element.attributes:
                    key = element.attributes['ezBind'].strip("()")
                    widget.insert('1.0', self.app.data.get(key, ''))

                    def on_text_change(event, key=key, widget=widget):
                        self.app.data.update(key, widget.get("1.0", "end-1c"))

                    widget.bind("<KeyRelease>", on_text_change)

            elif tag == 'optionmenu':
                key = element.attributes['ezBind'].strip("()")
                dropdown_data = self.app.data.get(key, {"options": {}, "selected_index": 0})
                var = tk.StringVar()
                options = dropdown_data.get("options", {})
                labels = list(options.keys())
                selected_index = dropdown_data.get("selected_index", 0)
                var.set(labels[selected_index] if labels else '')
                
                def on_select(value, key=key, var=var):
                    obj = self.app.data.get(key, {})
                    if "options" in obj:
                        labels = list(obj["options"].keys())
                        if value in labels:
                            obj["selected_index"] = labels.index(value)
                            self.app.data.update(key, obj)

                widget = tk.OptionMenu(parent, var, '', command=on_select)

                def update_dropdown(obj):
                    new_options = obj.get("options", {})
                    menu = widget["menu"]
                    menu.delete(0, "end")
                    labels = list(new_options.keys())
                    for i, (label, enabled) in enumerate(new_options.items()):
                        if not enabled:  # disabled
                            menu.add_command(label=label, state="disabled")
                        else:
                            menu.add_command(label=label, command=lambda v=label: var.set(v))
                            
                    current_index = obj.get("selected_index", 0)
                    if current_index < len(labels):
                        var.set(labels[current_index])
                    elif labels:
                        var.set(labels[0])
                    else:
                        var.set('')
                        
                self.app.bind_updater(key, update_dropdown)
                update_dropdown(dropdown_data)

            elif widget_class:
                if tag == 'entry' and 'ezBind' in element.attributes:
                    key = element.attributes['ezBind'].strip("()")
                    var = tk.StringVar()
                    var.set(self.app.data.get(key, ''))

                    def on_change(*args):
                        self.app.data.update(key, var.get())

                    var.trace_add("write", on_change)
                    self.app.data._bindings[key] = var
                    element._var = var
                    widget_args["textvariable"] = var

                elif tag == 'label' and 'ezBind' in element.attributes:
                    key = element.attributes['ezBind'].strip("()")
                    var = tk.StringVar()
                    var.set(self.app.data.get(key, ''))
                    self.app.data._bindings[key] = var
                    element._var = var                    
                    widget_args["textvariable"] = var

                elif tag == 'checkbutton' and 'ezBind' in element.attributes:
                    key = element.attributes['ezBind'].strip("()")
                    var = tk.BooleanVar()
                    var.set(bool(self.app.data.get(key, False)))

                    def on_check(*args):
                        self.app.data.update(key, var.get())

                    var.trace_add("write", on_check)
                    self.app.bind_var(key, var)
                    self.app.data._bindings[key] = var
                    element._var = var

                    # Remove any potential conflicts
                    widget_args.pop("background", None)
                    widget_args.pop("bg", None)
                    widget_args.pop("foreground", None)
                    widget_args.pop("fg", None)
                    
                    bg = element.attributes.get("background") or element.attributes.get("bg") or "#0000ff"
                    fg = element.attributes.get("foreground") or element.attributes.get("fg") or "#ffffff"

                    #widget_args["background"] = bg
                    #widget_args["foreground"] = fg

                    widget = tk.Checkbutton(parent, variable=var, **widget_args)

                    try:
                        widget.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg, selectcolor=bg)
                    except Exception as e:
                        print("Warning: Failed to set colors:", e)

                elif tag == 'radiobutton' and 'ezBind' in element.attributes and 'value' in element.attributes:
                    key = element.attributes['ezBind'].strip("()")
                    value = element.attributes["value"]
                    var = self.app.data._bindings.get(key)
                    if not var:
                        var = tk.StringVar()
                        var.set(self.app.data.get(key, ''))

                        def on_radio(*args):
                            self.app.data.update(key, var.get())

                        var.trace_add("write", on_radio)
                        self.app.bind_var(key, var)
                        self.app.data._bindings[key] = var

                    element._var = var
                    widget_args.pop("value", None)
                    widget_args.pop("background", None)
                    widget_args.pop("bg", None)
                    widget_args.pop("foreground", None)
                    widget_args.pop("fg", None)
                    
                    bg = element.attributes.get("background") or element.attributes.get("bg") or "#0000ff"
                    fg = element.attributes.get("foreground") or element.attributes.get("fg") or "#ffffff"

                    #widget_args["background"] = bg
                    #widget_args["foreground"] = fg

                    widget = tk.Radiobutton(parent, variable=var, value=value, **widget_args)
                    try:
                        widget.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg, selectcolor=bg)
                    except Exception as e:
                        print("Warning: Failed to set colors:", e)
                    
                elif tag == 'canvas':
                    width = int(element.attributes.get("width", 200))
                    height = int(element.attributes.get("height", 100))
                    widget = tk.Canvas(parent, width=width, height=height)
                    if 'init' in element.attributes:
                        fn = self.app.data.get(element.attributes['init'])
                        if callable(fn):
                            fn(widget)

                if widget is None and widget_class:
                    widget = widget_class(parent, **widget_args)
                    bg = element.attributes.get("background") or element.attributes.get("bg")
                    fg = element.attributes.get("foreground") or element.attributes.get("fg")

                    if not bg:
                        if tag in ('textbox', 'entry'):
                            bg = "#ffffff"
                        elif tag == 'button':
                            bg = "#cccccc"
                        else: 
                            bg = "#0000ff"

                    if not fg:
                        if tag in ('textbox', 'entry','button'):
                            fg = "#000000"
                        else: 
                            fg = "#ffffff"

                    if widget and hasattr(widget, "config"):
                        widget.config(background=bg, foreground=fg)

                if 'ezClick' in element.attributes:
                    handler_name = element.attributes['ezClick']
                    handler = self.app.data.get(handler_name)
                    if handler and hasattr(widget, "config"):
                        widget.config(command=lambda e=element: handler(e, self.app.system(self.app), self.app.data))

            if widget and tag != 'window':
                if "x" in element.attributes and "y" in element.attributes:
                    widget.place(x=int(element.attributes["x"]), y=int(element.attributes["y"]))
                else:
                    pack_args = {}
                    side = element.attributes.get("pack", "top").lower()
                    padx = element.attributes.get("padx")
                    pady = element.attributes.get("pady")

                    if side:
                        pack_args["side"] = side
                    if padx and int(padx) > 0:
                        pack_args["padx"] = int(padx)
                    if pady and int(pady) > 0:
                        pack_args["pady"] = int(pady)

                    # 👇 Inject full_screen auto-pack if this is root frame
                    if tag == "frame" and parent == self.full_screen_parent and not any(k in element.attributes for k in ("width", "height", "x", "y")):
                        pack_args["fill"] = "both"
                        pack_args["expand"] = True

                    if element.visibility == "hidden":
                        widget.lower()
                        widget.configure(state="disabled")

                    widget.pack(**pack_args)

            element.widget = widget
            self.app.register_element(element)

            for child in element.children:
                self.build(widget or parent, child)
                
    # TUI renderer uses curses
    class TUI:
        def __init__(self, root_element, data_model, opts, user_function=None, user_loop=None):
            options = opts
            self.app = ezUI.UIApp(root_element, data_model, options)
            self.system = system = self.app.system(self.app)
            self.screen = None
            self.focus_index = None
            self.focus_element = None
            self.last_focus_index = -1  # to track prior focus element
            self.elements_flat = []  # Linear list of interactive elements
            self.element_coords = []  # List of (x1, y1, x2, y2, element)
            self.clickable_zones = []  # List of (x1, y1, x2, y2, handler, name, element)
            self.layout_map = {}  # element -> (x, y)
            self.user_function = user_function
            self.user_loop = user_loop
            self.hover_element = None
            self.dropdowns = {}  # Maps dropdown name to (main dropdown element, dropdown frame)
            self.active_dropdown = None  # Currently opened dropdown name or None
            self.dropdown_guard = False # give dropdowns priority
            self.just_opened_dropdown = False # delays closing the dropdown
            self.dropdown_opener_name = None
            self._close_dropdown_next_frame = False
            self.modal_clickable_zones = []
            self.modal_root_name = None
            self.active_modal_element = None
            self.queue = {} # Stores {"mousebutton", "element", "handler", "zone", "name"} a;;ping fot cross-evertihng mouse up
            self.cursor_pos = 0
            self.insert_mode = False
            self.blink_state = True
            self.blink_timer = 0
            self.mouse_x = -1
            self.mouse_y = -1
            self.mouse_left = False
            self.mouse_right = False
            self.bg_color = (0, 0, 246)
            self.fg_color = (255,255,255)
            self.counter = 0
            
            self.screen = cu.initscr()
            if opts.get("full_screen", False):
                rows, cols = self.screen.getmaxyx()
            else:
                pixel_width = options.get("window_width", 800)
                pixel_height = options.get("window_height", 600)
                cols, rows = self.downscale_resolution(pixel_width, pixel_height)
                
            self.computed_width = cols
            self.computed_height = rows
            self.window_body_width = cols
            self.window_body_height = rows
            self.exit_button_rect = (0, 0, 0, 0)
            self.app.cleanup = self.cleanup
            
            print("TUI started")
            
            #Initialize curses here
            cu.noecho()
            cu.mousemask(cu.ALL_MOUSE_EVENTS | cu.REPORT_MOUSE_POSITION)
            print("Capturing mouse movements:")
            sys.stdout.write("\033[?1000h")  # Enable mouse move tracking
            sys.stdout.flush()
            print(" ")
            self.screen.nodelay(True)  # make getch non-blocking
            cu.cbreak()
            cu.curs_set(0)
            self.screen.keypad(True)
            
            # Enable color
            if cu.has_colors():
                cu.start_color()
                cu.init_pair(1, cu.COLOR_WHITE, cu.COLOR_BLACK)

            # Optional: catch cleanup on exit
            import atexit
            atexit.register(self.cleanup)
            
            self.canvas = ezUI.Canvas(self.computed_width,self.computed_height, ezUI.Canvas.mode.CP437)
            self.run()

        def run(self):
            cu.curs_set(0)
            self.screen.keypad(True)
            self.screen.nodelay(True)  # <-- make getch non-blocking
            self.running = True

            if self.user_function:
                self.user_function(self.app.system(self.app), self.app.data)
                
            self.make_optionmenus(self.app.root_element)

            self.draw_ui()
            
            while self.running:
                self.blink_timer += 1
                
                if self.blink_timer >= 20:
                    self.blink_timer = 0
                    self.blink_state = not self.blink_state
                
                try:
                    id, self.mouse_x, self.mouse_y, _, bstate = cu.getmouse()
                    self._check_hover()
    
                    self.mouse_left = False
                    self.mouse_right = False
                    
                    self.mouse_left = bool(bstate & cu.BUTTON1_CLICKED)
                    self.mouse_right = bool(bstate & cu.BUTTON3_CLICKED)  # BUTTON2 = middle click                          
                        
                    self.handle_mouse()
                    
                except cu.error:
                    pass
                
                key = self.screen.getch()
                if key != -1:
                    self.handle_input(key)
                
                if self.user_loop:
                    self.user_loop(self.system(self.app), self.app.data)
                
                self.draw_ui()
                
                if self._close_dropdown_next_frame:
                    dropdown = self.system.get_element_by_name(self.active_dropdown)
                    if dropdown:
                        dropdown.attributes["visibility"] = "collapsed"
                        dropdown.visibility = "collapsed"
                    self.active_dropdown = None
                    self._close_dropdown_next_frame = False
                    self.compute_layout()
                
                if self.dropdown_guard:
                    self.dropdown_guard = False
                    
                time.sleep(0.01)  # small delay to prevent CPU spinning
                
        def _check_hover(self):
            for x1, y1, x2, y2, handler, name, element in self.clickable_zones:
                if x1 <= self.mouse_x <= x2 and y1 == self.mouse_y:
                    if self.hover_element != name:
                        self.hover_element = name
                    return

            # If not hovering over anything
            if self.hover_element is not None:
                self.hover_element = None
                
        def parse_color(self, value, default):
            # If value is a hex string like "#ffffff"
            if isinstance(value, str) and value.startswith("#") and len(value) == 7:
                try:
                    r = int(value[1:3], 16)
                    g = int(value[3:5], 16)
                    b = int(value[5:7], 16)
                    return (r, g, b)
                except ValueError:
                    pass  # Fall through to use default

            # If default is already a tuple, return it
            if isinstance(default, tuple) and len(default) == 3:
                return default

            # If default is a hex string
            if isinstance(default, str) and default.startswith("#") and len(default) == 7:
                try:
                    r = int(default[1:3], 16)
                    g = int(default[3:5], 16)
                    b = int(default[5:7], 16)
                    return (r, g, b)
                except ValueError:
                    pass

            return (0, 0, 0)  # Fallback safe default
        
        @staticmethod            
        def downscale_resolution(real_pixel_width, real_pixel_height, cell_width=8, cell_height=16):
            cols = real_pixel_width // cell_width
            rows = real_pixel_height // cell_height
            return cols, rows
            
        def make_optionmenus(self,parent):
            
            def make_dropdowns_recursive(el):
                if el.tag.lower() == "optionmenu":
                    name = el.attributes.get("name")
                    if not name:
                        pass  # require name for tracking
                    else:
                        key = el.attributes.get("ezBind", "").strip("()")
                        dropdown_data = self.app.data.get(key, {"options": [], "selected_index": 0})
                        options = dropdown_data.get("options", {})
                        labels = list(options.keys())

                        # Dynamic width based on longest label + 4
                        max_label_len = max((len(label) for label in labels), default=0)
                        dropdown_width = max_label_len + 4
                        dropdown_height = len(labels)

                        drop_frame = ezUI.Element("frame", {
                            "name": "{}_dropdown".format(name),
                            "x": "0",  # will be repositioned later
                            "y": "0",
                            "width": str(dropdown_width * 8),     # pixels
                            "height": str(dropdown_height * 16),  # pixels
                            "visibility": "collapsed",
                            "ezModal": "clear",
                            "border": "false",
                            "overflow": "hidden",
                            "bg": "#cccccc"
                        })

                        # Each button sets index and hides dropdown
                        for i, (label, enabled) in enumerate(options.items()):
                            btn = ezUI.Element("button", {
                                "text": label,
                                "name": "{}_option_{}".format(name,i),
                                "width": str(max_label_len + 4)
                            })
                            
                            def make_handler(index, ui=self):  # ← capture self as ui
                                def handler(e, system, data):
                                    if key:
                                        obj = data.get(key)
                                        if isinstance(obj, dict) and "selected_index" in obj:
                                            obj["selected_index"] = index
                                            data.update(key, obj)

                                    dropdown_name = "{}_dropdown".format(name)
                                    dropdown = system.get_element_by_name(dropdown_name)
                                    if dropdown:
                                        dropdown.attributes["visibility"] = "collapsed"
                                        dropdown.visibility = "collapsed"
                                    
                                    ui.active_dropdown = None
                                    self.dropdown_opener_name = None
                                    ui.compute_layout()
                                return handler
                            
                            if enabled:
                                self.app.data.bind("{}_option_{}_handler".format(name,i), make_handler(i))
                                btn.attributes["ezClick"] = "{}_option_{}_handler".format(name,i)
                                
                            drop_frame.add_child(btn)

                            # Register and append dropdown frame
                            self.dropdowns[name] = (el, drop_frame)
                            self.app.register_element(drop_frame)
                            self.app.root_element.add_child(drop_frame)
                                
                            #self.elements_flat.append(drop_frame)                            
                            
                for child in el.children: 
                    make_dropdowns_recursive(child)
                
            for child in parent.children: 
                make_dropdowns_recursive(child)

        def compute_layout(self):
            self.elements_flat = []
            self.layout_map = {}

            def find_modal(root):
                stack = [root]
                while stack:
                    el = stack.pop()
                    if el.attributes.get("ezModal", "").lower() in ("clear", "opaque") and el.visibility == "visible":
                        return el
                    stack.extend(el.children[::-1])
                return None

            modal_element = find_modal(self.app.root_element)
            self.active_modal_element = modal_element
            self.modal_root_name = modal_element.attributes.get("name") if modal_element else None
            
            el = self.app.root_element
            self.title = el.attributes.get("title", "ezUI")

            max_width = self.window_body_width
            max_height = self.window_body_height
            layout_offset_x = 1
            layout_offset_y = 1 if self.app.options.get("show_title_bar", True) else 0
            layout_right_pad = 1
            layout_bottom_pad = 1

            self.window_body_width = self.computed_width - layout_offset_x - layout_right_pad
            self.window_body_height = self.computed_height - layout_offset_y - layout_bottom_pad

            def layout_recursive(element, x, y):                
                if element.visibility == "collapsed":
                    return  # Skip entirely
                
                nonlocal max_width, max_height
                cursor_x = x
                cursor_y = y
                right_x = self.computed_width
                bottom_y = y + self.window_body_height

                def is_focusable_tag(tag):
                    return tag in ["entry", "button", "checkbutton", "radiobutton", "optionmenu"]

                def add_focusable(child, width, height):
                    self.element_coords.append((
                        self.layout_map[child][0],
                        self.layout_map[child][1],
                        self.layout_map[child][0] + width - 1,
                        self.layout_map[child][1] + height - 1,
                        child
                    ))
                    
                    if child.tag.lower() in ["button", "checkbutton", "radiobutton"]:
                        name = child.attributes.get("name")
                        handler_name = child.attributes.get("ezClick")
                        x, y = self.layout_map[child]

                        # Default handler for toggling checkbutton or selecting radiobutton
                        def default_handler(e, system, data):
                            key = e.attributes.get("ezBind", "").strip("()")
                            if not key:
                                return
                            if e.tag.lower() == "checkbutton":
                                current = data.get(key, False)
                                data.update(key, not bool(current))
                            elif e.tag.lower() == "radiobutton":
                                key = e.attributes.get("ezBind", "").strip("()")
                                value = e.attributes.get("value")
                                if key and value:
                                    data.update(key, value)

                        if name:
                            if handler_name:
                                handler = self.app.data.get(handler_name)
                                if not callable(handler):
                                    handler = default_handler
                            else:
                                handler = default_handler

                            self.clickable_zones.append((x,y,x + width - 1,y,lambda h=handler, e=child: h(e, self.app.system(self.app), self.app.data),name,child))
                    
                    elif child.tag.lower() == "optionmenu":
                        name = child.attributes.get("name")
                        x, y = self.layout_map[child]
                        
                        # Add clickable dropdown toggle zone
                        def make_open_dropdown_handler(dropdown_element, toggle_element):
                            def open_dropdown(e=toggle_element, dropdown=dropdown_element):                                    

                                # Collapse previous dropdown if it's different
                                if self.active_dropdown and self.active_dropdown != dropdown.attributes.get("name"):
                                    prev = self.app.system(self.app).get_element_by_name(self.active_dropdown)
                                    if prev:
                                        prev.attributes["visibility"] = "collapsed"
                                        prev.visibility = "collapsed"

                                # Toggle this one
                                current_visibility = dropdown.attributes.get("visibility", "collapsed")
                                new_state = "visible" if current_visibility == "collapsed" else "collapsed"

                                dropdown.attributes["visibility"] = new_state
                                self.dropdown_opener_name = toggle_element.attributes.get("name")
                                dropdown.visibility = new_state
                                self.active_dropdown = dropdown.attributes["name"] if new_state == "visible" else None
                                self.dropdown_guard = (new_state == "visible")
                                self.just_opened_dropdown = True
                                
                                self.compute_layout()
                            return open_dropdown
                            
                        dropdown_name = "{}_dropdown".format(name)
                        drop_frame = self.system.get_element_by_name(dropdown_name)
                            
                        handler = make_open_dropdown_handler(drop_frame, child)
                            
                        labels = list(options.keys())
                        selected_index = dropdown_data.get("selected_index", 0)
                        selected_label = labels[selected_index] if selected_index < len(labels) else ""
                        # Dynamic width based on longest label + 4
                        max_label_len = max((len(label) for label in labels), default=0)
                        dropdown_width = max_label_len + 4
                        
                        self.clickable_zones.append((
                            x, y,
                            x + dropdown_width, y,
                            handler, 
                            name,
                            child
                        ))
                        
                        dropdown_name = "{}_dropdown".format(name)
                        
                        drop_height = len(self.app.data.get(name, {}).get("options", {})) - 1
                        window_height = self.window_body_height

                        drop_y = y + 1
                        
                        if drop_y + drop_height > window_height:
                            drop_y = max(0, window_height - drop_height)

                        drop_frame.attributes["x"] = str(x * 8)
                        drop_frame.attributes["y"] = str(drop_y * 16)
                        
                for child in element.children:                    
                    if child.visibility == "collapsed":
                        continue
                        
                    tag = child.tag.lower()
                    side = child.layout["side"]
                    padx, pady = self.downscale_resolution(int(child.layout["padx"]), int(child.layout["pady"]))
                    raw_text = child.attributes.get("text", "")
                    text_width = len(str(raw_text))
                    
                    # Estimate default width for non-frame controls
                    est_width = 12
                    est_height = 1
                    if tag == "label":
                        est_width = text_width + 2
                        text = child.attributes.get("text", "")
                        num_lines = text.count("\n") + 1
                        est_height = max(num_lines, int(child.attributes.get("height", num_lines)))
                    elif tag == "button":
                        text = child.attributes.get("text", "")
                        text_width = len(text)                        
                        el_width = int(child.attributes.get("width","10"))
                        space_len = 0 if el_width == (text_width + 4) else  (el_width - (text_width + 4))
                        if text_width/2 != math.floor(text_width/2):
                            space_len +=1
                        est_width = text_width + space_len + 4
                    elif tag in ["checkbutton", "radiobutton"]:
                        est_width = text_width + 4
                    elif tag == "optionmenu":
                        key = child.attributes.get("ezBind", "").strip("()")
                        dropdown_data = self.app.data.get(key, {"options": [], "selected_index": 0})
                        options = dropdown_data.get("options", {})
                        selected_index = dropdown_data.get("selected_index", 0)
                        labels = list(options.keys())

                        # Dynamic width based on longest label + 4
                        max_label_len = max((len(label) for label in labels), default=0)
                        dropdown_width = max_label_len + 4                        
                        est_width = dropdown_width
                        child.attributes["width"] = est_width

                    width = int(child.attributes.get("width", est_width))
                    height = int(child.attributes.get("height", est_height))                   
                    
                    # --- Handle <frame> ---
                    if tag == "frame":                        
                        child_width = int(child.attributes.get("width", -1))
                        child_height = int(child.attributes.get("height", -1))

                        if element.tag == "window" and (child_width <= 0 or child_height <= 0):
                            usable_w = self.window_body_width
                            usable_h = self.window_body_height
                            child_width = usable_w if child_width <= 0 else child_width
                            child_height = usable_h if child_height <= 0 else child_height

                            if "x" not in child.attributes and "y" not in child.attributes:
                                layout_x = layout_offset_x + (usable_w - child_width) // 2
                                layout_y = layout_offset_y
                            else:
                                layout_x, layout_y = self.downscale_resolution(
                                    int(child.attributes.get("x", 0)), int(child.attributes.get("y", 0))
                                )
                        else:
                            child_width = child_width if child_width > 0 else 10
                            child_height = child_height if child_height > 0 else 5

                            if "x" in child.attributes and "y" in child.attributes:
                                layout_x, layout_y = self.downscale_resolution(
                                    int(child.attributes["x"]), int(child.attributes["y"])
                                )
                            else:
                                layout_x, layout_y = cursor_x, cursor_y

                        self.layout_map[child] = (layout_x, layout_y)
                        child.canvas = ezUI.Canvas(child_width, child_height, ezUI.Canvas.mode.CP437)
                        child.x, child.y = layout_x, layout_y
                        child.width, child.height = child_width, child_height
                        layout_recursive(child, layout_x, layout_y)
                        
                        self.modal_root_name = None
                        self.active_modal_element = None
                        modal_element = None
                        
                        modal_type = child.attributes.get("ezModal", "None").lower()
                        if modal_type in ["clear", "opaque"]:
                            self.modal_root_name = child.attributes.get("name")
                            modal_element = child
                            self.active_modal_element = modal_element
                            break

                        if modal_element:
                            # Restrict clickable zones to modal frame + its subtree
                            allowed = set()

                            def collect_subtree_names(e):
                                name = e.attributes.get("name")
                                if name:
                                    allowed.add(name)
                                for child in e.children:
                                    collect_subtree_names(child)

                            collect_subtree_names(modal_element)
                            
                            self.elements_flat = [e for e in self.elements_flat if e in allowed_elements]
                            
                            if self.focus_element and self.focus_element not in self.elements_flat:
                                self.focus_element = None
                                self.focus_index = -1

                            # Filter clickable zones
                            self.clickable_zones = [z for z in self.clickable_zones if z[5] in allowed]

                            # Filter element coords
                            self.element_coords = [e for e in self.element_coords if e[4].attributes.get("name") in allowed]
                            
                        continue

                    # --- Normal element layout ---
                    if "x" in child.attributes and "y" in child.attributes:
                        layout_x, layout_y = self.downscale_resolution(
                            int(child.attributes["x"]), int(child.attributes["y"])
                        )
                    elif side == "top":
                        cursor_y += pady
                        layout_x = max(0, (self.computed_width - width) // 2) if tag in [
                            "label", "entry", "button",
                            "checkbutton", "radiobutton","optionmenu"
                        ] and "padx" not in child.attributes else cursor_x + padx
                        layout_y = cursor_y
                        cursor_y += height + pady
                    elif side == "bottom":
                        bottom_y -= height + pady
                        layout_x = max(0, (self.computed_width - width) // 2) if tag in [
                            "label", "entry", "button", 
                            "checkbutton", "radiobutton","optionmenu"
                        ] and "padx" not in child.attributes else x + padx
                        layout_y = bottom_y
                    elif side == "left":
                        layout_x = cursor_x
                        layout_y = y + (self.window_body_height - height) // 2
                        cursor_x += width + padx
                    elif side == "right":
                        right_x -= width + padx
                        layout_x = right_x
                        layout_y = y + (self.window_body_height - height) // 2
                    else:
                        cursor_y += pady
                        layout_x = x + padx
                        layout_y = cursor_y
                        cursor_y += height + pady

                    self.layout_map[child] = (layout_x, layout_y)

                    if is_focusable_tag(tag):
                        add_focusable(child, width, height)
                    
                    self.elements_flat.append(child)

                    end_x = layout_x + width
                    end_y = layout_y + height
                    max_width = max(max_width, end_x)
                    max_height = max(max_height, end_y)

                    layout_recursive(child, layout_x, layout_y)
                        
            layout_recursive(el, layout_offset_x, layout_offset_y)
            
            if self.active_modal_element:
                allowed = set()

                def collect_modal_subtree(el):
                    allowed.add(el)
                    for c in el.children:
                        collect_modal_subtree(c)

                collect_modal_subtree(self.active_modal_element)

                #self.elements_flat = [e for e in self.elements_flat if e in allowed]
                self.element_coords = [z for z in self.element_coords if z[4] in allowed]
                self.clickable_zones = [z for z in self.clickable_zones if z[6] in allowed]

        def draw_ui(self):
            self.screen.clear()
            self.element_coords = []
            self.clickable_zones.clear()
            self.canvas.clear()

            if self.app.options.get("show_title_bar", True):
                draw_exit = self.app.options.get("show_exit_button", True)
                highlight = (self.hover_element == "exit_button")
                self.draw_title_bar(draw_exit, hover=highlight)
                
            self.draw_background(color_bg=self.bg_color)
            
            self.compute_layout()
            
            
            #if self.focus_index is not None and self.focus_index < len(self.elements_flat):
            #    self.focus_element = self.elements_flat[self.focus_index]
            #else:
            #    self.focus_element = None
            
            self.canvas.setColorBG(self.bg_color)
            self.canvas.setColorFG(self.fg_color)            
            
            for el in self.elements_flat:
                if el.visibility in ("hidden", "collapsed"):                    
                    continue

                # walk up parents just to be safe
                parent = el.parent
                while parent:
                    if parent.visibility in ("hidden", "collapsed"):
                        break
                    parent = parent.parent                    
                
                x, y = self.layout_map.get(el, (0, 0))
                self.draw_elements_from(el, x, y)            
            
            self.draw_borders()

            self.canvas.flush(self.screen)
            self.screen.refresh()
            
        def draw_title_bar(self, show_exit, hover=False):
            self.canvas.setColorBG(227, 240, 236)
            self.canvas.setColorFG(0, 0, 0)
            w = self.computed_width
            title = self.app.options.get("title", "ezUI App")

            # Fill the title bar background
            for x in range(self.computed_width):
                self.canvas.draw_char(x, 0, ' ')

            # Draw title text
            self.canvas.text(1, 0, title)

            if show_exit:
                exit_label = "[X]"
                exit_x = self.computed_width - len(exit_label) - 1

                # Highlight effect if hovered
                if hover:
                    self.canvas.setColorBG(0, 0, 0)
                    self.canvas.setColorFG(227, 240, 236)
                else:
                    self.canvas.setColorBG(227, 240, 236)
                    self.canvas.setColorFG(0, 0, 0)
                    
                element = ezUI.Element("button", {"name": "sys_exit", "text": "exit"})

                self.canvas.text(exit_x, 0, exit_label)
                self.clickable_zones.append((
                    exit_x, 0, exit_x + len(exit_label) - 1, 0,
                    self.app.system(self.app).exit,
                    "exit_button",  # Identifier for hover matching
                    element
                ))
            
        def draw_background(self, color_bg=(30, 30, 30)):
            self.canvas.setColorBG(*color_bg)
            self.canvas.setColorFG(*color_bg)  # Use same FG to hide text artifacts
            start_y = 1 if self.app.options.get("show_title_bar", True) else 0
            self.canvas.fillbox(0, start_y, self.computed_width - 1, self.computed_height - 1)
                    
        def draw_elements_from(self, element, x, y, target=None):
            target = target or self.canvas
            if element.visibility in ("hidden", "collapsed"):
                return # skip entirely
                
            tag = element.tag.lower()
            if tag == "label":
                self.draw_label(element, x, y)
            elif tag == "entry":
                self.draw_entry(element, x, y)
            elif tag == "button":
                self.draw_button(element, x, y)
            elif tag == "checkbutton":
                self.draw_checkbutton(element, x, y)
            elif tag == "radiobutton":
                self.draw_radiobutton(element, x, y)
            elif tag == "frame":
                self.draw_frame(element, x, y)
            elif tag == "optionmenu":
                self.draw_optionmenu(element, x, y)
                    
        def draw_borders(self):
            title_offset = 1 if self.app.options.get("show_title_bar", True) else 0
            self.canvas.setColorBG(self.bg_color)
            self.canvas.setColorFG(self.fg_color)
            
            for y in range(title_offset,self.computed_height):                
                self.canvas.draw_char(0, y, '│')
                self.canvas.draw_char(self.computed_width - 1, y, '│')
        
            for x in range(self.computed_width):
                self.canvas.draw_char(x, self.computed_height - 1, '─')
                
            self.canvas.draw_char(0, self.computed_height - 1, '└')
            self.canvas.draw_char(self.computed_width - 1, self.computed_height - 1, '┘')
                    
        def draw_label(self, element, x, y, target=None):
            target = target or self.canvas
            bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), self.bg_color)
            fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), self.fg_color)
            target.setColorBG(*bg)
            target.setColorFG(*fg)
            
            text = ""
            if 'ezBind' in element.attributes:
                key = element.attributes['ezBind'].strip("()")
                text = self.app.data.get(key, '')
            elif 'text' in element.attributes:
                text = element.attributes['text']
                
            lines = text.split("\n")
                
            for i, line in enumerate(lines):
                target.text(x + 1, y + i, line)
                
            # self.element_coords.append((y, element))  # Optional: for mouse/focus and highlighting
            
            target.setColorFG(self.fg_color)
            target.setColorBG(self.bg_color)
            
        def draw_entry(self, element, x, y, target=None):
            target = target or self.canvas
            bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), "#ffffff")
            fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), "#000000")
            self.canvas.setColorBG(*bg)
            self.canvas.setColorFG(*fg)
            key = element.attributes.get("ezBind", "").strip("()")
            text = str(self.app.data.get(key, ""))
            max_length = int(element.attributes.get("width", 12))
            
            is_focus = (
                self.focus_element is not None and
                element.attributes.get("name") == self.focus_element.attributes.get("name")
            )

            cursor = self.cursor_pos if is_focus else len(text)
            if cursor > len(text):
                cursor = len(text)

            # Truncate text so cursor is always visible at far right
            if len(text) <= max_length:
                start = 0
                display_text = text.ljust(max_length)
            else:
                # Adjust window to keep cursor visible anywhere
                start = max(0, min(self.cursor_pos - max_length + 1, len(text) - max_length))
                end = start + max_length
                display_text = text[start:end].ljust(max_length)           

            cursor_screen_index = cursor - start if is_focus and start <= cursor <= start + max_length else -1

            for i, ch in enumerate(display_text):
                if i == cursor_screen_index and self.blink_state and is_focus:
                    if self.insert_mode:
                        target.setColorFG(255, 255, 255)
                        target.setColorBG(0, 0, 0)
                        target.draw_char(x + i, y, ch)
                    else:
                        target.setColorFG(0, 0, 0)
                        target.setColorBG(255, 255, 255)
                        target.draw_char(x + i, y, '_')
                else:
                    target.setColorFG(0, 0, 0)
                    target.setColorBG(255, 255, 255)
                    target.draw_char(x + i, y, ch)

            target.setColorFG(self.fg_color)
            target.setColorBG(self.bg_color)
            
        def draw_button(self, element, x, y, target=None):
            target = target or self.canvas
            text = element.attributes.get("text", "Button")
            is_hover = self.hover_element == element.attributes.get("name")
            is_focus = (
                self.focus_element is not None and
                element.attributes.get("name") == self.focus_element.attributes.get("name")
            )
            
            text_width = len(text)
            el_width = int(element.attributes.get("width","10"))
            space_len = 0 if el_width == (text_width + 4) else  (el_width - (text_width + 4))
            
            if space_len/2 != math.floor(space_len/2):
                space_len +=1
            
            space1 = " " * math.floor(space_len/2)
            space2 = space1

            label = "[ {}{}{} ]".format(space1,text,space2)
            
            if (len(label)/2) != math.floor(len(label)):
                space1 = " " * (math.floor(space_len/2)+1)
                label = "[ {}{}{} ]".format(space1,text,space2)
            
                       
            for i, ch in enumerate(label):
                if (i == 0 or i == len(label) - 1) and (is_hover or is_focus):
                    # Invert just the brackets on hover
                    target.setColorBG(100, 100, 100)   # darker
                    target.setColorFG(255, 255, 255)   # white text
                else:
                    # Default button style (light)
                    bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), "#cccccc")
                    fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), "#000000")
                    target.setColorBG(*bg)
                    target.setColorFG(*fg)

                target.draw_char(x + i, y, ch)

            target.setColorFG(self.fg_color)
            target.setColorBG(self.bg_color)

        def draw_checkbutton(self, element, x, y, target=None):
            target = target or self.canvas
            key = element.attributes.get("ezBind", "").strip("()")
            state = bool(self.app.data.get(key, False))
            label = element.attributes.get("text", "")
            box = "[x]" if state else "[ ]"
            full_label = "{} {}".format(box,label)
            is_hover = self.hover_element == element.attributes.get("name")
            is_focus = (
                self.focus_element is not None and
                element.attributes.get("name") == self.focus_element.attributes.get("name")
            )
            
            for i, ch in enumerate(full_label):
                if (ch == "[" or ch == "]") and (is_hover or is_focus):
                    # Invert just the brackets on hover
                    target.setColorBG(100, 100, 100)   # darker
                    target.setColorFG(255, 255, 255)   # white text
                else:
                    # Default button style (light)
                    bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), self.bg_color)
                    fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), self.fg_color)
                    target.setColorBG(*bg)
                    target.setColorFG(*fg)

                target.draw_char(x + i, y, ch)

            target.setColorFG(self.fg_color)
            target.setColorBG(self.bg_color)
            
        def draw_radiobutton(self, element, x, y, target=None):
            target = target or self.canvas
            key = element.attributes.get("ezBind", "").strip("()")
            value = element.attributes.get("value", "")
            current = self.app.data.get(key, "")
            state = (current == value)
            label = element.attributes.get("text", "")
            box = "(o)" if state else "( )"
            full_label = "{} {}".format(box, label)
            is_hover = self.hover_element == element.attributes.get("name")
            is_focus = (
                self.focus_element is not None and
                element.attributes.get("name") == self.focus_element.attributes.get("name")
            )

            for i, ch in enumerate(full_label):
                if (ch == "(" or ch == ")") and (is_hover or is_focus):
                    target.setColorBG(100, 100, 100)   # darker
                    target.setColorFG(255, 255, 255)   # white text
                else:
                    bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), self.bg_color)
                    fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), self.fg_color)
                    target.setColorBG(*bg)
                    target.setColorFG(*fg)

                target.draw_char(x + i, y, ch)

            target.setColorFG(self.fg_color)
            target.setColorBG(self.bg_color)
            
        def draw_optionmenu(self, element, x, y, target=None):
            target = target or self.canvas
            key = element.attributes.get("ezBind", "").strip("()")
            dropdown_data = self.app.data.get(key, {"options": [], "selected_index": 0})
            options = dropdown_data.get("options", [])
            selected_index = dropdown_data.get("selected_index", 0)
            labels = list(options.keys())

            # Dynamic width based on longest label + 4
            max_label_len = max((len(label) for label in labels), default=0)
            dropdown_width = max_label_len
            text = labels[selected_index]
            text_len = len(text)
            space_len = dropdown_width - text_len
            space = " " * space_len
            full_label = "{}{} [V]".format(text,space)
            is_hover = self.hover_element == element.attributes.get("name")
            is_focus = (
                self.focus_element is not None and
                element.attributes.get("name") == self.focus_element.attributes.get("name")
            )
            
            for i, ch in enumerate(full_label):
                if (ch == "[" or ch == "]") and (is_hover or is_focus):
                    bg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), "#000000")
                    fg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), "#cccccc")
                    target.setColorBG(*bg)
                    target.setColorFG(*fg)
                else:
                    bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), "#cccccc")
                    fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), "#000000")
                    target.setColorBG(*bg)
                    target.setColorFG(*fg)

                self.canvas.draw_char(x + i, y, ch)

            target.setColorFG(self.fg_color)
            target.setColorBG(self.bg_color)
            
        def draw_frame(self, element, x, y, target=None):
            target = target or self.canvas
            w = element.width
            h = element.height
            canvas = element.canvas
            canvas.clear()

            # Default to frame-specific background color if defined
            bg = self.parse_color(element.attributes.get("background") or element.attributes.get("bg"), self.bg_color)
            fg = self.parse_color(element.attributes.get("foreground") or element.attributes.get("fg"), self.fg_color)
            canvas.setColorBG(*bg)
            canvas.setColorFG(*fg)
                    
            canvas.fillbox(0, 0, w - 1, h - 1)  # fill background

            # Draw border if enabled
            if element.attributes.get("border", "false").lower() != "false":
                canvas.draw_char(0, 0, '┌')
                canvas.draw_char(w - 1, 0, '┐')
                canvas.draw_char(0, h - 1, '└')
                canvas.draw_char(w - 1, h - 1, '┘')
                for i in range(1, w - 1):
                    canvas.draw_char(i, 0, '─')
                    canvas.draw_char(i, h - 1, '─')
                for j in range(1, h - 1):
                    canvas.draw_char(0, j, '│')
                    canvas.draw_char(w - 1, j, '│')

            # Handle scrollLeft/scrollTop attributes
            scroll_x = int(element.attributes.get("scrollLeft", 0))
            scroll_y = int(element.attributes.get("scrollTop", 0))

            # Sanity: don't allow scrolling beyond canvas dimensions
            scroll_x = max(0, min(scroll_x, canvas.width - w))
            scroll_y = max(0, min(scroll_y, canvas.height - h))

            # Clipping logic
            overflow = element.attributes.get("overflow", "visible").lower()
            if overflow == "hidden":
                clip_x1 = scroll_x
                clip_y1 = scroll_y
                clip_x2 = scroll_x + w
                clip_y2 = scroll_y + h
            else:
                clip_x1 = clip_y1 = clip_x2 = clip_y2 = None

            # Flush to parent canvas (TUI root) with offset and optional clipping
            canvas.flush(
                target,
                start_x=x,
                start_y=y,
                clip_x1=clip_x1,
                clip_y1=clip_y1,
                clip_x2=clip_x2,
                clip_y2=clip_y2
            )
        
        def handle_input(self, key):
            #print(key)            
            prev_index = self.focus_index
            
            if key == 259:  # up arrow → move cursor to beginning                
                el = self.elements_flat[self.focus_index]
                tag = el.tag.lower()
                if tag in ("entry"):
                    keyname = el.attributes.get("ezBind", "").strip("()")
                    val = str(self.app.data.get(keyname, ""))
                    self.cursor_pos = 0                    
            elif key == 258:  # down arrow → move cursor to end
                el = self.elements_flat[self.focus_index]
                tag = el.tag.lower()
                if tag in ("entry"):
                    keyname = el.attributes.get("ezBind", "").strip("()")
                    val = str(self.app.data.get(keyname, ""))
                    self.cursor_pos = len(val)
            elif key == 260: # left arrow
                el = self.elements_flat[self.focus_index]
                tag = el.tag.lower()
                if tag in ("entry"):
                    self.cursor_pos = max(0, self.cursor_pos - 1)
            elif key == 261: # right arrow
                el = self.elements_flat[self.focus_index]                
                tag = el.tag.lower()
                if tag in ("entry"):
                    keyname = el.attributes.get("ezBind", "").strip("()")
                    val = str(self.app.data.get(keyname, ""))
                    self.cursor_pos = min(len(val), self.cursor_pos + 1)
            elif key in [cu.KEY_ENTER, 10, 13]:
                el = self.elements_flat[self.focus_index]
                tag = el.tag.lower()
                if tag in ("button"):
                    self.activate_current()
                elif tag in ("textbox"):
                    keyname = el.attributes.get("ezBind", "").strip("()")
                    val = str(self.app.data.get(keyname, ""))
                    self.app.data.update(keyname, "{}\n".format(val))
            elif key in range(32, 127):  # Printable characters
                el = self.elements_flat[self.focus_index]                
                tag = el.tag.lower()
                if tag in ("entry","textbox"):
                    self.update_text(chr(key))
            elif key  == 8: # Backspace key
                el = self.elements_flat[self.focus_index]                
                tag = el.tag.lower()
                if tag in ("entry","textbox"):
                    self.backspace_text()            
            elif key == 330:  # Delete key
                el = self.elements_flat[self.focus_index]                
                tag = el.tag.lower()
                if tag in ("entry","textbox"):
                    self.delete_text()
            elif key == 331:  # Insert key
                el = self.elements_flat[self.focus_index]                
                tag = el.tag.lower()
                if tag in ("entry","textbox"):
                    self.insert_mode = not self.insert_mode
                
            if self.focus_index != prev_index:
                el = self.elements_flat[self.focus_index]
                tag = el.tag.lower()
                if tag in ("entry","textbox"):
                    keyname = el.attributes.get("ezBind", "").strip("()")
                    val = str(self.app.data.get(keyname, ""))
                    self.cursor_pos = len(val)

        def activate_current(self, el, handler=None):            
            tag = el.tag.lower()
            handler_name = el.attributes.get("ezClick", "")         
            
            if tag in ("button","optionmenu"):
                handler = self.app.data.get(handler_name) if handler_name != "" else handler
                if handler and handler_name != "":
                    handler(el, self.system, self.app.data)
                else:
                    #must be sys exit or dropdown
                    handler()
            elif tag == "checkbutton":
                key = el.attributes.get("ezBind", "").strip("()")
                current = self.app.data.data.get(key, False)
                self.app.data.update(key, not current)
            elif tag == "radiobutton":
                key = el.attributes.get("ezBind", "").strip("()")
                value = el.attributes.get("value", "")
                self.app.data.update(key, value)
            

        def update_text(self, char):
            el = self.elements_flat[self.focus_index]
            if el.tag.lower() == "entry":
                key = el.attributes.get("ezBind", "").strip("()")
                val = str(self.app.data.get(key, ""))
                if self.insert_mode and self.cursor_pos < len(val):
                    new = val[:self.cursor_pos] + char + val[self.cursor_pos+1:]
                else:
                    new = val[:self.cursor_pos] + char + val[self.cursor_pos:]
                self.cursor_pos += 1
                self.app.data.update(key, new)

        def backspace_text(self):
            el = self.elements_flat[self.focus_index]
            tag = el.tag.lower()
            if tag in ("entry","textbox"):
                key = el.attributes.get("ezBind", "").strip("()")
                val = str(self.app.data.get(key, ""))
                if self.cursor_pos > 0:
                    new = val[:self.cursor_pos - 1] + val[self.cursor_pos:]
                    self.cursor_pos -= 1
                    self.app.data.update(key, new)
                    
        def delete_text(self):
            el = self.elements_flat[self.focus_index]                
            tag = el.tag.lower()
            if tag in ("entry","textbox"):
                keyname = el.attributes.get("ezBind", "").strip("()")
                val = str(self.app.data.get(keyname, ""))                    
                if self.cursor_pos < len(val):
                    new = val[:self.cursor_pos] + val[self.cursor_pos+1:]
                    self.app.data.update(keyname, new)
        
        def handle_mouse(self):
            if self.dropdown_guard:
                return  # Block input for one frame after dropdown opens
                
            # Block clicks outside modal dropdown and auto-close if modal="clear"
            if self.active_modal_element and self.mouse_left:
                modal_type = self.active_modal_element.attributes.get("ezModal", "none").lower()
                if modal_type in ("clear", "opaque"):
                    # Get modal layout area
                    bounds = self.layout_map.get(self.active_modal_element)
                    if bounds:
                        modal_x, modal_y = bounds
                        modal_w = self.active_modal_element.width
                        modal_h = self.active_modal_element.height
                        inside_modal = (
                            modal_x <= self.mouse_x < modal_x + modal_w and
                            modal_y <= self.mouse_y < modal_y + modal_h
                        )
                        if not inside_modal:
                            print("Clicked outside modal — closing dropdown")
                            self.active_dropdown = None
                            self.active_modal_element.attributes["visibility"] = "collapsed"
                            self.active_modal_element.visibility = "collapsed"
                            self.active_modal_element = None
                            self.modal_root_name = None
                            self.queue = None
                            self.compute_layout()
                            return  # Block further interaction

            click_happened = self.mouse_left or self.mouse_right
            mx, my = self.mouse_x, self.mouse_y

            # -----------------------------------------
            # Dropdown modal logic
            # -----------------------------------------
            if self.active_dropdown:
                dropdown_name = self.active_dropdown
                dropdown_frame_name = f"{dropdown_name}_dropdown"
                self.modal_clickable_zones = []

                clicked_inside = False

                # Restrict interaction to dropdown + its options
                for zone in self.clickable_zones:
                    x1, y1, x2, y2, handler, name, el = zone
                    if name == dropdown_name or name.startswith(dropdown_frame_name):
                        self.modal_clickable_zones.append(zone)
                        if x1 <= mx <= x2 and y1 == my:
                            clicked_inside = True
                            if click_happened:
                                self.queue = {
                                    "action": "MouseLeft" if self.mouse_left else "MouseRight",
                                    "element": el,
                                    "handler": el.attributes.get("ezClick"),
                                    "zone": (x1, y1, x2, y2),
                                    "name": name
                                }
                                self._close_dropdown_next_frame = True
                            break

                # Click outside dropdown — close it
                if not clicked_inside and click_happened:
                    dropdown = self.system.get_element_by_name(dropdown_frame_name)
                    if dropdown:
                        dropdown.attributes["visibility"] = "collapsed"
                        dropdown.visibility = "collapsed"
                    self.active_dropdown = None
                    self.queue = None
                    self.compute_layout()
                return  # Fully block anything outside

            # -----------------------------------------
            # Normal interaction if no active modal
            # -----------------------------------------
            self.modal_clickable_zones = self.clickable_zones
            
            # Handle modal outside-click close
            if self.active_modal_element:
                mx, my = self.mouse_x, self.mouse_y
                modal_x, modal_y = self.layout_map.get(self.active_modal_element, (None, None))
                if modal_x is not None:
                    modal_w = self.active_modal_element.width
                    modal_h = self.active_modal_element.height

                    inside_modal = (
                        modal_x <= mx < modal_x + modal_w and
                        modal_y <= my < modal_y + modal_h
                    )

                    if not inside_modal and (self.mouse_left or self.mouse_right):
                        modal_type = self.active_modal_element.attributes.get("ezModal", "").lower()
                        if modal_type == "clear" and self.active_dropdown:
                            # Close dropdown if click is outside
                            dropdown = self.system.get_element_by_name(self.active_dropdown + "_dropdown")
                            if dropdown:
                                dropdown.attributes["visibility"] = "collapsed"
                                dropdown.visibility = "collapsed"
                            self.active_dropdown = None
                            self.active_modal_element = None
                            self.modal_root_name = None
                            self.queue = None
                            self.compute_layout()
                        return  # Block any further interaction

            if click_happened:                
                # Mouse down – identify which zone is clicked
                for x1, y1, x2, y2, handler, name, el in self.modal_clickable_zones:
                    if x1 <= self.mouse_x <= x2 and y1 == self.mouse_y:
                        action = "MouseRight" if self.mouse_right else "MouseLeft"
                        self.queue = {
                            "action": action,
                            "element": el,
                            "handler": handler,
                            "zone": (x1, y1, x2, y2),
                            "name": name
                        }

                        # Visual focus
                        tag = el.tag.lower()
                        if tag in ["button", "checkbutton", "radiobutton", "optionmenu"]:
                            self.last_focus_index = self.focus_index
                            try:
                                self.focus_index = self.elements_flat.index(el)
                            except ValueError:
                                self.focus_index = None
                            self.focus_element = el
                        return
            else:
                # Mouse up – finalize any queued interaction
                if self.queue:
                    if self.active_dropdown:
                        # Only allow processing if the queued name is in modal zones
                        allowed = False
                        for _, _, _, _, _, name, _ in self.modal_clickable_zones:
                            if self.queue["name"] == name:
                                allowed = True
                                break
                        if not allowed:
                            self.queue = None
                            return
                            
                    action = self.queue["action"]
                    el = self.queue["element"]
                    handler = self.queue["handler"]
                    x1, y1, x2, y2 = self.queue["zone"]

                    if x1 <= self.mouse_x <= x2 and y1 == self.mouse_y and action == "MouseLeft":
                        tag = el.tag.lower()
                        if tag in ["button", "checkbutton", "radiobutton", "optionmenu"]:
                            self.activate_current(el, handler)

                    self.queue = None                    
            
            # Focus logic for entry clicks
            for i, (x1, y1, x2, y2, el) in reversed(list(enumerate(self.element_coords))):
                if el not in self.elements_flat:
                    continue
                if x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2:
                    if self.mouse_left:
                        tag = el.tag.lower()
                        self.last_focus_index = self.focus_index
                        self.focus_index = i + 1
                        self.focus_element = el

                        if tag == "entry":
                            max_length = int(el.attributes.get("width", 12))
                            keyname = el.attributes.get("ezBind", "").strip("()")
                            val = str(self.app.data.get(keyname, ""))
                            total_len = len(val)

                            start = 0
                            if total_len > max_length:
                                start = max(0, min(self.cursor_pos - max_length + 1, total_len - max_length))

                            click_offset = self.mouse_x - x1
                            click_offset = max(0, min(click_offset, max_length - 1))
                            self.cursor_pos = min(start + click_offset, total_len)
                    break
                
        def cleanup(self):
            cu.nocbreak()
            self.screen.keypad(False)
            cu.echo()
            cu.endwin()
                
    
    class Canvas:
        class mode:
            PIXEL = 0
            CP437 = 1

        def __init__(self, width, height, render_mode=0, fg=(255, 255, 255), bg=(0, 0, 0)):
            self.width = width
            self.height = height
            self.render_mode = render_mode
            self.color_fg = fg
            self.color_bg = bg
            self._color_cache = {}
            self._pair_id = 2
            if self.render_mode == self.mode.CP437:
                self.buffer = [[(" ", self.color_fg, self.color_bg) for _ in range(width)] for _ in range(height)]
            else:
                self.buffer = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]

        def set(self, x, y, color):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.buffer[y][x] = color

        def clear(self, fg=(255, 255, 255), bg=(0, 0, 0)):
            temp_fg = self.color_fg
            temp_bg = self.color_bg
            self.color_fg = fg
            self.color_bg = bg
            for x in range(self.width):
                for y in range(self.height):
                    if self.render_mode == self.mode.CP437:
                        self.draw_char(x,y,' ')
                    else:
                        self.buffer = [[(0, 0, 0) for _ in range(self.width)] for _ in range(self.height)]

            self.color_fg = temp_fg
            self.color_bg = temp_bg
            
        def setColorFG(self, r, g=None, b=None):
            if isinstance(r, tuple) and len(r) == 3:
                self.color_fg = r
            elif all(isinstance(v, int) for v in (r, g, b)):
                self.color_fg = (r, g, b)
            else:
                raise ValueError("Invalid FG color: {}, {}, {}".format(r,g,b))

        def setColorBG(self, r, g=None, b=None):
            if isinstance(r, tuple) and len(r) == 3:
                self.color_bg = r
            elif all(isinstance(v, int) for v in (r, g, b)):
                self.color_bg = (r, g, b)
            else:
                raise ValueError("Invalid BG color: {}, {}, {}".format(r,g,b))

        def draw_char(self, x, y, ch):
            if 0 <= x < self.width and 0 <= y < self.height and self.render_mode == self.mode.CP437:
                self.buffer[y][x] = (ch, self.color_fg, self.color_bg)

        def put(self, x, y, char):
            if y * 2 + 1 < self.height:
                self.set(x, y * 2, self.color_fg)
                self.set(x, y * 2 + 1, self.color_bg)

        def text(self, x, y, string):
            for i, ch in enumerate(string):
                if self.render_mode == self.mode.CP437:
                    self.draw_char(x + i, y, ch)
                else:
                    self.draw_cp437_char_to_pixel(x + i, y, ch, self.color_fg, self.color_bg)

        def draw_cp437_char_to_pixel(self, x, y, ch, fg, bg):
            if ch == '█':
                self.set(x, y * 2, fg)
                self.set(x, y * 2 + 1, fg)
            elif ch == '▀':
                self.set(x, y * 2, fg)
                self.set(x, y * 2 + 1, (0, 0, 0))
            elif ch == '▄':
                self.set(x, y * 2, (0, 0, 0))
                self.set(x, y * 2 + 1, fg)
            else:
                self.set(x, y * 2, bg)
                self.set(x, y * 2 + 1, bg)

        def hline(self, x1, x2, y):
            self.line(x1, y, x2, y)

        def vline(self, x, y1, y2):
            self.line(x, y1, x, y2)

        def line(self, x1, y1, x2, y2):
            for (x, y) in self.calculate_line(x1, y1, x2, y2):
                self.set(x, y, self.color_fg)

        def box(self, x1, y1, x2, y2):
            self.hline(x1, x2, y1)
            self.hline(x1, x2, y2)
            self.vline(x1, y1, y2)
            self.vline(x2, y1, y2)

        def fillbox(self, x1, y1, x2, y2, ch=' '):
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    self.draw_char(x, y, ch)

        def rgb_to_ansi256(self, r, g, b):
            r = int(round(r / 51))
            g = int(round(g / 51))
            b = int(round(b / 51))
            return 16 + (36 * r) + (6 * g) + b

        def get_color_pair(self, stdscr, fg, bg):
            key = (fg, bg)
            if key in self._color_cache:
                return self._color_cache[key]

            if self._pair_id >= cu.COLOR_PAIRS:
                return 1

            try:
                fg_code = self.rgb_to_ansi256(*fg)
                bg_code = self.rgb_to_ansi256(*bg)
                cu.init_pair(self._pair_id, fg_code, bg_code)
                self._color_cache[key] = self._pair_id
                self._pair_id += 1
                return self._color_cache[key]
            except cu.error:
                return 1

        def flush(self, target, start_x=0, start_y=0, clip_x1=None, clip_y1=None, clip_x2=None, clip_y2=None):
            clip = all(v is not None for v in (clip_x1, clip_y1, clip_x2, clip_y2))
            offset_x = clip_x1 if clip else 0
            offset_y = clip_y1 if clip else 0

            if type(target) is type(self):
                for y in range(self.height):
                    if clip and not (clip_y1 <= y < clip_y2):
                        continue
                    for x in range(self.width):
                        if clip and not (clip_x1 <= x < clip_x2):
                            continue
                        dst_x = start_x + (x - offset_x)
                        dst_y = start_y + (y - offset_y)

                        if self.render_mode == target.render_mode:                           
                            if 0 <= dst_y < len(target.buffer) and 0 <= dst_x < len(target.buffer[0]):
                                target.buffer[dst_y][dst_x] = self.buffer[y][x]

                        elif self.render_mode == self.mode.PIXEL and target.render_mode == self.mode.CP437:
                            if y % 2 == 0 and y + 1 < self.height:
                                top = self.buffer[y][x]
                                bottom = self.buffer[y + 1][x]
                                ch = ' '
                                fg, bg = (255, 255, 255), (0, 0, 0)
                                if top == bottom and top != (0, 0, 0):
                                    ch = '█'
                                    fg = top
                                    bg = top
                                elif top != (0, 0, 0) and bottom != (0, 0, 0):
                                    ch = '█'
                                    fg = top
                                    bg = bottom
                                elif top != (0, 0, 0):
                                    ch = '▀'
                                    fg = top
                                    bg = (0, 0, 0)
                                elif bottom != (0, 0, 0):
                                    ch = '▄'
                                    fg = (0, 0, 0)
                                    bg = bottom
                                target.buffer[dst_y // 2][dst_x] = (ch, fg, bg)

                        elif self.render_mode == self.mode.CP437 and target.render_mode == self.mode.PIXEL:
                            ch, fg, bg = self.buffer[y][x]
                            target.draw_cp437_char_to_pixel(dst_x, dst_y, ch, fg, bg)

            else:
                stdscr = target
                if self.render_mode == self.mode.CP437:
                    for y in range(self.height):
                        if clip and not (clip_y1 <= y < clip_y2):
                            continue
                        for x in range(self.width):
                            if clip and not (clip_x1 <= x < clip_x2):
                                continue
                            ch, fg, bg = self.buffer[y][x]
                            pair_id = self.get_color_pair(stdscr, fg, bg)
                            try:
                                stdscr.attron(cu.color_pair(pair_id))
                                stdscr.addch(start_y + (y - offset_y), start_x + (x - offset_x), ch)
                                stdscr.attroff(cu.color_pair(pair_id))
                            except cu.error:
                                pass
                else:
                    rows = self.height // 2
                    for row in range(rows):
                        for col in range(self.width):
                            y_screen = start_y + row
                            x_screen = start_x + col
                            if clip and not (clip_y1 <= row * 2 < clip_y2 and clip_x1 <= col < clip_x2):
                                continue
                            top = self.buffer[row * 2][col]
                            bottom = self.buffer[row * 2 + 1][col] if (row * 2 + 1) < self.height else (0, 0, 0)

                            if top == bottom and top != (0, 0, 0):
                                ch = '█'
                                fg = top
                                bg = top
                            elif top != (0, 0, 0) and bottom != (0, 0, 0):
                                ch = '█'
                                fg = top
                                bg = bottom
                            elif top != (0, 0, 0):
                                ch = '▀'
                                fg = top
                                bg = (0, 0, 0)
                            elif bottom != (0, 0, 0):
                                ch = '▄'
                                fg = (0, 0, 0)
                                bg = bottom
                            else:
                                ch = ' '
                                fg = (255, 255, 255)
                                bg = (0, 0, 0)

                            pair_id = self.get_color_pair(stdscr, fg, bg)
                            try:
                                stdscr.attron(cu.color_pair(pair_id))
                                stdscr.addch(y_screen, x_screen, ch)
                                stdscr.attroff(cu.color_pair(pair_id))
                            except cu.error:
                                pass

        def show_cursor(self):
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

        @staticmethod
        def calculate_line(x1, y1, x2, y2):
            points = []
            dx = abs(x2 - x1)
            dy = -abs(y2 - y1)
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            err = dx + dy
            x, y = x1, y1
            while True:
                points.append((x, y))
                if x == x2 and y == y2:
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    x += sx
                if e2 <= dx:
                    err += dx
                    y += sy
            return points
            
    # Entry point
    @staticmethod
    def start_ui(root, data_model, mode=0, options=None, user_function=None, user_loop=None):
        options = options or ezUI.Options()
        if mode == ezUI.mode.GUI:
            ezUI.GUI(root, data_model, options, user_function)
        elif mode == ezUI.mode.TUI:
            if cu is None:
                raise RuntimeError("TUI mode not available on Windows. Install windows-curses or use GUI mode.")
            tui = ezUI.TUI(root, data_model, options, user_function)
        else:
            raise ValueError("Unknown mode: use ezUI.mode.GUI or ezUI.mode.TUI")
            
if __name__ == "__main__":
    import sys
    if "--version" in sys.argv:
        print("Version: {}".format(ezUI.VERSION))
        sys.exit(0)
    
    print("This module is meant to be imported, not run directly.")
