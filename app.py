import dash
import flask
from dash.dependencies import Output
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.express as px
# import plotly.figure_factory as ff
import pandas as pd

from datetime import date, datetime, timedelta, timezone, tzinfo
import pytz

from pymongo import MongoClient

from secretsFile import mongoString

mongoClient = MongoClient(mongoString)
db = mongoClient['scrobble']

tz = pytz.timezone("America/Chicago")
searchDate = datetime.combine(
    date.today(), datetime.max.time()
)
searchEnd = tz.localize(searchDate)
searchStart = searchEnd - timedelta(days=6)
# dbDocs = db['scrobbles'].find(
#     {"time": {"$gt": searchStart, "$lte": searchEnd}},
#     projection={"time":1, "title":1, "artists":1},
# )
dbDocs = db['scrobbles'].aggregate(
    [
        {
            '$match': {
                'time': {
                    '$gt': searchStart, 
                    '$lt': searchEnd,
                }
            }
        }, {
            '$lookup': {
                'from': 'songs', 
                'localField': 'songId', 
                'foreignField': '_id', 
                'as': 'songData'
            }
        }, {
            '$replaceRoot': {
                'newRoot': {
                    '$mergeObjects': [
                        {
                            '$arrayElemAt': [
                                '$songData', 0
                            ]
                        }, '$$ROOT'
                    ]
                }
            }
        }, {
            '$project': {
                'songId': 0, 
                'songData': 0
            }
        }
    ]
)

data = pd.DataFrame(list(dbDocs))
data['localtime'] = data['time'].dt.tz_localize(tz=pytz.utc).dt.tz_convert(tz=tz)
data['timestring'] = data['localtime'].dt.strftime("%Y-%m-%d %H:%M")
del data['_id']
data['artists'] = data['artists'].str.join(", ")

fig1 = px.histogram(
    data, y="localtime",
    marginal="rug",
    nbins=7,
)

fig1.update_layout(
    bargap=0.4
)
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

server = flask.Flask(__name__)
app = dash.Dash(server=server, external_stylesheets=external_stylesheets)

dfColumns = [
    {"name": "Time", "id": "timestring"},
    {"name": "Song Title", "id": "title"},
    {"name": "Artists", "id": "artists"},
    {"name": "Like", "id": "likeStatus"}
]

app.layout = html.Div(
    children=[
        html.H1(children="Youtube Music Scrobbles"),
        dcc.Graph(
            id="fig1",
            figure=fig1
        ),
        dash_table.DataTable(
            id="table",
            columns=dfColumns,
            data=data.to_dict('records'),
            sort_action='native',
            style_data={
                "height": "auto",
                "whiteSpace": "normal"
            },
            style_cell_conditional=[
                {"if": {"column_id": "timestring"}, "width": "175px"}
            ],
        )
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)