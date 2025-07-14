#!/usr/bin/env python3

import sys
from ezUI import ezUI

def test_ui(mode):
    root_element = ezUI.Element("window")
    frame = ezUI.Element("frame")
    frame.add_child(ezUI.Element("label", {"text": "Top Center Label", "pack": "top"}))
    frame.add_child(ezUI.Element("entry", {"name": "incrementer", "ezBind": "(test_key)", "pack": "top"}))
    frame.add_child(ezUI.Element("label", {"text": "Left\nLabel", "pack": "left"}))
    frame.add_child(ezUI.Element("label", {"text": "Right Label", "pack": "right"}))
    frame.add_child(ezUI.Element("button", {"name": "increment", "text": "Click Me", "ezClick": "test_handler", "x": "24", "y": "32"}))
    frame.add_child(ezUI.Element("checkbutton", {"name": "Check Me", "text": "Check Me", "ezBind": "(test_check)", "pack": "top"}))
    frame.add_child(ezUI.Element("radiobutton", {"name": "Option 1", "text": "Option 1", "value": "1", "ezBind": "(test_radio)", "pack": "top"}))
    frame.add_child(ezUI.Element("radiobutton", {"name": "Option 2", "text": "Option 2", "value": "2", "ezBind": "(test_radio)", "pack": "top"}))
    frame.add_child(ezUI.Element("button", {"name": "exit", "text": "Exit", "ezClick": "exit_handler", "pack": "bottom"}))
    frame.add_child(ezUI.Element("optionmenu", {"name": "test_option_menu", "ezBind": "test_option_menu", "pack": "bottom"}))
    root_element.add_child(frame)

    data_model = ezUI.DataModel()
    data_model.bind("test_key", 100)
    data_model.bind("test_check", False)
    data_model.bind("test_radio", "1")
    data_model.bind("test_option_menu", {"options": {"Drop Me": False, "Option 1": True, "--------------": False, "Option 2": True,}, "selected_index": 0})

    def test_handler(element, system, data):
        value = int(data.get("test_key")) + 1
        data.update("test_key", value)

    def exit_handler(element, system, data):
        system.exit()

    data_model.bind("test_handler", test_handler)
    data_model.bind("exit_handler", exit_handler)

    def user_func(system, data):
        print("UI is running...")

    options = ezUI.Options({
        "title": "ezUi Test",
        "show_title_bar": True,
        "show_exit_button": True,
        "full_screen": True,
        "window_width": 400,
        "window_height": 200
    })

    ezUI.start_ui(root_element, data_model, mode=mode, options=options, user_function=user_func)

if __name__ == "__main__":
    if "--tui" in sys.argv:
        test_ui(ezUI.mode.TUI)
    elif "--gui" in sys.argv:
        test_ui(ezUI.mode.GUI)
    else:
        print("Please use uiTest.py --gui to test the GUI and uiTest.py --tui to test the TUI")