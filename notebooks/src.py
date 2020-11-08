import requests
import pprint
import pandas as pd
import io

from bokeh.io import push_notebook, show, output_notebook
from bokeh.layouts import row
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Legend, HoverTool
from bokeh.palettes import all_palettes

from dataclasses import dataclass, field

def get_countries(show_results=True):
    """ Utility that gets country names. Useful for creating InputConfig objects """
    url = f'https://api.covid19api.com/countries'
    result = requests.get(url).json()
    if show_results:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(result)
    
    return result

def get_data(country, country_pop, province=""):
    """Retrieves data from API, returns cleaned DF 
    
    Country is inputted from user. I'm just going a simple Google 
        search to populate this.
    """
    url = f'https://api.covid19api.com/dayone/country/{country}/status/confirmed/live'
    j = requests.get(url).json()

    raw_df = pd.DataFrame.from_dict(j)
    
    df = raw_df.copy()
    
    df = df[df["Province"] == province]
    
    df = df.reset_index()
    
    df['Date'] = df['Date'].astype('datetime64[ns]')
    df["Daily Cases"] = 0
    
    for i in range(1, len(df)):
        df.loc[i, 'Daily Cases'] = df.loc[i, 'Cases'] - df.loc[i-1, 'Cases']
        
    df = df[df['Daily Cases'] >= 0]
    
    df['DCRA'] = df['Daily Cases'].rolling(7).mean()  # Daily Cases Rolling Average
    
    df['DCRA Per Capita'] = df['DCRA']/country_pop * 100000
    
    return df

# Don't be intimated by the below, it's just an alternative object instantiation
#     using dataclasses. See https://docs.python.org/3/library/dataclasses.html
#     and https://www.infoworld.com/article/3563878/how-to-use-python-dataclasses.html
#     for more details

@dataclass
class InputConfig:
    country: str
    base_pop: int
    province: str = ""
    df: pd.DataFrame = field(init=False)
    data_src: ColumnDataSource = field(init=False)
        
    def __post_init__(self):
        self.df = get_data(self.country, self.base_pop, province=self.province)
        self.data_src = ColumnDataSource(self.df)


# Below is equivalent to the above, but in a more recognizable form

# class InputConfig:
#     """ Object that holds data and labels of data for graphing """
    
#     def __init__(self, country, base_pop, province=""):
        
#         self.country = country
#         self.base_pop = base_pop
#         self.province = province
#         self.df = get_data(country, base_pop, province=province)
#         self.data_src = ColumnDataSource(self.df)

# Some Bokeh plotting accessories
def get_hover_tool(renderer):

    return HoverTool(
        renderers=[renderer],
        tooltips=[
            ("Daily New Cases 7-Day Rolling Avg", "@{DCRA Per Capita} per 100k ppl"),
            ("Daily New Cases Raw Count", "@{Daily Cases} Total"),
            ("Country", "@{Country}"),
            ("Date", "@Date{%F}"),
        ],
        formatters={
            '@Date': 'datetime',
        }
    )

def format_country_label(input_config):
    legend_label = f'{input_config.country.title().replace("-", " ")}'
    if input_config.province:
        legend_label = f"{legend_label} ({input_config.province.title()})"
    return legend_label

def graph_data(input_configs):
    p = figure(
        plot_width=800,
        plot_height=400,
        x_axis_type='datetime',
        x_axis_label='Date (M/YYYY)',
        y_axis_label='Daily New Cases per 100 000 people',
    )
    
    legend = Legend()
    legend.click_policy="hide"
    p.add_layout(legend, 'right')
    
    colors = all_palettes['Colorblind'][3]
    if len(input_configs) > 3:
        colors = all_palettes['Colorblind'][len(input_configs)]

    for input_config, color in zip(input_configs, colors):

        curr_series = p.circle(
            x="Date",
            y="DCRA Per Capita",
            fill_color=color,
            line_color=color,
            fill_alpha=0.8,
            legend_label=format_country_label(input_config),
            source=input_config.data_src
        )
        
        p.add_tools(get_hover_tool(curr_series))

    show(p)