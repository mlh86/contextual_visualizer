"""
contextual_visualizer -- An app that puts things in perspective

This little app offers spatial and population-based visualizations
to help the user get to grips with his or her place in the universe.

On the spatial side, you enter your house-area, your city's area and
your country-name, and it shows you three levels of perspective:
- how big your city would be if your house was shrunk to 1 pixel
- how big the world & your country would be if your city was shrunk to 1 pixel
- how big earth's orbit is compared to the size of the sun and the earth

On the population side, it shows you the number of people born every hour and
every day, as well as the number of deaths per hour and per day.

Copyright (C) 2022  Mohammad L. Hussain

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfd
import ctypes
import os

from PIL import Image, ImageDraw

DAILY_BIRTHS = 385000
DAILY_DEATHS = 165000
S_TO_EO_DIAMETER_RATIO = 211.60 # Ratio of sun's diameter to earth's orbital diameter

def _get_grid_pattern_string(color):
    even_row_str = "{ "
    odd_row_str = "{ "
    for i in range(2):
        even_row_str += f"{color} {color} " if i % 2 else "#ffffff #ffffff "
        odd_row_str += "#ffffff #ffffff " if i % 2 else f"{color} {color} "
    even_row_str += "} "
    odd_row_str += "} "
    return even_row_str + even_row_str + odd_row_str + odd_row_str


def draw_canvas_grid(width, height, use_scrollers, wintitle, inset_width=0, title_count=None):
    """
    This is the workhorse function that takes a width and a height and draws a corresponding
    grid using tk.Canvas. The grid is also drawn in-memory using PIL's ImageDraw module in
    order to be able to save the image to PNG with high fidelity. Note that for proper scrolling,
    I had to nest the actual canvas inside a frame inside an outer-canvas C. The scrollbars are
    only created if the canvas-grid overflows the screen's dimensions (e.g. if it's greater than
    0.86 of the screen's height)
    """
    # For proper scrolling, need to  (as frames don't have scrollbars)
    cwin = tk.Toplevel(root)
    C = tk.Canvas(cwin, name='c')
    cframe = ttk.Frame(C, name='f')
    canvas = tk.Canvas(cframe, name='canvas')
    C.grid(row=0,column=0,sticky='nsew')

    # Configuring top-level elements...
    if use_scrollers:
        yscroller = ttk.Scrollbar(cwin, command=C.yview, orient='vertical')
        xscroller = ttk.Scrollbar(cwin, command=C.xview, orient='horizontal')
        C['xscrollcommand'] = xscroller.set
        C['yscrollcommand'] = yscroller.set
        yscroller.grid(row=0,column=1,sticky='nsw')
        xscroller.grid(row=1,column=0,sticky='ewn')

    C.create_window(0,0, window=cframe, anchor='nw')
    canvas.grid(row=0, column=0, sticky='nw')

    if not title_count:
        title_count = " - 1 in " + "{0:,}".format(width*height)
    cwin.columnconfigure(0, weight=1)
    cwin.rowconfigure(0, weight=1)
    cwin.title(wintitle + title_count)
    cwin['bg'] = "#dddddd"

    C['bg'] = "black"
    C['highlightthickness'] = 0

    canvas['background'] = '#000000'
    canvas['width'] = width*2
    canvas['height'] = height*2

    # Draw the grid image on canvas, at double-scale...
    canvas.img = tk.PhotoImage(width = width*2, height = height*2)
    canvas.create_image((2, 2), image = canvas.img, state = "normal", anchor = tk.NW)

    canvas.img.put(_get_grid_pattern_string("#000000"), to=(0, 0, width*2, height*2))
    canvas.create_rectangle((2,2,3,3),outline="red",fill="red")

    # We draw the image in parallel using PIL, without displaying it. Used for saving to PNG...
    even_row_bytes = b""
    odd_row_bytes = b""
    for i in range(width):
        even_row_bytes += b"\x00\x00\x00" if i % 2 else b"\xff\xff\xff"
        odd_row_bytes += b"\xff\xff\xff" if i % 2 else b"\x00\x00\x00"
    pixel_bytes = (even_row_bytes + odd_row_bytes) * ((height+1)//2)

    pil_img = Image.frombytes("RGB", (width, height), pixel_bytes)
    draw = ImageDraw.Draw(pil_img)
    canvas.image = pil_img

    if inset_width: # inset_height == inset_width
        canvas.img.put(_get_grid_pattern_string("green"), to=(0, 0, inset_width*2, inset_width*2))
        for i in range(0, inset_width, 2):
            draw.line([i,0,i,inset_width], 'green')
        for i in range(0, inset_width, 2):
            draw.line([0,i,inset_width,i], 'green')

    draw.line([1,1,1,1],'red')

    if use_scrollers:
        C['width'] = 0.86*root.winfo_screenwidth()
        C['height'] = 0.86*root.winfo_screenheight()
        C['scrollregion'] = (0, 0, width*2, height*2)
        cwin.geometry('+%d+%d'%(5,5))
    else:
        C['width'] = width*2
        C['height'] = height*2
        cwin.resizable(False, False)

    cwin.bind("<Control-s>", save_canvas_to_png)


def draw_earth_sun_diagram():
    """
    This is a variant of the function above that draws earth's orbit around the sun
    instead of a pixel-grid. The basic canvas-level logic is the same, but it uses
    create_oval instead of create_line. The image is again drawn in parallel using
    both tk.Canvas and PIL's ImageDraw so as to allow proper saving to PNG.
    """
    cwin = tk.Toplevel(root)
    C = tk.Canvas(cwin, name='c')
    cframe = ttk.Frame(C, name='f')
    canvas = tk.Canvas(cframe, name='canvas')
    C.grid(row=0,column=0,sticky='nsew')
    C.create_window(0,0, window=cframe, anchor='nw')
    canvas.grid(row=0, column=0, sticky='nw')

    orbital_diameter = round(8 * S_TO_EO_DIAMETER_RATIO)
    orbital_radius = round(orbital_diameter/2)

    canvas['width'] =  orbital_diameter + 8
    canvas['height'] = orbital_diameter + 8

    # We draw the image in parallel using PIL, without displaying it. Used for saving to PNG...
    image = Image.new("RGB", (orbital_diameter+8, orbital_diameter+8), "white")
    draw = ImageDraw.Draw(image)
    canvas.image = image

    canvas.create_oval(4, 4, 4+orbital_diameter, 4+orbital_diameter)
    draw.ellipse([4, 4, 4+orbital_diameter, 4+orbital_diameter], outline="black")
    canvas.create_oval(orbital_radius, orbital_radius, orbital_radius+8, orbital_radius+8,
                       outline="orange",fill="red")
    draw.ellipse([orbital_radius, orbital_radius, orbital_radius+8, orbital_radius+8],
                 outline="orange",fill="red")

    if orbital_diameter > 0.86*root.winfo_screenheight() or orbital_diameter > 0.96*root.winfo_screenwidth():
        yscroller = ttk.Scrollbar(cwin, command=C.yview, orient='vertical')
        xscroller = ttk.Scrollbar(cwin, command=C.xview, orient='horizontal')
        C['xscrollcommand'] = xscroller.set
        C['yscrollcommand'] = yscroller.set
        yscroller.grid(row=0,column=1,sticky='nsw')
        xscroller.grid(row=1,column=0,sticky='ewn')
        if orbital_diameter > 0.96*root.winfo_screenwidth():
            C['width'] = 0.96*root.winfo_screenwidth()
        else:
            C['width'] = orbital_diameter + 8
        C['height'] = 0.86*root.winfo_screenheight()
        C['scrollregion'] = (0, 0, orbital_diameter+8, orbital_diameter+8)
        cwin.geometry('+%d+%d'%(5,5))
    else:
        C['width'] = orbital_diameter + 8
        C['height'] = orbital_diameter + 8

    cwin.resizable(False, False)
    cwin.title("The Earth is an invisible speck in space, with a diameter < 1% of the Sun's")
    cwin.bind("<Control-s>", save_canvas_to_png)


def create_ratio_visualization(ratio, wintitle, subratio=None, title_count=None):
    """
    A helper function that takes in a ratio and a sub-ratio, as well as a window title,
    and calls the workhorse function above to draw appropriately sized pixel-grids. You
    basically pass in a ratio-number such as 300,000 and it auto-creates a grid containing
    roughly that many pixels, making best-use of the screen's aspect ratio.
    """
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    aspect_ratio = screen_width / screen_height
    gridheight = round((ratio/aspect_ratio)**0.5)
    gridwidth = round(aspect_ratio*gridheight)
    use_scrollers = True if gridheight > 0.45*screen_height else False
    inset_width = round(subratio**0.5) if subratio else 0
    draw_canvas_grid(gridwidth, gridheight, use_scrollers, wintitle, inset_width, title_count)


def save_canvas_to_png(evt=None):
    """
    This function takes the in-memory image drawn using PIL's ImageDraw module and saves it
    as a PNG file using the filepath selected by the user via the save-file-as dialog.
    """
    cwin = evt.widget
    canvas = cwin.nametowidget(str(cwin) + ".c.f.canvas")
    filepath = tkfd.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Files","*.png")])
    if not filepath:
        return
    temp_tk = tk.Toplevel(root)
    temp_tk.title("Saving file...")
    temp_tk.geometry("")
    temp_pb = ttk.Progressbar(temp_tk)
    temp_pb.pack()
    temp_tk.transient(root)
    temp_tk.geometry("+%d+%d" % (400, 200))
    temp_pb.step(20)
    root.update()
    canvas.image.save(filepath)
    temp_pb.step(60)
    root.update()
    temp_tk.destroy()

##############################################################################################

def create_spatial_visualizations():
    """
    This function takes the area-values entered by the user and calls the
    create_ratio_visualization function with appropriate ratio-parameters.
    It also calls the draw_earth_sun_diagram function, resulting in
    3 new top-level windows being created.
    """
    house_area = float(entry_HA.get())
    if ha_unit.get() == 'sq. feet':
        house_area *= 0.092903
    elif ha_unit.get() == 'sq. yards':
        house_area *= 0.836127

    city_area = float(entry_CA.get())
    if ca_unit.get() == 'sq. miles':
        city_area = city_area * 2.58999 * 1000000
    else:
        city_area = city_area * 1000000
    country_area = country_areas[combobox_COUNTRY.get()] * 1000000
    world_area = 510072000 * 1000000

    h_to_c_ratio = round(city_area / house_area)
    create_ratio_visualization(h_to_c_ratio, "Your House in Your City")

    c_to_w_ratio = round(world_area / city_area)
    c_to_c_ratio = round(country_area / city_area)
    create_ratio_visualization(c_to_w_ratio, "Your City in Your Country and the World",
                               subratio=c_to_c_ratio)

    draw_earth_sun_diagram()


def validate_form_and_create_spatial_visualizations(evt=None):
    """
    Performs basic validation of the user's spatial area inputs.
    It shows a warning prompt if the inputs are invalid, and calls
    the create_spatial_visualization function otherwise.
    """
    error_msg = ""
    try:
        float1 = float(entry_HA.get())
        float2 = float(entry_CA.get())
    except:
        error_msg = "Please enter numeric area values"
    if not error_msg and (float1 <= 0 or float2 <= 0):
        error_msg = "Please enter positive area values"
    if not error_msg and combobox_COUNTRY.get() not in countries_list:
        error_msg = "Please select a country-name from the dropdown list"

    if error_msg:
        tk.messagebox.showwarning("Invalid Input", error_msg)
    else:
        create_spatial_visualizations()


def create_population_visualizations(evt=None):
    """
    This function validates the user's population-pane checkbox selection
    and calls the create_ratio_visualization function to display the
    number of births and/or deaths per hour and per day.
    """
    if not show_births.get() and not show_deaths.get():
        tk.messagebox.showwarning("Invalid Selection",
                                  "Please select at least one visualization checkbox")
    if show_births.get():
        create_ratio_visualization(DAILY_BIRTHS, "Births per day (and hr)",
                                   DAILY_BIRTHS//24, " ~ " + str(DAILY_BIRTHS))
    if show_deaths.get():
        create_ratio_visualization(DAILY_DEATHS, "Deaths per day (and hr)",
                                   DAILY_DEATHS//24, " ~ " + str(DAILY_DEATHS))

################################################################################################
# The main GUI-creation code can be found below. It uses ttk.Notebook to create a 2-tab window,
# one tab for spatial visualization and the other for population.

if os.name == 'nt':
    ctypes.windll.shcore.SetProcessDpiAwareness(2)

root = tk.Tk()
root.geometry("480x640")
root.resizable(False, False)
root.title("Contextual Visualizer")

style = ttk.Style()

N = ttk.Notebook(root, padding=4)
N.grid(row=0,column=0,sticky='nsew')

FS = ttk.Frame(N, padding=10)
FP = ttk.Frame(N, padding=10)
N.add(FS, text=" Space ")
N.add(FP, text=' Population ')

# -----------------POPULATION-PANE-----------------

show_births = tk.BooleanVar()
checkbutton_BIRTHS = ttk.Checkbutton(FP, text="No. of people born each day",variable=show_births)

show_deaths = tk.BooleanVar()
checkbutton_DEATHS = ttk.Checkbutton(FP, text="No. of people who die each day",variable=show_deaths)

pop_vis_button = ttk.Button(FP, text="Visualize", command=create_population_visualizations)
pop_vis_button.bind("<Return>", create_population_visualizations)

checkbutton_BIRTHS.grid(row=0, column=0, sticky=tk.W)
checkbutton_DEATHS.grid(row=1, column=0, sticky=tk.W)
pop_vis_button.grid(row=2, column=0, sticky=tk.E, pady=10)

# ------------------SPATIAL-PANE-------------------

label_HA = ttk.Label(FS, text="House Area ")
label_CA = ttk.Label(FS, text="City Area ")
entry_HA = ttk.Entry(FS)
entry_CA = ttk.Entry(FS)

ha_unit = tk.StringVar(FS, 'sq. yards')
option_HA_unit = ttk.OptionMenu(FS, ha_unit, "sq. yards", "sq. feet", "sq. yards", "sq. meters")
option_HA_unit.configure(takefocus=0)

ca_unit = tk.StringVar(FS, 'sq. kms')
option_CA_unit = ttk.OptionMenu(FS, ca_unit, "sq. kms", "sq. kms", "sq. miles")
option_CA_unit.configure(takefocus=0)

country = tk.StringVar(FS)

country_areas = {"Russia": 17098242, "Canada": 9984670, "China": 9706961, "United States": 9372610,
"Brazil": 8515767, "Australia": 7692024, "India": 3287590, "Argentina": 2780400,
"Kazakhstan": 2724900, "Algeria": 2381741, "DR Congo": 2344858, "Greenland": 2166086,
"Saudi Arabia": 2149690, "Mexico": 1964375, "Indonesia": 1904569, "Sudan": 1886068,
"Libya": 1759540, "Iran": 1648195, "Mongolia": 1564110, "Peru": 1285216, "Chad": 1284000,
"Niger": 1267000, "Angola": 1246700, "Mali": 1240192, "South Africa": 1221037, "Colombia": 1141748,
"Ethiopia": 1104300, "Bolivia": 1098581,"Mauritania": 1030700, "Egypt": 1002450, "Tanzania": 945087,
"Nigeria": 923768, "Venezuela": 916445, "Pakistan": 881912, "Namibia": 825615, "Mozambique": 801590,
"Turkey": 783562, "Chile": 756102, "Zambia": 752612, "Myanmar": 676578, "Afghanistan": 652230,
"Somalia": 637657, "Central African Republic": 622984, "South Sudan": 619745, "Ukraine": 603500,
"Madagascar": 587041, "Botswana": 582000, "Kenya": 580367, "France": 551695, "Yemen": 527968,
"Thailand": 513120, "Spain": 505992, "Turkmenistan": 488100, "Cameroon": 475442,
"Papua New Guinea": 462840, "Sweden": 450295, "Uzbekistan": 447400, "Morocco": 446550,
"Iraq": 438317, "Paraguay": 406752, "Zimbabwe": 390757, "Japan": 377930, "Germany": 357114,
"Philippines": 342353, "Congo": 342000, "Finland": 338424, "Vietnam": 331212,
"Malaysia": 330803, "Norway": 323802, "Cote d'Ivoire": 322463, "Poland": 312679, "Oman": 309500,
"Italy": 301336, "Ecuador": 276841, "Burkina Faso": 272967, "New Zealand": 270467, "Gabon": 267668,
"Western Sahara": 266000, "Guinea": 245857, "United Kingdom": 242900, "Uganda": 241550,
"Ghana": 238533, "Romania": 238391, "Laos": 236800, "Guyana": 214969, "Belarus": 207600,
"Kyrgyzstan": 199951, "Senegal": 196722, "Syria": 185180, "Cambodia": 181035, "Uruguay": 181034,
"Suriname": 163820, "Tunisia": 163610, "Bangladesh": 147570, "Nepal": 147181, "Tajikistan": 143100,
"Greece": 131990, "Nicaragua": 130373, "North Korea": 120538, "Malawi": 118484, "Eritrea": 117600,
"Benin": 112622, "Honduras": 112492, "Liberia": 111369, "Bulgaria": 110879, "Cuba": 109884,
"Guatemala": 108889, "Iceland": 103000, "South Korea": 100210, "Hungary": 93028, "Portugal": 92090,
"Jordan": 89342, "Serbia": 88361, "Azerbaijan": 86600, "Austria": 83871,
"United Arab Emirates": 83600, "French Guiana": 83534, "Czechia": 78865, "Panama": 75417,
"Sierra Leone": 71740, "Ireland": 70273, "Georgia": 69700, "Sri Lanka": 65610, "Lithuania": 65300,
"Latvia": 64559, "Togo": 56785, "Croatia": 56594, "Bosnia and Herzegovina": 51209,
"Costa Rica": 51100, "Slovakia": 49037, "Dominican Republic": 48671, "Estonia": 45227,
"Denmark": 43094, "Netherlands": 41850, "Switzerland": 41284, "Bhutan": 38394, "Taiwan": 36193,
"Guinea-Bissau": 36125, "Moldova": 33846, "Belgium": 30528, "Lesotho": 30355, "Armenia": 29743,
"Solomon Islands": 28896, "Albania": 28748, "Equatorial Guinea": 28051, "Burundi": 27834,
"Haiti": 27750, "Rwanda": 26338, "Republic of North Macedonia": 25713, "Djibouti": 23200,
"Belize": 22966, "El Salvador": 21041, "Israel": 20770, "Slovenia": 20273, "New Caledonia": 18575,
"Fiji": 18272, "Kuwait": 17818, "Eswatini": 17364, "Timor-Leste": 14874, "Bahamas": 13943,
"Montenegro": 13812, "Vanuatu": 12189, "Falkland Islands": 12173, "Qatar": 11586, "Jamaica": 10991,
"Gambia": 10689, "Lebanon": 10452, "Cyprus": 9251, "Puerto Rico": 8870, "State of Palestine": 6220,
"Brunei Darussalam": 5765, "Trinidad and Tobago": 5130,"French Polynesia": 4167, "Cabo Verde": 4033,
"Samoa": 2842, "Luxembourg": 2586, "Reunion": 2511, "Mauritius": 2040, "Comoros": 1862,
"Guadeloupe": 1628, "Faeroe Islands": 1393, "Martinique": 1128, "Sao Tome and Principe": 964,
"Turks and Caicos Islands": 948, "Kiribati": 811, "Bahrain": 765, "Dominica": 751, "Tonga": 747,
"Singapore": 710, "Micronesia": 702, "Saint Lucia": 616, "Isle of Man": 572, "Guam": 549,
"Andorra": 468, "Northern Mariana Islands": 464, "Palau": 459, "Seychelles": 452, "Curacao": 444,
"Antigua and Barbuda": 442, "Barbados": 430, "Saint Helena": 394,
"Saint Vincent and the Grenadines": 389, "Mayotte": 374, "United States Virgin Islands": 347,
"Grenada": 344, "Caribbean Netherlands": 328, "Malta": 316, "Maldives": 300, "Cayman Islands": 264,
"Saint Kitts and Nevis": 261, "Niue": 260, "Saint Pierre and Miquelon": 242, "Cook Islands": 236,
"American Samoa": 199, "Marshall Islands": 181, "Aruba": 180, "Liechtenstein": 160,
"British Virgin Islands": 151, "Wallis and Futuna Islands": 142, "Montserrat": 102, "Anguilla": 91,
"San Marino": 61, "Bermuda": 54, "Saint Martin": 53, "Sint Maarten": 34, "Tuvalu": 26, "Nauru": 21,
"Saint Barthelemy": 21, "Tokelau": 12, "Gibraltar": 6, "Monaco": 2}

countries_list = sorted(country_areas.keys())

def filter_countries(event):
    """Filter's the combobox's drop-down list entries based on what the user has entered"""
    value = event.widget.get()
    if value == '':
        event.widget['values'] = countries_list
    else:
        event.widget['values'] = [c for c in countries_list if c.lower().startswith(value.lower())]

combobox_COUNTRY = ttk.Combobox(FS, textvariable=country, values=countries_list)
combobox_COUNTRY.bind('<KeyRelease>', filter_countries)
label_COUNTRY = ttk.Label(FS, text="Country ")

vis_button = ttk.Button(FS, text="Visualize",
                        command=validate_form_and_create_spatial_visualizations)

label_HA.grid(row=0, column=0, sticky=tk.E)
entry_HA.grid(row=0, column=1)
option_HA_unit.grid(row=0, column=2, sticky=tk.E)

label_CA.grid(row=1, column=0, sticky=tk.E)
entry_CA.grid(row=1, column=1)
option_CA_unit.grid(row=1, column=2, sticky=tk.E)

label_COUNTRY.grid(row=2, column=0, sticky=tk.E)
combobox_COUNTRY.grid(row=2, column=1, columnspan=2, sticky=tk.W+tk.E)

vis_button.grid(row=3, column=1, sticky=tk.W+tk.E, pady=10)
vis_button.bind("<Return>", validate_form_and_create_spatial_visualizations)

entry_HA.focus()

root.mainloop()
