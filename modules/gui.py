"""
gui.py
------
The Tkinter GUI for SmartFlow AI.
Provides a modern, clean interface for submitting traffic requests,
running demo cases, and viewing color-coded AI pipeline output.
All AI logic is handled by the other modules — this file only
handles display and user interaction.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

from modules.input_preprocessing import validate_and_preprocess
from modules.request_router      import route_request
from modules.final_response      import build_final_response

# ------------------------------------------------------------------
# COLOR PALETTE — consistent across all GUI panels
# ------------------------------------------------------------------
C_BG_DARK     = "#0f172a"   # sidebar + topbar background
C_BG_MID      = "#1e293b"   # active sidebar item, pipeline box
C_BG_LIGHT    = "#f8fafc"   # main panel background
C_BG_WHITE    = "#ffffff"   # form field background
C_BG_CONSOLE  = "#0f172a"   # output console background

C_ACCENT_BLUE = "#3b82f6"   # primary accent (active nav, buttons)
C_TEXT_LIGHT  = "#f1f5f9"   # text on dark backgrounds
C_TEXT_MUTED  = "#64748b"   # secondary text
C_TEXT_DIM    = "#475569"   # very dim text (sidebar labels)
C_BORDER      = "#e2e8f0"   # form field borders

# Output console tag colors (one per module)
TAG_COLORS = {
    "ANN":      "#c4b5fd",   # purple — ANN module
    "KB":       "#93c5fd",   # blue   — Knowledge Base
    "KB_REJECT":"#f87171",   # red    — KB rejection
    "CSP":      "#86efac",   # green  — CSP scheduler
    "SEARCH":   "#fdba74",   # amber  — Search navigation
    "HEADER":   "#94a3b8",   # gray   — section headers
    "DONE":     "#4ade80",   # bright green — success
    "FAIL":     "#f87171",   # red          — failure
    "DIVIDER": "#334155",  # dark line separators
}

# Request categories and their display names
CATEGORIES = [
    ("Route_Request",                  "Route request"),
    ("Policy_Check",                   "Policy check"),
    ("Control_Allocation_Request",     "Control allocation"),
    ("Emergency_Response_Request",     "Emergency response"),
    ("Integrated_City_Service_Request","Integrated service"),
]

# Pipeline labels shown per category
PIPELINES = {
    "Route_Request":                   ["Search"],
    "Policy_Check":                    ["Knowledge Base"],
    "Control_Allocation_Request":      ["Knowledge Base", "CSP"],
    "Emergency_Response_Request":      ["ANN", "Knowledge Base", "CSP", "A* Search"],
    "Integrated_City_Service_Request": ["ANN", "Knowledge Base", "CSP", "A* Search"],
}

LOCATIONS = [
    "Police_HQ", "Traffic_Control_Center", "River_Bridge",
    "North_Station", "Central_Junction", "East_Market",
    "Stadium", "Airport_Road", "City_Hospital",
    "South_Residential", "West_Terminal", "Fire_Station",
    "Industrial_Zone",
]

# ------------------------------------------------------------------
# DEMO TEST CASES
# ------------------------------------------------------------------
DEMOS = [
    {
        "label": "Demo 1 — Standard route",
        "data": {
            "request_id":       "DEMO-001",
            "vehicle_type":     "Civilian",
            "request_category": "Route_Request",
            "current_location": "Police_HQ",
            "destination":      "City_Hospital",
            "incident_severity":"Low",
            "time_sensitivity": "No",
            "traffic_density":  "Light",
            "priority_claim":   "Normal",
            "distance":         "8",
            "description_note": "Standard civilian route request.",
        },
    },
    {
        "label": "Demo 2 — Civilian policy check (rejected)",
        "data": {
            "request_id":       "DEMO-002",
            "vehicle_type":     "Civilian",
            "request_category": "Policy_Check",
            "current_location": "East_Market",
            "destination":      "North_Station",
            "incident_severity":"Low",
            "time_sensitivity": "No",
            "traffic_density":  "Moderate",
            "priority_claim":   "Normal",
            "distance":         "4",
            "description_note": "Civilian requesting signal override — should be rejected.",
        },
    },
    {
        "label": "Demo 3 — Ambulance emergency (approved)",
        "data": {
            "request_id":       "DEMO-003",
            "vehicle_type":     "Ambulance",
            "request_category": "Emergency_Response_Request",
            "current_location": "Central_Junction",
            "destination":      "City_Hospital",
            "incident_severity":"High",
            "time_sensitivity": "Yes",
            "traffic_density":  "Dense",
            "priority_claim":   "Emergency",
            "distance":         "6",
            "description_note": "Ambulance responding to critical incident.",
        },
    },
    {
        "label": "Demo 4 — Integrated city service",
        "data": {
            "request_id":       "DEMO-004",
            "vehicle_type":     "Ambulance",
            "request_category": "Integrated_City_Service_Request",
            "current_location": "North_Station",
            "destination":      "City_Hospital",
            "incident_severity":"High",
            "time_sensitivity": "Yes",
            "traffic_density":  "Dense",
            "priority_claim":   "Emergency",
            "distance":         "7",
            "description_note": "Full integrated emergency service request.",
        },
    },
]


# ------------------------------------------------------------------
# MAIN APPLICATION CLASS
# ------------------------------------------------------------------

class SmartFlowApp:
    """
    Main GUI application class for SmartFlow AI.
    Builds the window, all panels, and connects user actions
    to the underlying AI pipeline modules.
    """

    def __init__(self, root):
        """
        Initializes the application window and builds all UI panels.
        'root' is the tk.Tk() window passed in from main.py.
        """
        self.root = root
        self.root.title("SmartFlow AI — Smart City Traffic & Emergency Response")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=C_BG_DARK)

        # Track currently selected category
        self.selected_category = tk.StringVar(value="Route_Request")

        # Build layout: topbar + body (sidebar + main)
        self._build_topbar()
        self._build_body()

        # Load first demo on startup to show the system ready
        self.root.after(300, lambda: self._run_demo(0))

    # ==============================================================
    # TOPBAR
    # ==============================================================

    def _build_topbar(self):
        """
        Builds the dark header bar at the top of the window.
        Contains the logo pill, app name, and system status indicators.
        """
        topbar = tk.Frame(self.root, bg=C_BG_DARK, height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        # Left side — logo pill + app name
        left = tk.Frame(topbar, bg=C_BG_DARK)
        left.pack(side="left", padx=20, pady=0)

        logo = tk.Label(
            left, text=" SF AI ", bg="#1e40af", fg="#bfdbfe",
            font=("Helvetica", 10, "bold"), padx=6, pady=2
        )
        logo.pack(side="left", pady=14)

        tk.Label(
            left, text="  SmartFlow AI",
            bg=C_BG_DARK, fg=C_TEXT_LIGHT,
            font=("Helvetica", 13, "bold")
        ).pack(side="left")

        tk.Label(
            left, text="  Smart City Traffic & Emergency Response",
            bg=C_BG_DARK, fg=C_TEXT_MUTED,
            font=("Helvetica", 10)
        ).pack(side="left")

        # Right side — status indicators
        right = tk.Frame(topbar, bg=C_BG_DARK)
        right.pack(side="right", padx=20)

        # Green online dot
        tk.Label(right, text="●", bg=C_BG_DARK, fg="#22c55e",
                 font=("Helvetica", 9)).pack(side="left")
        tk.Label(right, text=" System online  ·  ANN model loaded  ·  City graph ready",
                 bg=C_BG_DARK, fg=C_TEXT_MUTED,
                 font=("Helvetica", 9)).pack(side="left")

    # ==============================================================
    # BODY — sidebar + main panel side by side
    # ==============================================================

    def _build_body(self):
        """
        Creates the two-column body layout:
        left = sidebar (210px fixed), right = main panel (fills rest).
        """
        body = tk.Frame(self.root, bg=C_BG_LIGHT)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main_panel(body)

    # ==============================================================
    # SIDEBAR
    # ==============================================================

    def _build_sidebar(self, parent):
        """
        Builds the dark left sidebar containing:
        - Request type navigation buttons (one per category)
        - Demo case quick-run buttons
        - Active pipeline indicator at the bottom
        """
        sidebar = tk.Frame(parent, bg=C_BG_DARK, width=215)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Section: Request Type
        self._sidebar_section(sidebar, "REQUEST TYPE")
        self.nav_buttons = {}
        for key, label in CATEGORIES:
            btn = self._nav_button(sidebar, label, key)
            self.nav_buttons[key] = btn

        # Section: Demo Cases
        self._sidebar_section(sidebar, "DEMO CASES")
        for i, demo in enumerate(DEMOS):
            self._demo_button(sidebar, demo["label"], i)

        # Pipeline box at the bottom
        self.pipeline_frame = tk.Frame(sidebar, bg=C_BG_MID, padx=12, pady=10)
        self.pipeline_frame.pack(side="bottom", fill="x", padx=12, pady=12)

        tk.Label(
            self.pipeline_frame, text="ACTIVE PIPELINE",
            bg=C_BG_MID, fg=C_TEXT_DIM,
            font=("Helvetica", 8, "bold")
        ).pack(anchor="w")

        self.pipeline_label = tk.Label(
            self.pipeline_frame, text="Search",
            bg=C_BG_MID, fg="#60a5fa",
            font=("Helvetica", 9), wraplength=170, justify="left"
        )
        self.pipeline_label.pack(anchor="w", pady=(4, 0))

        # Highlight the first nav button as active
        self._set_active_nav("Route_Request")

    def _sidebar_section(self, parent, text):
        """Creates a small section label in the sidebar."""
        tk.Label(
            parent, text=text,
            bg=C_BG_DARK, fg=C_TEXT_DIM,
            font=("Helvetica", 8, "bold"),
            padx=14, pady=4
        ).pack(anchor="w", pady=(10, 0))

    def _nav_button(self, parent, label, category_key):
        """
        Creates a navigation button for a request category.
        Clicking it updates the form fields, pipeline badge,
        and active nav highlight.
        """
        btn = tk.Button(
            parent,
            text=f"  {label}",
            bg=C_BG_DARK, fg="#94a3b8",
            font=("Helvetica", 11),
            anchor="w", relief="flat",
            activebackground=C_BG_MID,
            activeforeground=C_TEXT_LIGHT,
            cursor="hand2",
            command=lambda k=category_key: self._on_category_select(k),
        )
        btn.pack(fill="x", padx=8, pady=1, ipady=5)
        return btn

    def _demo_button(self, parent, label, index):
        """
        Creates a demo quick-run button in the sidebar.
        Clicking it populates all form fields and submits automatically.
        """
        btn = tk.Button(
            parent,
            text=f"  ▶  {label}",
            bg=C_BG_DARK, fg="#94a3b8",
            font=("Helvetica", 10),
            anchor="w", relief="flat",
            activebackground=C_BG_MID,
            activeforeground=C_TEXT_LIGHT,
            cursor="hand2",
            command=lambda i=index: self._run_demo(i),
        )
        btn.pack(fill="x", padx=8, pady=1, ipady=4)

    def _set_active_nav(self, active_key):
        """
        Updates the visual style of nav buttons — highlights
        the active one in blue, resets all others to muted gray.
        """
        for key, btn in self.nav_buttons.items():
            if key == active_key:
                btn.config(bg=C_BG_MID, fg=C_TEXT_LIGHT)
            else:
                btn.config(bg=C_BG_DARK, fg="#94a3b8")

    # ==============================================================
    # MAIN PANEL
    # ==============================================================

    def _build_main_panel(self, parent):
        """
        Builds the white right panel containing:
        - A header bar (title, request ID, status badges)
        - The form section (all input fields as dropdowns)
        - Submit / Reset buttons
        - The output console (color-coded scrolled text)
        """
        main = tk.Frame(parent, bg=C_BG_LIGHT)
        main.pack(side="left", fill="both", expand=True)

        self._build_main_header(main)
        self._build_form(main)
        self._build_buttons(main)
        self._build_output(main)

    def _build_main_header(self, parent):
        """
        Dark sub-header inside the main panel showing:
        request type label, request ID, and status tags.
        """
        header = tk.Frame(parent, bg=C_BG_WHITE, height=56,
                          relief="flat", bd=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Thin bottom border
        border = tk.Frame(parent, bg=C_BORDER, height=1)
        border.pack(fill="x")

        left = tk.Frame(header, bg=C_BG_WHITE)
        left.pack(side="left", padx=20, pady=8)

        self.header_title = tk.Label(
            left, text="Route request",
            bg=C_BG_WHITE, fg="#0f172a",
            font=("Helvetica", 13, "bold")
        )
        self.header_title.pack(anchor="w")

        self.header_sub = tk.Label(
            left, text="Pipeline: Search only",
            bg=C_BG_WHITE, fg=C_TEXT_MUTED,
            font=("Helvetica", 9)
        )
        self.header_sub.pack(anchor="w")

        right = tk.Frame(header, bg=C_BG_WHITE)
        right.pack(side="right", padx=20)

        self.priority_badge = tk.Label(
            right, text="",
            bg="#f0fdf4", fg="#15803d",
            font=("Helvetica", 9, "bold"),
            padx=10, pady=3
        )
        self.priority_badge.pack(side="right", padx=4)

        self.status_badge = tk.Label(
            right, text="",
            bg="#eff6ff", fg="#1d4ed8",
            font=("Helvetica", 9, "bold"),
            padx=10, pady=3
        )
        self.status_badge.pack(side="right", padx=4)

    def _build_form(self, parent):
        """
        Builds all 8 input fields as labeled dropdowns (Combobox).
        Laid out in a 4-column grid: [label, input, label, input]
        """
        form_frame = tk.Frame(parent, bg=C_BG_LIGHT, padx=20, pady=14)
        form_frame.pack(fill="x")

        tk.Label(
            form_frame, text="REQUEST DETAILS",
            bg=C_BG_LIGHT, fg=C_TEXT_MUTED,
            font=("Helvetica", 8, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # Field definitions: (label, variable_name, options_list)
        fields = [
            ("Request ID",       "request_id",       None),
            ("Vehicle type",     "vehicle_type",     ["Civilian","Ambulance","FireTruck","Police"]),
            ("Current location", "current_location", LOCATIONS),
            ("Destination",      "destination",      LOCATIONS),
            ("Incident severity","incident_severity",["Low","Medium","High"]),
            ("Traffic density",  "traffic_density",  ["Light","Moderate","Dense"]),
            ("Time sensitivity", "time_sensitivity", ["Yes","No"]),
            ("Priority claim",   "priority_claim",   ["Normal","Emergency"]),
        ]

        self.form_vars = {}

        for i, (label, var_name, options) in enumerate(fields):
            row    = (i // 2) + 1   # 2 fields per row
            col    = (i % 2) * 2    # columns 0,2,4,6

            # Label
            tk.Label(
                form_frame, text=label,
                bg=C_BG_LIGHT, fg=C_TEXT_MUTED,
                font=("Helvetica", 9)
            ).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=4)

            var = tk.StringVar()
            self.form_vars[var_name] = var

            if options:
                # Dropdown (Combobox)
                cb = ttk.Combobox(
                    form_frame, textvariable=var,
                    values=options, state="readonly",
                    width=22, font=("Helvetica", 10)
                )
                cb.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=4)
                cb.set(options[0])
            else:
                # Free text entry (for request_id)
                entry = ttk.Entry(
                    form_frame, textvariable=var,
                    width=25, font=("Helvetica", 10)
                )
                entry.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=4)
                var.set("REQ-001")

        # Hidden category field (controlled by sidebar, not form)
        self.form_vars["request_category"] = self.selected_category

    def _build_buttons(self, parent):
        """
        Builds Submit, Reset, and Clear Output action buttons.
        """
        btn_frame = tk.Frame(parent, bg=C_BG_LIGHT, padx=20, pady=4)
        btn_frame.pack(fill="x")

        # Submit — primary action
        tk.Button(
            btn_frame, text="  Submit request  ",
            bg=C_ACCENT_BLUE, fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", padx=6, pady=6,
            cursor="hand2",
            activebackground="#2563eb",
            command=self._submit_request,
        ).pack(side="left", padx=(0, 8))

        # Reset — clears form
        tk.Button(
            btn_frame, text="  Reset form  ",
            bg=C_BG_WHITE, fg=C_TEXT_MUTED,
            font=("Helvetica", 10),
            relief="flat", padx=6, pady=6,
            cursor="hand2",
            command=self._reset_form,
        ).pack(side="left", padx=(0, 8))

        # Clear output — on the right
        tk.Button(
            btn_frame, text="  Clear output  ",
            bg=C_BG_WHITE, fg="#dc2626",
            font=("Helvetica", 10),
            relief="flat", padx=6, pady=6,
            cursor="hand2",
            command=self._clear_output,
        ).pack(side="right")

    def _build_output(self, parent):
        """
        Builds the scrollable output console at the bottom.
        Uses a dark background and color-coded text tags
        (one per AI module) for easy visual tracing.
        """
        out_frame = tk.Frame(parent, bg=C_BG_LIGHT, padx=20, pady=8)
        out_frame.pack(fill="both", expand=True)

        # Header row above console
        hdr = tk.Frame(out_frame, bg=C_BG_LIGHT)
        hdr.pack(fill="x", pady=(0, 6))

        tk.Label(
            hdr, text="SYSTEM OUTPUT",
            bg=C_BG_LIGHT, fg=C_TEXT_MUTED,
            font=("Helvetica", 8, "bold")
        ).pack(side="left")

        self.timestamp_label = tk.Label(
            hdr, text="",
            bg=C_BG_LIGHT, fg=C_TEXT_DIM,
            font=("Helvetica", 8)
        )
        self.timestamp_label.pack(side="right")

        # The scrollable text widget — acts as the output console
        self.output_text = scrolledtext.ScrolledText(
            out_frame,
            bg=C_BG_CONSOLE, fg="#cbd5e1",
            font=("Courier", 10),
            relief="flat",
            padx=14, pady=12,
            wrap="word",
            state="disabled",   # read-only — we write via tag_insert
        )
        self.output_text.pack(fill="both", expand=True)

        # Register a color tag for each module label
        for tag, color in TAG_COLORS.items():
            self.output_text.tag_config(tag, foreground=color)

        # Extra tags for styled inline labels in the output lines
        self.output_text.tag_config("TAG_ANN",    foreground="#c4b5fd", font=("Courier", 9, "bold"))
        self.output_text.tag_config("TAG_KB",     foreground="#93c5fd", font=("Courier", 9, "bold"))
        self.output_text.tag_config("TAG_CSP",    foreground="#86efac", font=("Courier", 9, "bold"))
        self.output_text.tag_config("TAG_SEARCH", foreground="#fdba74", font=("Courier", 9, "bold"))

    # ==============================================================
    # INTERACTION HANDLERS
    # ==============================================================

    def _on_category_select(self, category_key):
        """
        Called when a sidebar nav button is clicked.
        Updates the active nav highlight, the header title,
        the pipeline badge, and the hidden category form variable.
        """
        self.selected_category.set(category_key)
        self._set_active_nav(category_key)

        # Update header
        display_name = dict(CATEGORIES).get(category_key, category_key)
        self.header_title.config(text=display_name.capitalize())

        # Update pipeline label in sidebar
        pipeline_steps = PIPELINES.get(category_key, [])
        self.pipeline_label.config(text=" → ".join(pipeline_steps))
        self.header_sub.config(text=f"Pipeline: {' → '.join(pipeline_steps)}")

    def _collect_form_data(self):
        """
        Reads all form fields and returns them as a raw request dict
        ready to pass into validate_and_preprocess().
        """
        return {
            var_name: var.get()
            for var_name, var in self.form_vars.items()
        }

    def _submit_request(self):
        """
        Collects form data, runs the full AI pipeline in a background
        thread (so the GUI doesn't freeze), and displays the result
        in the output console.
        """
        raw_data = self._collect_form_data()

        # Run in background thread to keep GUI responsive
        def pipeline_thread():
            self._write_output([("HEADER", "Processing request...")])
            self._run_pipeline(raw_data)

        thread = threading.Thread(target=pipeline_thread, daemon=True)
        thread.start()

    def _run_pipeline(self, raw_data):
        """
        The actual pipeline execution:
        1. Validate and preprocess the raw form data
        2. Route to correct AI modules
        3. Build final response
        4. Display result in the console
        """
        try:
            # Step 1 — Preprocessing
            clean = validate_and_preprocess(raw_data)
            if "error" in clean:
                self._write_output([
                    ("FAIL", f"Input Error: {clean['error']}")
                ])
                return

            # Step 2 — Route through AI modules
            results = route_request(clean)

            # Step 3 — Build final response
            final = build_final_response(results)

            # Step 4 — Display in console
            self._write_output(final["lines"])

            # Update status badges in the header
            self.root.after(0, lambda: self._update_badges(final))

        except Exception as e:
            self._write_output([
                ("FAIL", f"System Error: {str(e)}")
            ])

    def _write_output(self, lines):
        """
        Writes a list of (tag, text) tuples to the output console.
        Each tag controls the color of that line.
        Must update the Tkinter widget from the main thread.
        """
        def update():
            self.output_text.config(state="normal")
            self.output_text.delete("1.0", tk.END)   # clear previous output

            for tag, text in lines:
                # Write a small colored tag label before the line
                if tag in ("ANN", "KB", "KB_REJECT", "CSP", "SEARCH"):
                    label_map = {
                        "ANN":       (" ANN  ", "TAG_ANN"),
                        "KB":        ("  KB  ", "TAG_KB"),
                        "KB_REJECT": ("  KB  ", "TAG_KB"),
                        "CSP":       (" CSP  ", "TAG_CSP"),
                        "SEARCH":    ("  A*  ", "TAG_SEARCH"),
                    }
                    tag_text, tag_style = label_map[tag]
                    self.output_text.insert(tk.END, f"[{tag_text}]  ", tag_style)
                    self.output_text.insert(tk.END, text + "\n", tag)
                else:
                    self.output_text.insert(tk.END, text + "\n", tag)

            self.output_text.config(state="disabled")
            self.output_text.see(tk.END)   # scroll to bottom

            # Update timestamp
            import time
            self.timestamp_label.config(
                text=f"Last run: {time.strftime('%H:%M:%S')}"
            )

        self.root.after(0, update)   # schedule on main thread

    def _update_badges(self, final):
        """
        Updates the priority and status badge labels in the
        header bar based on the final response result.
        """
        priority = final.get("priority", "N/A")
        approved = final.get("approved", True)

        # Priority badge styling
        priority_colors = {
            "Critical": ("#fef2f2", "#b91c1c"),
            "High":     ("#fff7ed", "#c2410c"),
            "Normal":   ("#f0fdf4", "#15803d"),
            "Low":      ("#f8fafc", "#475569"),
            "N/A":      ("#f8fafc", "#475569"),
        }
        bg, fg = priority_colors.get(priority, ("#f8fafc", "#475569"))
        self.priority_badge.config(text=f"  {priority}  ", bg=bg, fg=fg)

        # Status badge
        if approved:
            self.status_badge.config(text=" Approved ", bg="#f0fdf4", fg="#15803d")
        else:
            self.status_badge.config(text=" Rejected ", bg="#fef2f2", fg="#b91c1c")

    def _run_demo(self, index):
        """
        Loads the preset data for demo case at 'index',
        populates all form fields, switches to the correct
        category in the sidebar, and submits the request.
        """
        demo = DEMOS[index]
        data = demo["data"]

        # Switch category in sidebar
        cat = data.get("request_category", "Route_Request")
        self._on_category_select(cat)

        # Populate all matching form variables
        for field, var in self.form_vars.items():
            if field in data:
                var.set(data[field])

        # Auto-submit after a short delay so the UI updates first
        self.root.after(200, self._submit_request)

    def _reset_form(self):
        """Resets all form fields to their default first option."""
        defaults = {
            "request_id":       "REQ-001",
            "vehicle_type":     "Civilian",
            "current_location": "Police_HQ",
            "destination":      "City_Hospital",
            "incident_severity":"Low",
            "time_sensitivity": "No",
            "traffic_density":  "Light",
            "priority_claim":   "Normal",
        }
        for field, value in defaults.items():
            if field in self.form_vars:
                self.form_vars[field].set(value)

    def _clear_output(self):
        """Clears the output console text area."""
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state="disabled")
        self.status_badge.config(text="", bg="#eff6ff")
        self.priority_badge.config(text="", bg="#f0fdf4")


# ------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------

def launch_gui():
    """
    Creates the root Tk window and starts the SmartFlow GUI.
    Called from main.py.
    """
    root = tk.Tk()

    # Apply a clean ttk theme as the base
    style = ttk.Style(root)
    style.theme_use("clam")

    # Style Combobox fields
    style.configure(
        "TCombobox",
        fieldbackground="#ffffff",
        background="#ffffff",
        foreground="#0f172a",
        selectbackground="#eff6ff",
        selectforeground="#1d4ed8",
        borderwidth=1,
        relief="flat",
    )

    app = SmartFlowApp(root)
    root.mainloop()