# ---
# jupyter:
#   jupytext:
#     notebook_metadata_filter: all
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.4
#   kernelspec:
#     display_name: venv
#     language: python
#     name: python3
#   language_info:
#     codemirror_mode:
#       name: ipython
#       version: 3
#     file_extension: .py
#     mimetype: text/x-python
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
#     version: 3.11.5
# ---

# +
import ipywidgets as widgets
from IPython.display import display

slider = widgets.IntSlider(value=10, min=0, max=100, step=1, description="Slider:")
display(slider)

# +
import panel as pn
import ipywidgets as widgets

pn.extension('ipywidgets')

slider = widgets.IntSlider(value=10, min=0, max=100, step=1, description="Slider:")
# pn.pane.IPyWidget(slider).show()
pn.pane.IPyWidget(slider)
