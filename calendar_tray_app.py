import tkinter as tk
import calendar
import json
from datetime import date, timedelta
from pathlib import Path
import threading
import queue

from PIL import Image, ImageDraw, ImageFont
import pystray

# ************************************************************* SETTINGS

APP_DIR = (
    Path.home()
    / "AppData"
    / "Local"
    / "DayCalendar"
)

JSON_FILE = APP_DIR / "day_values.json"
IMAGE_FILE = APP_DIR / "weekly_calendar.png"

# ************************************************************* GLOBAL VARIABLES

root = None
tray_icon = None

# Communication between the pystray thread and Tkinter thread.
command_queue = queue.Queue()

# Stores:
#
# date object -> "1", "2", "3"
#
# Blank days are not stored.
day_values = {}

# The calendar window, if open.
calendar_window = None

# ************************************************************* COLORS

HEADER_COLOR = "#2F5597"
SELECTED_COLOR = "#FFF2CC"
TODAY_COLOR_SELECT = "#D9EAF7"
TODAY_COLOR_OUTPUT = "#FFFFFF"
OTHER_DAY_COLOR_OUTPUT = "#FFFFFF"

# ************************************************************* FONT

def get_font(size, bold=False):

    if bold:
        fonts = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
        ]
    else:
        fonts = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]

    for filename in fonts:

        if Path(filename).exists():

            return ImageFont.truetype(
                filename,
                size
            )

    return ImageFont.load_default()

# ************************************************************* CREATE EMPTY JSON FILE IF NEEDED

def create_empty_json_if_needed():

    APP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not JSON_FILE.exists():

        with open(
            JSON_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {},
                file,
                indent=4
            )

# ************************************************************* LOAD JSON FILE

def load_day_values():

    global day_values

    day_values = {}

    create_empty_json_if_needed()

    try:

        with open(
            JSON_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):
            return

        for date_string, value in data.items():

            try:

                saved_date = date.fromisoformat(
                    date_string
                )

            except ValueError:
                continue

            if value in ("1", "2", "3"):

                day_values[saved_date] = value

    except (
        OSError,
        json.JSONDecodeError
    ):

        # If the JSON is damaged, don't crash.
        day_values = {}

# ************************************************************* SAVE JSON FILE

def save_day_values():

    APP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    data = {}

    for selected_date, value in day_values.items():

        if value in ("1", "2", "3"):

            data[
                selected_date.isoformat()
            ] = value

    try:

        with open(
            JSON_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    except OSError as error:

        print(
            "Error saving JSON:",
            error
        )

# ************************************************************* CREATE IMAGE FILE

def create_weekly_image():

    today = date.today()

    # Sunday of this week.
    sunday = (
        today
        - timedelta(days=today.weekday() + 1)
    )

    # 14 days = this week + next week.
    days = [
        sunday + timedelta(days=i)
        for i in range(14)
    ]

    width = 1400

    title_height = 70
    header_height = 80
    row_height = 140

    height = (
        title_height
        + header_height
        + row_height * 2
    )

    image = Image.new(
        "RGB",
        (width, height),
        "white"
    )

    draw = ImageDraw.Draw(image)

    title_font = get_font(
        36,
        bold=True
    )

    day_font = get_font(
        25,
        bold=True
    )

    date_font = get_font(25)

    value_font = get_font(
        65,
        bold=True
    )

# ************************************************************* MAKE THE TILE OF THE IMAGE

    title = "My Upcoming Approximate Schedule"

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    title_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (width - title_width) / 2,
            15
        ),
        title,
        fill="black",
        font=title_font
    )

