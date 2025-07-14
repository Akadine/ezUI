ezUI - Unified Python GUI/TUI Framework
=======================================

ezUI is a lightweight, markup-driven UI framework for Python inspired by XAML and AngularJS-style data binding. It allows developers to build declarative UI structures with two-way data binding and a consistent model across both GUI (Tkinter) and TUI (Curses-style) modes.

Unlike raw HTML or Tkinter, ezUI requires a minimal but structured understanding of widget tags and attributes, similar to XAML markup or AngularJS templates—but with enhanced dropdown support and reactive control via simple Python dictionaries.

-------------------------------------------------------------------------------
Part 1 - Basic Usage
-------------------------------------------------------------------------------

Step 1: Define Your UI Structure and options
--------------------------------
You build your UI using ezUI.Element objects, this is based on tkinter names and HTML format, and will be passed mostly straight through.
There are a few custom attributes whitch are parsed and stript before sending to tkinter.

    from ezui import ezUI

    root_element = ezUI.Element("window")
    frame = ezUI.Element("frame")
    frame.add_child(ezUI.Element("label", {"name": "label", "text": "Enter Name:"}))
    frame.add_child(ezUI.Element("entry", {"ezBind": "(username)", "name": "name"}))
    frame.add_child(ezUI.Element("button", {
        "text": "Submit",
		name: "Submit",
        "ezClick": "handle_submit"
    }))
	root_element.add_child(frame)
	
You can specify app options here to make it easy. For example, tkinter shows no title bar full screen. 
If you specify both full_screen and show_title bar here, a custom title bar will automatically be built by ezUI.

	options = ezUI.Options({
        "title": "ezUi Test",
        "full_screen": True,
        "window_width": 400,
        "window_height": 200
    })
	
These are the default options. You can omit these in your options and the defaulst will be used.

	DEFAULTS = {
		"show_title_bar": True,
		"show_exit_button": True,
		"title": "ezUI App",
		"full_screen" : False,
		"window_width": 800,
		"window_height": 600
	}

Step 2: Define Your Data Model
Note: You need only define click handlers and bound data here, you can add other data later in the user_function
------------------------------

    data_model = ezUI.DataModel()
	
	#add data
    data_model.bind("username", "")
	
	#for ezClick handlers:
	def handle_submit(self, system, data):
		system.get_element_by_name("label").text = "Hello, {}".format(data.get("username"))
		
	data_model.bind("handle_sumbit", handle_submit)

Step 3: Launch the UI
---------------------
    
    #optional
	#pre set up initialization
	def my_func(system,data):
		#do something with the elements
		el = system.get_element_by_name("nameInput")
		#change data
		date.bind("new_key", new_value)
		data.update("usename", "Joe")
	#animation loop, this is ran on every gui draw frame
	def my_loop(system,data):
		label = system.get_element_by_name("label")
		name = data.get("username")
		
    ezUI.start_ui(root_element, data_model, mode=mode, options=options, user_function=my_func, user_loop=my_loop)
	
	^^Here mode is either ezUI.mode.GUI or ezUI.mode.TUI. see uiTest for more.

-------------------------------------------------------------------------------
Part 2 - GUI Mode (Tkinter)
-------------------------------------------------------------------------------

Supported Elements:
-------------------

  Tag            | Description
  ---------------|-------------------------------------------------------------
  window         | Root container (must be present)
  label          | Static or bound label text (ezBind="(key)")
  entry          | Single-line input, bound to string
  textbox        | Multi-line input, bound via <KeyRelease>
  button         | Triggers method (ezClick="handlerName")
  checkbutton    | Boolean True/False, bound via ezBind
  radiobutton    | Multiple exclusive options, same ezBind key + unique value
  optionmenu     | Dropdown with special binding, False sets it to disabled, so you can have a place holder or group segrgation:
                 |   data.bind("test_option_menu", {"options": {"Drop Me": False, "Option 1": True, "--------": False, "Option 2": True,}, "selected_index": 0})

Binding Notes:
--------------

set up data model with: 

- Use `ezBind="(key)"` to bind a field from your data model.
- For dropdowns (`optionmenu`), the key must point to an object with:
    - "options": a list of strings
    - "index": the currently selected option index

- Checkbuttons bind to a boolean value (`True`/`False`)
- Radiobuttons bind to a shared string, each with its own `value`

Event Handling:
---------------

- Assign `ezClick="handler_name"` to a button.
- The handler is a method in your data model class.
- It receives `(sender_element, system, data)` as parameters.

Named Elements:
---------------

- Any element can include a `name="myElement"` attribute.
- Use `system.get_element_by_name("myElement")` to access it in user_function or click handlers.
  (TUI will support the same system)

-------------------------------------------------------------------------------
Part 3 - TUI Mode 
-------------------------------------------------------------------------------

The TUI version of ezUI runs in console using the same virtual DOM and data model as the GUI version. You can run the same app either way.

This allows you to build one application that can render in either a modern GUI window or an old-school text-based interface with mouse and keyboard support.

Implemented so far:

Traversing the virual dom, fully fucntional pack layout system mirroring the TKinter GUI:
Respects the top, left, padx, pady set. Automatically computes (x, y) coordinates for each widget in layout_map.

Supports: label, entry, button, checkbutton, and radiobutton.
Reactive data for those.

Keyboard support: arrow keys to change active control, enter to select or toggle  << broken for now
typing goes into focused control, backspace support

Mouse support: fully implemented as expected, no right click "context" menu.

Shared system Object:
TUI uses the same UIApp.system API as GUI

Todo: multiline textboxes, polish dropdowns.

-------------------------------------------------------------------------------
Notes:
-------------------------------------------------------------------------------

- Inspired by XAML and AngularJS-style reactive UIs.
- Dropdowns use a special object with `options` and `index` to support dynamic data sources.
- GUI is fully functional now; TUI half done
- Use `user_function` in `start_ui(...)` for final setup (e.g., set up initial data, start a asych loop and animate, and more!)

