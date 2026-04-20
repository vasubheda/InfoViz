import os
import json
import pandas as pd
from flask import Flask, render_template
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

app = Flask(__name__)

# ensure that we can reload when we change the HTML / JS for debugging
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'exercise_01', 'data', 'agriRuralDevelopment.csv')

COUNTRIES = [
    'Afghanistan', 'Albania', 'Algeria', 'Angola', 'Argentina', 'Armenia',
    'Australia', 'Austria', 'Azerbaijan', 'Brazil', 'Bulgaria', 'Cameroon',
    'Chile', 'China', 'Colombia', 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic',
    'Ecuador', 'Egypt, Arab Rep.', 'Eritrea', 'Ethiopia', 'France', 'Germany',
    'Ghana', 'Greece', 'India', 'Indonesia', 'Iran, Islamic Rep.', 'Iraq',
    'Ireland', 'Italy', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Lebanon',
    'Malta', 'Mexico', 'Morocco', 'Pakistan', 'Peru', 'Philippines',
    'Russian Federation', 'Syrian Arab Republic', 'Tunisia', 'Turkey', 'Ukraine'
]

# Map CSV country names to TopoJSON admin property values where they differ
NAME_MAP = {
    'Egypt, Arab Rep.':     'Egypt',
    'Iran, Islamic Rep.':   'Iran',
    'Russian Federation':   'Russia',
    'Syrian Arab Republic': 'Syria',
}


def load_and_filter():
    df = pd.read_csv(CSV_PATH, na_values=['NA'])
    return df[df['Country Name'].isin(COUNTRIES)].copy()


def build_csv_data(df, indicators):
    result = {}
    for name, group in df.groupby('Country Name'):
        code = str(group.iloc[0]['Country Code'])
        years_data = {}
        for _, row in group.iterrows():
            yr = str(int(row['year']))
            vals = [
                round(float(row[ind]), 4) if pd.notna(row[ind]) else None
                for ind in indicators
            ]
            years_data[yr] = vals
        result[name] = {
            'code': code,
            'topoName': NAME_MAP.get(name, name),
            'years': years_data,
        }
    return result


def run_pca(df, indicators):
    most_recent_yr = int(df['year'].max())
    recent = df[df['year'] == most_recent_yr].copy()

    X = recent[indicators]
    # Drop columns that are entirely NaN for this year
    X = X.loc[:, X.notna().any()]
    # Mean-impute remaining NaNs
    X = X.fillna(X.mean())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=2)
    coords = pca.fit_transform(X_scaled)

    points = []
    for i, (_, row) in enumerate(recent.iterrows()):
        points.append({
            'name': row['Country Name'],
            'code': str(row['Country Code']),
            'x': round(float(coords[i, 0]), 4),
            'y': round(float(coords[i, 1]), 4),
        })

    return {
        'explained_variance': [
            round(float(pca.explained_variance_ratio_[0]), 4),
            round(float(pca.explained_variance_ratio_[1]), 4),
        ],
        'points': points,
    }


@app.route('/')
def index():
    df = load_and_filter()
    indicators = list(df.columns[3:])
    csv_data = build_csv_data(df, indicators)
    pca_data = run_pca(df, indicators)
    return render_template(
        'index.html',
        csvData=json.dumps(csv_data),
        pcaData=json.dumps(pca_data),
        indicatorList=json.dumps(indicators),
    )


if __name__ == '__main__':
    app.run()