# ************************************************************* MAKE THE TOP OF THE IMAGE

    column_width = width // 7

    day_names = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]

    for col, name in enumerate(day_names):

        x1 = col * column_width
        x2 = x1 + column_width

        draw.rectangle(
            [
                x1,
                title_height,
                x2,
                title_height + header_height
            ],
            fill=HEADER_COLOR,
            outline="white",
            width=2
        )

        bbox = draw.textbbox(
            (0, 0),
            name,
            font=day_font
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        text_height = (
            bbox[3] - bbox[1]
        )

        draw.text(
            (
                x1
                + (column_width - text_width) / 2,

                title_height
                + (header_height - text_height) / 2
            ),
            name,
            fill="white",
            font=day_font
        )

# ************************************************************* FILL IN THE CALENDAR

    for row in range(2):

        for col in range(7):

            current_date = days[
                row * 7 + col
            ]

            x1 = col * column_width
            x2 = x1 + column_width

            y1 = (
                title_height
                + header_height
                + row * row_height
            )

            y2 = y1 + row_height

            if current_date == today:

                background = TODAY_COLOR_OUTPUT

            else:

                background = OTHER_DAY_COLOR_OUTPUT

            draw.rectangle(
                [
                    x1,
                    y1,
                    x2,
                    y2
                ],
                fill=background,
                outline="black",
                width=2
            )

            # Date
            date_text = current_date.strftime(
                "%b %d"
            )

            bbox = draw.textbbox(
                (0, 0),
                date_text,
                font=date_font
            )

            date_width = (
                bbox[2] - bbox[0]
            )

            draw.text(
                (
                    x1
                    + (column_width - date_width) / 2,
                    y1 + 12
                ),
                date_text,
                fill="black",
                font=date_font
            )

            # Value
            value = day_values.get(
                current_date,
                ""
            )

            if value:

                bbox = draw.textbbox(
                    (0, 0),
                    value,
                    font=value_font
                )

                value_width = (
                    bbox[2] - bbox[0]
                )

                draw.text(
                    (
                        x1
                        + (column_width - value_width) / 2,
                        y1 + 55
                    ),
                    value,
                    fill="black",
                    font=value_font
                )

# ************************************************************* SAVE THE IMAGE FILE

    APP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    image.save(
        IMAGE_FILE,
        "PNG"
    )

# ************************************************************* CALENDAR INPUT

def show_calendar():

    global calendar_window

    # Already open?
    if (
        calendar_window is not None
        and calendar_window.winfo_exists()
    ):

        calendar_window.deiconify()
        calendar_window.lift()
        calendar_window.focus_force()

        return

    today = date.today()

    # This month
    year1 = today.year
    month1 = today.month

    # Next month
    if month1 == 12:

        year2 = year1 + 1
        month2 = 1

    else:

        year2 = year1
        month2 = month1 + 1

# ************************************************************* CALENDAR INPUT WINDOW

    calendar_window = tk.Toplevel(root)

    calendar_window.title(
        "Day Calendar"
    )

    calendar_window.resizable(
        False,
        False
    )

    calendar_window.protocol(
        "WM_DELETE_WINDOW",
        hide_calendar
    )

# ************************************************************* CREATE CALENDAR INPUT WINDOW OVERHEAD

    title = tk.Label(
        calendar_window,
        text="Day Calendar",
        font=("Segoe UI", 16, "bold")
    )

    title.pack(
        pady=(10, 3)
    )

    instructions = tk.Label(
        calendar_window,
        text="Click a day to select OFF, 1st, 2nd, or 3rd Shift",
        font=("Segoe UI", 9)
    )

    instructions.pack(
        pady=(0, 10)
    )

# ************************************************************* CALENDAR INPUT WINDOW DETAILS

    month_container = tk.Frame(
        calendar_window
    )

    month_container.pack(
        padx=10,
        pady=5
    )

    create_month(
        month_container,
        year1,
        month1,
        0
    )

    create_month(
        month_container,
        year2,
        month2,
        1
    )

# ************************************************************* CALENDAR INPUT DATA FROM JSON FILE

    file_label = tk.Label(
        calendar_window,
        text=(
            f"Data:  {JSON_FILE}\n"
            f"Image: {IMAGE_FILE}"
        ),
        font=("Segoe UI", 8),
        fg="gray"
    )

    file_label.pack(
        pady=(5, 10)
    )

    # Center window
    calendar_window.update_idletasks()

    screen_width = (
        calendar_window.winfo_screenwidth()
    )

    screen_height = (
        calendar_window.winfo_screenheight()
    )

    window_width = (
        calendar_window.winfo_width()
    )

    window_height = (
        calendar_window.winfo_height()
    )

    x = (
        screen_width - window_width
    ) // 2

    y = (
        screen_height - window_height
    ) // 2

    calendar_window.geometry(
        f"+{x}+{y}"
    )

    calendar_window.lift()
    calendar_window.focus_force()

# ************************************************************* REMOVE CALENDAR WINDOW FROM VIEW

def hide_calendar():

    global calendar_window

    if (
        calendar_window is not None
        and calendar_window.winfo_exists()
    ):

        calendar_window.withdraw()

# ************************************************************* CALENDAR WINDOW MAKE THE DISPLAY CONTENT

def create_month(
    parent,
    year,
    month,
    column
):

    frame = tk.Frame(
        parent,
        bd=1,
        relief="solid",
        bg="white"
    )

    frame.grid(
        row=0,
        column=column,
        padx=5
    )

    # Month title
    month_title = tk.Label(
        frame,
        text=f"{calendar.month_name[month]} {year}",
        font=("Segoe UI", 13, "bold"),
        bg="white"
    )

    month_title.grid(
        row=0,
        column=0,
        columnspan=7,
        pady=(8, 8)
    )

    # Day headings
    names = [
        "Sun",
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat"
    ]

    for col, name in enumerate(names):

        label = tk.Label(
            frame,
            text=name,
            width=5,
            font=("Segoe UI", 9, "bold"),
            bg="#E8E8E8"
        )

        label.grid(
            row=1,
            column=col,
            padx=1,
            pady=1
        )

    weeks = calendar.setfirstweekday(6)

    # Actual dates
    weeks = calendar.monthcalendar(
        year,
        month
    )

    today = date.today()

    for row, week in enumerate(
        weeks,
        start=2
    ):

        for col, day_number in enumerate(week):

            if day_number == 0:

                empty = tk.Label(
                    frame,
                    text="",
                    width=5,
                    height=2,
                    bg="white"
                )

                empty.grid(
                    row=row,
                    column=col,
                    padx=1,
                    pady=1
                )

                continue

            selected_date = date(
                year,
                month,
                day_number
            )

            value = day_values.get(
                selected_date,
                ""
            )

            # Background
            if selected_date == today:

                background = TODAY_COLOR_SELECT

            elif value:

                background = SELECTED_COLOR

            else:

                background = "white"

            # Text
            if value:

                text = (
                    f"{day_number}\n"
                    f"[{value}]"
                )

            else:

                text = str(day_number)

            button = tk.Button(
                frame,
                text=text,
                width=5,
                height=2,
                font=("Segoe UI", 10),
                bg=background,
                activebackground="#DDEBF7",
                command=lambda d=selected_date:
                    open_value_menu(d)
            )

            button.grid(
                row=row,
                column=col,
                padx=1,
                pady=1
            )

# ************************************************************* MAKE CALENDAR WINDOW

def rebuild_calendar():

    global calendar_window

    if (
        calendar_window is None
        or not calendar_window.winfo_exists()
    ):

        return

    # Remember position
    x = calendar_window.winfo_x()
    y = calendar_window.winfo_y()

    # Destroy existing window
    calendar_window.destroy()

    calendar_window = None

    # Create it again
    show_calendar()

    # Restore position
    if (
        calendar_window is not None
        and calendar_window.winfo_exists()
    ):

        calendar_window.geometry(
            f"+{x}+{y}"
        )

# ************************************************************* CHOOSE SHIFT WINDOW

def open_value_menu(selected_date):

    window = tk.Toplevel(root)

    window.title(
        selected_date.strftime(
            "%A, %B %d, %Y"
        )
    )

    window.resizable(
        False,
        False
    )

    window.transient(
        calendar_window
    )

    window.grab_set()

    label = tk.Label(
        window,
        text="Choose value:",
        font=("Segoe UI", 11)
    )

    label.pack(
        padx=15,
        pady=(15, 8)
    )

    buttons = tk.Frame(
        window
    )

    buttons.pack(
        padx=15,
        pady=(0, 15)
    )

    choices = [
        ("OFF", ""),
        ("1st", "1"),
        ("2st", "2"),
        ("3st", "3")
    ]

    for text, value in choices:

        button = tk.Button(
            buttons,
            text=text,
            width=8,
            height=2,
            font=("Segoe UI", 11),

            command=lambda v=value:
                change_value(
                    selected_date,
                    v,
                    window
                )
        )

        button.pack(
            side="left",
            padx=3
        )

# ************************************************************* CALENDAR INPUT FROM USER

def change_value(
    selected_date,
    value,
    selection_window
):

    # --------------------------------------------------------
    # Update memory
    # --------------------------------------------------------

    if value == "":

        day_values.pop(
            selected_date,
            None
        )

    else:

        day_values[selected_date] = value

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    save_day_values()

    # --------------------------------------------------------
    # Update image
    # --------------------------------------------------------

    create_weekly_image()

    # --------------------------------------------------------
    # Close selection window
    # --------------------------------------------------------

    selection_window.grab_release()
    selection_window.destroy()

    # --------------------------------------------------------
    # Update calendar
    # --------------------------------------------------------

    rebuild_calendar()

# ************************************************************* CREATE WINDOWS TRAY ICON

def create_tray_image():

    image = Image.new(
        "RGBA",
        (64, 64),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(image)

    # Calendar
    draw.rounded_rectangle(
        [5, 8, 59, 58],
        radius=7,
        fill="#2F5597"
    )

    draw.rectangle(
        [5, 21, 59, 58],
        fill="white"
    )

    # Binding rings
    draw.rectangle(
        [16, 4, 21, 17],
        fill="#2F5597"
    )

    draw.rectangle(
        [43, 4, 48, 17],
        fill="#2F5597"
    )

    # Current date
    font = get_font(
        27,
        bold=True
    )

    text = str(
        date.today().day
    )

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    text_width = (
        bbox[2] - bbox[0]
    )

    text_height = (
        bbox[3] - bbox[1]
    )

    draw.text(
        (
            32 - text_width / 2,
            29 - text_height / 2
        ),
        text,
        fill="#2F5597",
        font=font
    )

    return image

# ************************************************************* TRAY OPTIONS, WHEN YOU CLICK ON IT

def tray_open_calendar(
    icon,
    item
):

    # IMPORTANT:
    #
    # Do NOT call Tkinter from this thread.
    #
    # Put a command into the queue instead.

    command_queue.put(
        "show_calendar"
    )


def tray_exit(
    icon,
    item
):

    command_queue.put(
        "exit"
    )

# ************************************************************* START WINDOWS TRAY

def start_tray():

    global tray_icon

    menu = pystray.Menu(

        pystray.MenuItem(
            "Open Calendar",
            tray_open_calendar,
            default=True
        ),

        pystray.MenuItem(
            "Exit",
            tray_exit
        )
    )

    tray_icon = pystray.Icon(
        "DayCalendar",
        create_tray_image(),
        "Day Calendar",
        menu
    )

    tray_icon.run()

# ************************************************************* TRAY ICON OPTIONS CAN BE CLICKED

def process_commands():

    global tray_icon

    try:

        while True:

            command = command_queue.get_nowait()

            if command == "show_calendar":

                show_calendar()

            elif command == "exit":

                if tray_icon is not None:

                    tray_icon.stop()

                root.destroy()

                return

    except queue.Empty:

        pass

    # Check again in 100 ms.
    root.after(
        100,
        process_commands
    )

# ************************************************************* MAIN ROUTINE CALL, START HERE

def main():

    global root

    # --------------------------------------------------------
    # Create application directory
    # --------------------------------------------------------

    APP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Create JSON file immediately
    # --------------------------------------------------------

    create_empty_json_if_needed()

    # --------------------------------------------------------
    # Load saved values
    # --------------------------------------------------------

    load_day_values()

    # --------------------------------------------------------
    # Generate initial image
    # --------------------------------------------------------

    create_weekly_image()

    # --------------------------------------------------------
    # Create Tkinter
    # --------------------------------------------------------

    root = tk.Tk()

    root.withdraw()

    # --------------------------------------------------------
    # Start tray
    # --------------------------------------------------------

    tray_thread = threading.Thread(
        target=start_tray,
        daemon=True
    )

    tray_thread.start()

    # --------------------------------------------------------
    # Process commands from tray
    # --------------------------------------------------------

    root.after(
        100,
        process_commands
    )

    # --------------------------------------------------------
    # Start Tkinter
    # --------------------------------------------------------

    root.mainloop()

# ************************************************************* START HERE ACTUALLY

if __name__ == "__main__":

    main()